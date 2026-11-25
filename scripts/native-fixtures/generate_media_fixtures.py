#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Generate and semantically read back four synthetic native-test inputs, offline."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import tarfile
import threading

HERE = Path(__file__).resolve().parent
FILES = ('test_480p.mp4', 'test_1080p_bframes.mp4', 'test_images.mcap', 'potato.mcap')


def digest(path):
    """Hash bytes without loading media into memory."""
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify_probe(probe, width, height, require_b_frames):
    """Enforce the actual decoder fixtures' shape and 120-frame time base."""
    streams = probe['streams']
    assert len(streams) == 1, 'expected one video stream'
    s = streams[0]
    assert (s['codec_name'], s['pix_fmt'], s['width'], s['height']) == ('h264', 'yuv420p', width, height)
    assert s['avg_frame_rate'] == '30/1' and int(s['nb_read_frames']) == 120
    assert abs(float(s['duration']) - 4.0) < 0.001
    assert not require_b_frames or int(s['has_b_frames']) > 0
    return s


def verify_headers(include):
    """Use only the reviewed MCAP 2.1.1 header set; its upstream archive is pinned."""
    lock = json.loads((HERE / 'mcap-source-lock.json').read_text())
    assert not any(p.is_symlink() for p in (include / 'mcap').rglob('*')), 'MCAP header symlinks are not allowed'
    actual = {p.relative_to(include).as_posix(): digest(p)
              for p in (include / 'mcap').rglob('*') if p.is_file()}
    assert actual == lock['headers'], 'MCAP headers differ from reviewed source lock'
    return lock


def package_identity(package, metadata, tools, timeout=180):
    """Match executable bytes to an APT-authenticated package supplied by CI."""
    info = json.loads(metadata.read_text())
    assert info['sha256'] == digest(package), 'package archive SHA mismatch'
    for field in ('Package', 'Version'):
        actual = subprocess.check_output(['dpkg-deb', '--field', str(package), field], text=True,
                                         timeout=timeout).strip()
        assert actual == info[field.lower()], f'package {field} mismatch'
    assert info['url'].startswith(('https://deb.debian.org/', 'http://archive.ubuntu.com/',
                                  'https://archive.ubuntu.com/', 'http://security.ubuntu.com/',
                                  'https://security.ubuntu.com/')), 'expected official Debian/Ubuntu package source'
    assert info.get('apt_signature_evidence'), 'CI must retain signed APT acquisition evidence'
    command = ['dpkg-deb', '--fsys-tarfile', str(package)]
    # The generator runs on Linux. dpkg-deb may launch a decompressor which
    # inherits the pipe, so terminate the new, owned process group on timeout.
    process = subprocess.Popen(command, stdout=subprocess.PIPE, start_new_session=True)
    expired = threading.Event()

    def stop_overdue():
        expired.set()
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    timer = threading.Timer(timeout, stop_overdue)
    timer.daemon = True
    timer.start()
    found = {}
    try:
        with tarfile.open(fileobj=process.stdout, mode='r|') as archive:
            for member in archive:
                name = member.name.removeprefix('./')
                if name in ('usr/bin/ffmpeg', 'usr/bin/ffprobe'):
                    assert member.isfile(), 'tool must be a regular package file'
                    found[Path(name).name] = hashlib.file_digest(archive.extractfile(member), 'sha256').hexdigest()
        status = process.wait()
    except BaseException:
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.wait()
        if expired.is_set():
            raise subprocess.TimeoutExpired(command, timeout)
        raise
    finally:
        timer.cancel()
        if process.stdout is not None:
            process.stdout.close()
    if expired.is_set():
        raise subprocess.TimeoutExpired(command, timeout)
    assert status == 0 and len(found) == 2
    assert found == {name: digest(path) for name, path in tools.items()}, 'tools do not match official package bytes'
    return info


def run_logged(command, cwd, evidence, label, timeout=180):
    """Keep raw output even when a bounded generation command times out."""
    process = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               start_new_session=True)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        stdout, stderr = process.communicate()
        (evidence / (label + '.stdout')).write_bytes(stdout)
        (evidence / (label + '.stderr')).write_bytes(stderr)
        raise subprocess.TimeoutExpired(command, timeout, output=stdout, stderr=stderr) from exc
    except BaseException:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.communicate()
        raise
    (evidence / (label + '.stdout')).write_bytes(stdout)
    (evidence / (label + '.stderr')).write_bytes(stderr)
    assert process.returncode == 0, f'{label} exited {process.returncode}; inspect retained evidence'
    return stdout


def verify_manifest(directory, expected_sha256=None):
    """Check transport identity and strict four-file semantic claims before staging."""
    path = directory / 'manifest.json'
    if expected_sha256 is not None:
        assert digest(path) == expected_sha256, 'manifest transport SHA mismatch'
    manifest = json.loads(path.read_text())
    assert manifest['schema'] == 1 and manifest['synthetic'] is True
    assert set(manifest['files']) == set(FILES), 'unexpected artifact file set'
    for name, entry in manifest['files'].items():
        media = directory / name
        assert media.is_file() and not media.is_symlink()
        assert media.stat().st_size == entry['bytes'] and digest(media) == entry['sha256'], name
    for name, width, height in [(FILES[0], 640, 480), (FILES[1], 1920, 1080)]:
        verify_probe({'streams': [manifest['semantics']['video'][name]]}, width, height, width == 1920)
    for name, channels, count in [(FILES[2], 1, 90), (FILES[3], 4, 8400)]:
        record = manifest['semantics']['mcap'][name]
        assert record['channels'] == channels and record['messages_per_channel'] == count
        assert record['all_payloads_timestamps_sequences_validated'] is True
    return manifest


def main():
    """Keep every generated file in a new directory; never replace old fixtures."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mcap-include', type=Path, required=True)
    parser.add_argument('--mcap-license', type=Path, required=True)
    parser.add_argument('--ffmpeg', type=Path, required=True)
    parser.add_argument('--ffprobe', type=Path, required=True)
    parser.add_argument('--cxx', type=Path, required=True)
    parser.add_argument('--tool-package', type=Path, required=True)
    parser.add_argument('--tool-provenance', type=Path, required=True)
    args = parser.parse_args()
    include = args.mcap_include.resolve()
    tools = {'ffmpeg': args.ffmpeg.resolve(), 'ffprobe': args.ffprobe.resolve()}
    lock = verify_headers(include)
    assert digest(args.mcap_license) == lock['license_sha256'], 'MCAP license differs from pinned source'
    package = package_identity(args.tool_package, args.tool_provenance, tools)
    out = args.output.absolute()
    assert not out.exists() and not out.is_symlink(), 'output must be a new directory'
    out.mkdir(parents=True)
    evidence = out / 'evidence'
    evidence.mkdir()
    (evidence / 'MCAP-LICENSE').write_bytes(args.mcap_license.read_bytes())
    commands = []
    # Paths in the portable manifest are symbolic, never cloud workspace paths.
    replacements = [(str(out), '$OUTPUT'), (str(HERE), '$GENERATOR'),
                    (str(include), '$MCAP_INCLUDE'), (str(args.cxx.resolve()), '$CXX')]
    replacements += [(str(path), '$' + name.upper()) for name, path in tools.items()]

    def run(command, label):
        command = [str(item) for item in command]
        printable = list(command)
        for path, token in replacements:
            printable = [item.replace(path, token) for item in printable]
        commands.append({'label': label, 'argv': printable})
        return run_logged(command, out, evidence, label)

    identities = {}
    for name, path in {**tools, 'cxx': args.cxx.resolve()}.items():
        identities[name] = {'sha256': digest(path), 'version': run([path, '-version' if name != 'cxx' else '--version'], name + '-version').decode()}
    probes = {}
    for name, width, height, keyint in [('test_480p.mp4', 640, 480, 15), ('test_1080p_bframes.mp4', 1920, 1080, 30)]:
        run([tools['ffmpeg'], '-nostdin', '-n', '-f', 'lavfi', '-i', f'testsrc=size={width}x{height}:rate=30:duration=4',
             '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-g', keyint, '-keyint_min', keyint, '-bf', '3', '-threads', '2', out / name], name + '-generate')
        probe = json.loads(run([tools['ffprobe'], '-v', 'error', '-select_streams', 'v', '-count_frames', '-show_streams', '-of', 'json', out / name], name + '-probe'))
        probes[name] = verify_probe(probe, width, height, width == 1920)
    png = evidence / 'synthetic.png'
    run([tools['ffmpeg'], '-nostdin', '-n', '-f', 'lavfi', '-i', 'testsrc=size=32x24:rate=1', '-frames:v', '1', '-threads', '1', png], 'png-generate')
    png_probe = json.loads(run([tools['ffprobe'], '-v', 'error', '-show_streams', '-of', 'json', png], 'png-probe'))['streams'][0]
    assert (png_probe['codec_name'], png_probe['width'], png_probe['height']) == ('png', 32, 24)
    payload = {'timestamp': {'sec': 0, 'nsec': 0}, 'frame_id': 'synthetic-camera', 'format': 'png', 'data': base64.b64encode(png.read_bytes()).decode()}
    image_json = evidence / 'image.json'
    image_json.write_text(json.dumps(payload), encoding='utf-8')
    assert base64.b64decode(json.loads(image_json.read_text())['data'], validate=True) == png.read_bytes()
    binary = evidence / 'mcap-fixture-generator'
    run([args.cxx.resolve(), '-std=c++20', '-O1', '-I', include, HERE / 'mcap_fixture_generator.cpp', '-o', binary], 'mcap-compile')
    mcap = [json.loads(line) for line in run([binary, image_json, out], 'mcap-generate-readback').decode().splitlines()]
    assert [(x['channels'], x['messages_per_channel']) for x in mcap] == [(1, 90), (4, 8400)]
    manifest = {'schema': 1, 'synthetic': True, 'purpose': 'offline decoder/query/dual-store tests, NOT live MCAP or golden media',
                'files': {name: {'bytes': (out / name).stat().st_size, 'sha256': digest(out / name)} for name in FILES},
                'tools': identities, 'tool_package': package, 'mcap_source': lock, 'commands': commands,
                'semantics': {'video': probes, 'mcap': dict(zip(FILES[2:], mcap)), 'png': {'width': 32, 'height': 24}},
                'generator_sources': {p.name: digest(p) for p in [Path(__file__), HERE / 'mcap_fixture_generator.cpp', HERE / 'mcap-source-lock.json']},
                'byte_reproducibility': 'not guaranteed across encoder/platform versions; verify semantics and record actual bytes'}
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    verify_manifest(out)
    print(json.dumps(manifest['files'], indent=2))


if __name__ == '__main__':
    if not __debug__:
        raise SystemExit('Do not disable fixture validation with Python -O')
    main()
