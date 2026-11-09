#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Fail-closed checks for a separately staged Windows native-test bundle.

These checks do not build, copy or execute a test. A successful audit does not
prove dynamically loaded dependencies or fixture safety; those require the
additional evidence described in the accompanying design document.
"""
from __future__ import annotations

import argparse
import collections
import ctypes
from ctypes import wintypes
import hashlib
import json
import ntpath
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit

SCHEMA = 1
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
WIN_ABS = re.compile(r"(?:(?<![A-Za-z0-9_])|(?<=-I)|(?<=-L))[A-Za-z]:[\\/]")
UNC_ABS = re.compile(r"\\\\(?=[^\\/])|(?<![:A-Za-z0-9_/])//(?=[^/])")
POSIX_ABS = re.compile(r"(?<![A-Za-z0-9_:/\\])/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*/?")
RESERVED = re.compile(r"(?:CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|COM[1-9¹²³]|LPT[1-9¹²³])(?:\..*)?\Z", re.I)
MSVC_DEBUG = re.compile(r"(?:(?:msvcp|msvcr|vcruntime|concrt|vccorlib|vcomp)\d+(?:_\d+)?d|mfc(?:m)?\d+u?d|ucrtbased)\.dll\Z", re.I)
BANNED_NAMES = {"cmakecache.txt", "build.ninja", "rules.ninja", "remotes.json", "credentials.json", "credentials.db", "global.conf", ".netrc", ".gitconfig", ".git-credentials", ".npmrc", ".pypirc", ".env", "auth.json", "pwsh.exe", "powershell.exe"}
BANNED_SUFFIXES = {".obj", ".lib", ".pdb"}
GTEST_SKIP = re.compile(r"^\[\s*SKIPPED\s*\]\s+(\S*\.\S+?)(?:\s+\(\d+\s+ms\))?\s*$")
GTEST_SKIP_TOTAL = re.compile(r"^\[\s*SKIPPED\s*\]\s+(\d+)\s+tests?\b")
QT_SKIP = re.compile(r"^SKIP\s*:\s*(.+?)\s*$")
QT_TOTALS = re.compile(r"^Totals:\s+\d+ passed,\s+\d+ failed,\s+(\d+) skipped\b")


class AuditError(Exception):
    """The audit could not establish a required property."""


def is_reserved_component(name: str):
    # Win32 treats a reserved DOS device name as reserved even with an
    # extension and spaces before its dot (e.g. NUL .txt).
    return RESERVED.fullmatch(name.split('.', 1)[0].rstrip(' ')) is not None


class StreamData(ctypes.Structure):
    _fields_ = [('size', ctypes.c_longlong), ('name', ctypes.c_wchar * 296)]


def windows_stream_names(path: Path, kernel=None, get_last_error=None):
    """Enumerate NTFS streams; unexpected Windows errors fail closed."""
    kernel = kernel if kernel is not None else ctypes.WinDLL('kernel32', use_last_error=True)
    get_last_error = get_last_error if get_last_error is not None else ctypes.get_last_error
    first, following, close = kernel.FindFirstStreamW, kernel.FindNextStreamW, kernel.FindClose
    first.argtypes = [wintypes.LPCWSTR, ctypes.c_int, ctypes.POINTER(StreamData), wintypes.DWORD]
    first.restype = wintypes.HANDLE
    following.argtypes = [wintypes.HANDLE, ctypes.POINTER(StreamData)]
    following.restype = wintypes.BOOL
    close.argtypes = [wintypes.HANDLE]
    close.restype = wintypes.BOOL
    data = StreamData()
    handle = first(str(path), 0, ctypes.byref(data), 0)
    if handle == ctypes.c_void_p(-1).value:
        if get_last_error() == 38:  # ERROR_HANDLE_EOF, including empty directory streams.
            return []
        raise AuditError(f'cannot enumerate Windows streams for {path}: error {get_last_error()}')
    try:
        result = [data.name]
        while following(handle, ctypes.byref(data)):
            result.append(data.name)
        error = get_last_error()
        if error != 38:
            raise AuditError(f'Windows stream enumeration failed for {path}: error {error}')
        return result
    finally:
        if not close(handle):
            raise AuditError(f'cannot close Windows stream enumeration for {path}')


def check_no_named_streams(path: Path, is_directory: bool):
    if os.name != 'nt':
        return
    names = windows_stream_names(path)
    if any(name != '::$DATA' for name in names) or len(names) > 1 or (not is_directory and names != ['::$DATA']):
        raise AuditError(f'payload has named or unexpected Windows data streams: {path}')


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def check_provenance(p):
    """Require an identity record without accepting a mutable branch as identity."""
    if not isinstance(p, dict):
        raise AuditError("provenance must be a JSON object")
    for key in ("source_sha", "source_tree", "workflow_sha"):
        if not HEX40.fullmatch(str(p.get(key, ""))):
            raise AuditError(f"{key} must be a full lower-case Git object ID")
    if p.get("source_clean") is not True:
        raise AuditError("source_clean must be true after CI verifies the exact checkout")
    for key in ("configuration", "qt", "sdk", "compiler", "windows_sdk", "generator", "runner_image"):
        if (not isinstance(p.get(key), str) or not p[key].strip() or len(p[key]) > 256 or
                "\n" in p[key] or "\r" in p[key]):
            raise AuditError(f"missing or non-sanitized provenance field: {key}")
    for key in ("conan_lock_sha256", "conan_graph_sha256"):
        if not HEX64.fullmatch(str(p.get(key, ""))):
            raise AuditError(f"{key} must be a SHA-256 digest")
    subs = p.get("submodules")
    if not isinstance(subs, dict) or not subs or any(not HEX40.fullmatch(str(v)) for v in subs.values()):
        raise AuditError("submodules must map names to full lower-case commit IDs")
    tools = p.get("tools")
    if not isinstance(tools, list) or not tools:
        raise AuditError("tools must list each runtime tool and its pinned origin")
    names = set()
    for tool in tools:
        if not isinstance(tool, dict) or any(not isinstance(tool.get(k), str) or not tool[k].strip() for k in ("name", "version", "origin")):
            raise AuditError("every tool needs name, version and origin")
        if not re.fullmatch(r"[a-z0-9._-]+", tool["name"]):
            raise AuditError("tool names must be lower-case identifiers")
        url = urlsplit(tool["origin"])
        if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise AuditError("tool origin must be an HTTPS URL without credentials, query or fragment")
        if len(tool["version"]) > 128 or "\n" in tool["version"] or "\r" in tool["version"]:
            raise AuditError("tool version must be a short single line")
        if not HEX64.fullmatch(str(tool.get("sha256", ""))):
            raise AuditError("every tool needs its verified distribution SHA-256")
        if tool["name"].casefold() in names:
            raise AuditError("duplicate provenance tool name")
        names.add(tool["name"].casefold())
    required_tools = {"cmake", "ctest", "python", "embedded-cpython", "lrelease", "lupdate", "rcc", "ifw", "7z"}
    if not required_tools.issubset(names):
        raise AuditError(f"missing required runtime tool identities: {sorted(required_tools - names)}")


def check_windows_relative(rel: str, logical_root: str):
    """Reject ambiguous, illegal or too-long Windows paths before transfer."""
    if not rel or rel.startswith("/") or "\\" in rel:
        raise AuditError(f"not a canonical relative path: {rel!r}")
    parts = rel.split("/")
    for part in parts:
        if (part in ("", ".", "..") or part.endswith((".", " ")) or
                any(ord(c) < 32 or c in '<>:"|?*' for c in part) or is_reserved_component(part)):
            raise AuditError(f"invalid Windows component: {rel!r}")
        if len(part.encode("utf-16-le")) // 2 > 255:
            raise AuditError(f"Windows component exceeds 255 UTF-16 code units: {rel!r}")
    # A conservative ceiling leaves room for Win32 operations when the target
    # machine has not enabled long paths. It is deliberately not raised here.
    absolute = ntpath.join(logical_root, *parts)
    if len(absolute.encode("utf-16-le")) // 2 >= 240:
        raise AuditError(f"destination path reaches the conservative 240-unit UTF-16 ceiling: {rel!r}")
    if {".git", ".ssh", ".aws"} & {part.casefold() for part in parts}:
        raise AuditError(f"Git or credential metadata must not be bundled: {rel!r}")
    name = parts[-1].casefold()
    if name in BANNED_NAMES or Path(name).suffix in BANNED_SUFFIXES or MSVC_DEBUG.fullmatch(name):
        raise AuditError(f"cache, build-only, credential or non-redistributable debug file: {rel!r}")


def regular_file(path: Path):
    info = path.lstat()
    # Windows junctions carry FILE_ATTRIBUTE_REPARSE_POINT even when islink is false.
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
        raise AuditError(f"reparse point or symlink: {path}")
    if not stat.S_ISREG(info.st_mode):
        raise AuditError(f"not a regular file: {path}")
    if info.st_nlink > 1:
        raise AuditError(f"hard-linked file must be copied to an independent staging file: {path}")
    return info


def check_root(root: Path, logical_root: str, require_exact: bool = False):
    """Reject reparse points along the physical destination and wrong VM roots."""
    root = root.absolute()
    for path in (root, *root.parents):
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise AuditError(f"reparse point or symlink in root ancestry: {path}")
    if require_exact and os.name == "nt" and ntpath.normcase(ntpath.normpath(str(root))) != ntpath.normcase(logical_root):
        raise AuditError("payload is not at its exact build-time root")
    return root


def inventory(root: Path, logical_root: str, exclude_manifest: bool = False, require_exact: bool = False,
              ignore_owned_runs: bool = False):
    root = check_root(root, logical_root, require_exact=require_exact)
    if not root.is_dir() or root.is_symlink():
        raise AuditError("payload root must be an existing non-symlink directory")
    root_info = root.lstat()
    if getattr(root_info, "st_file_attributes", 0) & 0x400:
        raise AuditError("payload root is a reparse point")
    check_no_named_streams(root, True)
    files, directories, seen = [], [], set()
    def scan_error(error):
        raise AuditError(f'cannot enumerate payload directory: {error}') from error
    for parent, dirs, names in os.walk(root, followlinks=False, onerror=scan_error):
        parent = Path(parent)
        for name in sorted(dirs + names, key=str.casefold):
            p = parent / name
            rel = p.relative_to(root).as_posix()
            if exclude_manifest and rel == "_bundle/manifest.json":
                regular_file(p)
                check_no_named_streams(p, False)
                continue
            check_windows_relative(rel, logical_root)
            folded = rel.casefold()
            if folded in seen:
                raise AuditError(f"case-insensitive destination collision: {rel}")
            seen.add(folded)
            info = p.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise AuditError(f"reparse point or symlink: {rel}")
            if name in dirs:
                if not stat.S_ISDIR(info.st_mode):
                    raise AuditError(f"not a directory: {rel}")
                check_no_named_streams(p, True)
                directories.append(rel)
                if ignore_owned_runs and rel == 'r':
                    # Existing test-run evidence is not read, changed or reused.
                    dirs.remove(name)
            else:
                info = regular_file(p)
                check_no_named_streams(p, False)
                sha = digest(p)
                after = regular_file(p)
                if (info.st_size, info.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                    raise AuditError(f"file changed while being hashed: {rel}")
                files.append({"path": rel, "bytes": info.st_size, "sha256": sha, "mtime_ns": info.st_mtime_ns})
    return {"files": sorted(files, key=lambda x: x["path"].casefold()),
            "directories": sorted(directories, key=str.casefold)}


def windows_root(value: str):
    """Require a canonical absolute drive path ending in the source SHA prefix."""
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z]:\\(?:[^\\]+\\)*n\\[0-9a-f]{12}", value):
        raise AuditError("logical root must be an absolute drive path ending in n\\<12 lowercase SHA>")
    if ntpath.normpath(value) != value:
        raise AuditError("logical root is not canonical")
    for part in value[3:].split("\\"):
        if (part in ("", ".", "..") or part.endswith((".", " ")) or is_reserved_component(part) or
                any(ord(c) < 32 or c in '<>:"|?*' for c in part)):
            raise AuditError("logical root contains an invalid Windows path component")
    return value


def stage_allowlisted(plan_path: Path, staging: Path, logical_root: str):
    """Copy only explicitly enumerated, hashed files into a fresh staging root.

    The origin/notice declarations are evidence for review, not a license or
    dependency-closure determination. No directory, glob or cache is copied.
    """
    plan = read_json(plan_path)
    if not isinstance(plan, dict):
        raise AuditError("stage plan must be an object")
    origins, entries = plan.get("origins"), plan.get("files")
    declared_dirs = plan.get("directories", [])
    if not isinstance(declared_dirs, list) or any(not isinstance(x, str) for x in declared_dirs):
        raise AuditError("directories must be an explicit list of relative paths")
    if not isinstance(origins, dict) or not origins or not isinstance(entries, list) or not entries:
        raise AuditError("stage plan needs non-empty origins and files")
    staging = staging.absolute()
    if not staging.exists():
        staging.mkdir()
    check_root(staging, logical_root)
    if not staging.is_dir() or any(staging.iterdir()):
        raise AuditError("staging directory must be fresh and empty")
    roots, sanitized_origins = {}, {}
    for key, value in origins.items():
        if not isinstance(key, str) or not key or not isinstance(value, dict):
            raise AuditError("invalid stage origin")
        if any(not isinstance(value.get(k), str) or not value[k].strip() for k in ("root", "description", "revision")):
            raise AuditError(f"origin needs root, description and revision: {key}")
        if (len(value["description"]) > 256 or any(x in value["description"] for x in ("\n", "\r", "?", "@"))):
            raise AuditError(f"origin description must be a sanitized single line: {key}")
        if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", value["revision"]):
            raise AuditError(f"origin revision must be a full commit ID or SHA-256: {key}")
        licenses = value.get("license_files")
        if not isinstance(licenses, list) or not licenses or any(not isinstance(x, str) for x in licenses):
            raise AuditError(f"origin needs explicit bundled license files: {key}")
        root = Path(value["root"])
        if not root.is_absolute() or not root.is_dir():
            raise AuditError(f"origin root is not an existing absolute directory: {key}")
        root = check_root(root, logical_root)
        if {".git", ".ssh", ".aws"} & {part.casefold() for part in root.parts}:
            raise AuditError(f"origin root is inside Git or credential metadata: {key}")
        try:
            common = os.path.normcase(os.path.commonpath((str(root), str(staging))))
        except ValueError:
            common = ""
        if common in (os.path.normcase(str(root)), os.path.normcase(str(staging))):
            raise AuditError("staging and origin directories must not contain each other")
        roots[key] = root
        sanitized_origins[key] = {"description": value["description"], "revision": value["revision"], "license_files": licenses}
    seen, prepared = {}, []
    for directory in declared_dirs:
        check_windows_relative(directory, logical_root)
        if directory.split("/")[0].casefold() == "_bundle":
            raise AuditError("reserved evidence directory in stage plan")
    for entry in entries:
        if not isinstance(entry, dict):
            raise AuditError("invalid staged file entry")
        origin, src, dst, expected = (entry.get(k) for k in ("origin", "source", "destination", "sha256"))
        if origin not in roots or not isinstance(src, str) or not isinstance(dst, str) or not HEX64.fullmatch(str(expected)):
            raise AuditError("each staged file needs origin, exact source/destination and SHA-256")
        check_windows_relative(src, logical_root)
        check_windows_relative(dst, logical_root)
        if dst.split("/")[0].casefold() == "_bundle":
            raise AuditError("reserved bundle evidence path in stage plan")
        folded = dst.casefold()
        if folded in seen:
            raise AuditError(f"duplicate or case-colliding staged destination: {dst}")
        seen[folded] = dst
        source = roots[origin].joinpath(*src.split("/"))
        for parent in source.parents:
            if parent == roots[origin]:
                break
            info = parent.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise AuditError(f"source contains a link or reparse point: {src}")
        info = source.lstat()
        if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise AuditError(f"source is not an ordinary file: {src}")
        if digest(source) != expected:
            raise AuditError(f"source SHA-256 mismatch: {src}")
        prepared.append((source, dst, expected, origin, src))
    spellings = {}
    for target in list(seen.values()) + declared_dirs:
        parts = target.split("/")
        for i in range(1, len(parts) + 1):
            name = "/".join(parts[:i])
            folded = name.casefold()
            if folded in spellings and spellings[folded] != name:
                raise AuditError(f"case-colliding staged path: {name}")
            spellings[folded] = name
            if i < len(parts) and folded in seen:
                raise AuditError("a staged file is also a parent of another path")
    if len({x.casefold() for x in declared_dirs}) != len(declared_dirs):
        raise AuditError("duplicate staged directory")
    if any(x.casefold() in seen for x in declared_dirs):
        raise AuditError("a staged path cannot be both a file and directory")
    for key, value in sanitized_origins.items():
        for license_path in value["license_files"]:
            check_windows_relative(license_path, logical_root)
            if license_path.casefold() not in seen:
                raise AuditError(f"declared license file is absent from the allowlist: {key}: {license_path}")
    for directory in declared_dirs:
        staging.joinpath(*directory.split("/")).mkdir(parents=True, exist_ok=True)
    for source, dst, expected, origin, src in prepared:
        target = staging.joinpath(*dst.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        if digest(target) != expected:
            raise AuditError(f"staged file SHA-256 mismatch: {dst}")
    origin_record = {"schema": SCHEMA, "origins": sanitized_origins,
                     "files": [{"path": dst, "origin": origin, "source_relative": src}
                               for _, dst, _, origin, src in prepared]}
    write_json(staging / "_bundle" / "origins.json", origin_record)
    inventory(staging, logical_root)
    return {"files_copied": len(prepared), "origins": len(origins), "origin_record": "_bundle/origins.json"}


def create_manifest(root: Path, logical_root: str, provenance: Path, output: Path):
    root = check_root(root, logical_root)
    output = output.absolute()
    internal_manifest = output == root / "_bundle" / "manifest.json"
    if (output == root or root in output.parents) and not internal_manifest:
        raise AuditError("an internal manifest must be _bundle/manifest.json")
    if internal_manifest:
        if output.exists():
            raise AuditError("refusing to overwrite a pre-existing internal manifest")
        output.parent.mkdir(parents=True, exist_ok=True)
    p = read_json(provenance)
    check_provenance(p)
    if p["source_sha"][:12] != logical_root[-12:]:
        raise AuditError("logical root SHA prefix differs from source_sha")
    snapshot = inventory(root, logical_root)
    files = snapshot["files"]
    if not files:
        raise AuditError("empty payload")
    manifest = {"schema": SCHEMA, "logical_root": logical_root, "provenance": p,
                "files": files, "directories": snapshot["directories"]}
    write_json(output, manifest)
    check_no_named_streams(output, False)
    return {"files": len(files), "directories": len(snapshot["directories"]),
            "bytes": sum(x["bytes"] for x in files), "manifest_sha256": digest(output)}


def verify_manifest(root: Path, manifest_path: Path, require_mtime: bool, expected_manifest_sha256: str,
                    expected_root: str, expected_source_sha: str, expected_source_tree: str, expected_config: str,
                    allow_owned_runs: bool = False):
    regular_file(manifest_path)
    check_no_named_streams(manifest_path, False)
    if not HEX64.fullmatch(expected_manifest_sha256) or digest(manifest_path) != expected_manifest_sha256:
        raise AuditError("manifest SHA-256 does not match independent CI evidence")
    manifest = read_json(manifest_path)
    if manifest.get("schema") != SCHEMA:
        raise AuditError("unsupported manifest schema")
    logical_root = windows_root(manifest.get("logical_root", ""))
    if ntpath.normcase(logical_root) != ntpath.normcase(windows_root(expected_root)):
        raise AuditError("manifest root differs from the independently approved test root")
    check_provenance(manifest.get("provenance"))
    if manifest["provenance"]["source_sha"] != expected_source_sha or manifest["provenance"]["source_tree"] != expected_source_tree:
        raise AuditError("manifest source identity differs from independently expected source/tree")
    if manifest["provenance"]["configuration"] != expected_config:
        raise AuditError("manifest build configuration differs from the independently expected configuration")
    if manifest["provenance"]["source_sha"][:12] != logical_root[-12:]:
        raise AuditError("source SHA and logical root disagree")
    root = check_root(root, logical_root, require_exact=True)
    internal_manifest = manifest_path.absolute() == root / "_bundle" / "manifest.json"
    if allow_owned_runs and (any(item.get('path', '').casefold().startswith('r/') for item in manifest.get('files', [])) or
                             any(item.casefold().startswith('r/') for item in manifest.get('directories', []))):
        raise AuditError('the owned run-output directory must be empty in the original bundle')
    snapshot = inventory(root, logical_root, exclude_manifest=internal_manifest, require_exact=True,
                         ignore_owned_runs=allow_owned_runs)
    actual = snapshot["files"]
    expected = manifest.get("files")
    if snapshot["directories"] != manifest.get("directories"):
        raise AuditError("payload directory set differs from the manifest")
    if not isinstance(expected, list) or not expected:
        raise AuditError("manifest file list is empty or invalid")
    def identity(items):
        if require_mtime:
            return items
        return [{k: v for k, v in item.items() if k != "mtime_ns"} for item in items]
    if identity(actual) != identity(expected):
        raise AuditError("payload file set, bytes, SHA-256 or requested mtimes do not match the manifest")
    return {"files": len(actual), "directories": len(snapshot["directories"]),
            "bytes": sum(x["bytes"] for x in actual), "mtimes_checked": require_mtime}


def to_relative(path: str, logical_root: str):
    normalized = ntpath.normpath(path)
    try:
        common = ntpath.commonpath([ntpath.normcase(normalized), ntpath.normcase(logical_root)])
    except ValueError:
        raise AuditError(f"path is outside the agreed root: {path}") from None
    if common != ntpath.normcase(logical_root):
        raise AuditError(f"path is outside the agreed root: {path}")
    return ntpath.relpath(normalized, logical_root).replace("\\", "/")


def absolute_references(text: str):
    """Extract obvious drive paths; ambiguous multi-path strings fail closed."""
    for segment in re.split(r'[;\r\n"]', text):
        if UNC_ABS.search(segment):
            raise AuditError(f"UNC path cannot be bundled under the agreed root: {segment!r}")
        if re.search(r'(?:^|[=\s]|-[IL])\\(?!\\)', segment):
            raise AuditError(f"drive-root-relative Windows path needs explicit review: {segment!r}")
        if re.search(r'(?:^|[=\s]|-[IL])[A-Za-z]:(?![\\/])', segment):
            raise AuditError(f"drive-relative Windows path needs explicit review: {segment!r}")
        if POSIX_ABS.search(segment):
            raise AuditError(f"POSIX absolute path needs explicit review: {segment!r}")
        matches = list(WIN_ABS.finditer(segment))
        if len(matches) > 1:
            raise AuditError(f"ambiguous string contains multiple Windows paths: {segment!r}")
        if matches:
            yield segment[matches[0].start():].strip()


def walk_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for x in value:
            yield from walk_strings(x)
    elif isinstance(value, dict):
        for x in value.values():
            yield from walk_strings(x)


def bundled_qttest_output(test, logical_root):
    """Recognize only this repository's two explicit QtTest text outputs."""
    if test.get('name') != 'pj_bundled_translations_test':
        return None
    command = test.get('command')
    if (not isinstance(command, list) or len(command) != 5 or
            not all(isinstance(arg, str) for arg in command) or
            ntpath.basename(command[0]).casefold() != 'pj_bundled_translations_test.exe' or
            command[1:4] != ['-o', '-,txt', '-o'] or not command[4].endswith(',txt')):
        raise AuditError('bundled translations QtTest command differs from the reviewed output contract')
    path = command[4][:-4]
    relative = to_relative(path, logical_root)
    check_windows_relative(relative, logical_root)
    if relative.casefold() not in ('b/testing/temporary/bundled-translations.txt',
                                    'i/testing/temporary/bundled-translations.txt'):
        raise AuditError('bundled translations output is not in the exact owned CTest location')
    return path


def audit_discovery(root: Path, logical_root: str, discovery: Path, allowed_outputs: Path | None, expected_config: str):
    root = check_root(root, logical_root)
    doc = read_json(discovery)
    if doc.get("kind") != "ctestInfo" or not isinstance(doc.get("tests"), list) or not doc["tests"]:
        raise AuditError("expected a non-empty CTest json-v1 discovery")
    allow = read_json(allowed_outputs) if allowed_outputs else {}
    if not isinstance(allow, dict) or any(not isinstance(v, list) for v in allow.values()):
        raise AuditError("allowed outputs must map individual test names to exact paths")
    used, names, refs = set(), set(), []
    for test in doc["tests"]:
        name, command = test.get("name"), test.get("command")
        if not isinstance(name, str) or not name or name in names:
            raise AuditError(f"missing or duplicate CTest name: {name!r}")
        names.add(name)
        if test.get("config") != expected_config:
            raise AuditError(f"unexpected or missing test configuration: {name}")
        if not isinstance(command, list) or not command or not all(isinstance(x, str) for x in command):
            raise AuditError(f"missing or malformed command: {name}")
        if not WIN_ABS.match(command[0]):
            raise AuditError(f"command executable is not an absolute path: {name}")
        properties = test.get("properties", [])
        if not isinstance(properties, list) or any(not isinstance(x, dict) or "name" not in x or "value" not in x for x in properties):
            raise AuditError(f"malformed properties: {name}")
        cwd = [x["value"] for x in properties if x["name"] == "WORKING_DIRECTORY"]
        if len(cwd) != 1 or not isinstance(cwd[0], str) or not WIN_ABS.match(cwd[0]):
            raise AuditError(f"missing or ambiguous absolute WORKING_DIRECTORY: {name}")
        qt_output = bundled_qttest_output(test, logical_root)
        for field, value in (("command", command), ("properties", properties)):
            for s in walk_strings(value):
                if field == "command" and qt_output is not None and s == command[4]:
                    s = qt_output  # Strip only the reviewed QtTest ",txt" format suffix.
                for ref in absolute_references(s):
                    rel = to_relative(ref, logical_root)
                    if rel == ".":
                        actual = root
                    else:
                        check_windows_relative(rel, logical_root)
                        actual = root.joinpath(*rel.split("/"))
                    exists = actual.exists()
                    exception = (name, ntpath.normcase(ntpath.normpath(ref)))
                    approved = {ntpath.normcase(ntpath.normpath(v)) for v in allow.get(name, []) if isinstance(v, str)}
                    if exists and qt_output is not None and ntpath.normcase(ntpath.normpath(ref)) == ntpath.normcase(ntpath.normpath(qt_output)) and ntpath.normcase(ntpath.normpath(ref)) in approved:
                        used.add(exception)
                    if not exists:
                        if ntpath.normcase(ntpath.normpath(ref)) not in approved:
                            raise AuditError(f"missing referenced path in {name}: {ref}")
                        if field == "command" and ref == command[0] or ref == cwd[0]:
                            raise AuditError(f"test executable or working directory cannot be a future output: {name}")
                        used.add(exception)
                    refs.append({"test": name, "field": field, "path": ref, "exists": exists})
        if not root.joinpath(*to_relative(command[0], logical_root).split("/")).is_file():
            raise AuditError(f"test executable is missing or not a file: {name}")
        if not root.joinpath(*to_relative(cwd[0], logical_root).split("/")).is_dir():
            raise AuditError(f"working directory is missing or not a directory: {name}")
    backtrace = doc.get("backtraceGraph", {})
    if not isinstance(backtrace, dict) or not isinstance(backtrace.get("files", []), list):
        raise AuditError("malformed CTest backtrace file list")
    for value in backtrace.get("files", []):
        if not isinstance(value, str):
            raise AuditError("malformed CTest backtrace file path")
        for ref in absolute_references(value):
            rel = to_relative(ref, logical_root)
            check_windows_relative(rel, logical_root)
            if not root.joinpath(*rel.split("/")).is_file():
                raise AuditError(f"missing referenced CTest backtrace source: {ref}")
            refs.append({"test": None, "field": "backtraceGraph", "path": ref, "exists": True})
    for test, paths in allow.items():
        for path in paths:
            if not isinstance(path, str):
                raise AuditError("allowed output path must be a string")
            to_relative(path, logical_root)
            key = (test, ntpath.normcase(ntpath.normpath(path)))
            if key not in used:
                raise AuditError(f"stale or unused output exception: {test}: {path}")
    return {"test_count": len(names), "path_reference_count": len(refs), "references": refs}


def audit_results(discovery: Path, junit: Path):
    doc = read_json(discovery)
    tests = doc.get("tests") if isinstance(doc, dict) else None
    if not isinstance(doc, dict) or doc.get("kind") != "ctestInfo" or not isinstance(tests, list) or not tests:
        raise AuditError("invalid discovery")
    expected = [x.get("name") for x in tests]
    if any(not isinstance(x, str) or not x for x in expected) or len(expected) != len(set(expected)):
        raise AuditError("invalid or duplicate discovered names")
    tree = ET.parse(junit)
    cases = list(tree.getroot().iter("testcase"))
    observed = [x.get("name") for x in cases]
    if collections.Counter(expected) != collections.Counter(observed):
        missing = list((collections.Counter(expected) - collections.Counter(observed)).elements())
        extra = list((collections.Counter(observed) - collections.Counter(expected)).elements())
        raise AuditError(f"JUnit/discovery mismatch, missing={missing[:20]!r}, extra={extra[:20]!r}")
    top_skips, failures, nested, truncated, case_results = [], [], [], [], []
    for case in cases:
        name = case.get("name")
        status = case.get("status")
        if status not in ("run", "fail", "notrun", "disabled"):
            raise AuditError(f"unknown or missing CTest JUnit status for {name}: {status!r}")
        skipped = case.find("skipped")
        failure = case.find("failure")
        error = case.find("error")
        if (any(len(case.findall(tag)) > 1 for tag in ("skipped", "failure", "error")) or
                (status == "run" and (skipped is not None or failure is not None or error is not None)) or
                (status == "fail" and skipped is not None) or
                (status in ("notrun", "disabled") and (failure is not None or error is not None)) or
                (status == "disabled" and skipped is not None)):
            raise AuditError(f"contradictory or duplicated CTest JUnit outcome for {name}")
        reason = (skipped.get("message", "") if skipped is not None else "")
        if status == "disabled":
            category = "disabled"
        elif status == "notrun" or skipped is not None:
            category = ("conditional_skip" if reason.startswith(("SKIP_RETURN_CODE=", "SKIP_REGULAR_EXPRESSION="))
                        else "not_run")
        elif status == "fail" or failure is not None or error is not None:
            category = "failure"
        else:
            category = "pass"
        if category in ("disabled", "conditional_skip", "not_run"):
            top_skips.append(name)
        if status == "fail" or failure is not None or error is not None:
            failures.append(name)
            if not reason:
                detail = failure if failure is not None else error
                reason = detail.get("message", "") if detail is not None else "CTest status=fail"
            category = "failure"
        case_results.append({"test": name, "ctest_status": status, "category": category, "reason": reason})
        out = "\n".join(case.itertext())
        lowered = out.casefold()
        if "test output was removed" in lowered or "exceeds the threshold" in lowered:
            truncated.append(name)
        found = set()
        qt_summary = 0
        gtest_summary = 0
        for line in out.splitlines():
            match = GTEST_SKIP.match(line.strip())
            if match:
                found.add("gtest:" + match.group(1))
            match = GTEST_SKIP_TOTAL.match(line.strip())
            if match:
                gtest_summary = max(gtest_summary, int(match.group(1)))
            match = QT_SKIP.match(line.strip())
            if match:
                found.add("qt:" + match.group(1))
            match = QT_TOTALS.match(line.strip())
            if match:
                qt_summary = max(qt_summary, int(match.group(1)))
        gtest_found = sum(x.startswith("gtest:") for x in found)
        qt_found = sum(x.startswith("qt:") for x in found)
        if gtest_summary > gtest_found:
            found.add(f"gtest:unidentified_skip_count={gtest_summary - gtest_found}")
        if qt_summary > qt_found:
            found.add(f"qt:unidentified_skip_count={qt_summary - qt_found}")
        for entry in sorted(found):
            nested.append({"test": name, "case": entry})
    return {"test_count": len(cases), "case_results": case_results,
            "top_level_skips": top_skips, "failures": failures, "nested_skips": nested,
            "truncated_outputs": truncated,
            "complete_without_skips_or_failures": not (top_skips or failures or nested or truncated)}


def space_estimate(compressed, unpacked, host_free, guest_free, run_extra, host_reserve, guest_reserve, host_copies):
    values = (compressed, unpacked, host_free, guest_free, run_extra, host_reserve, guest_reserve)
    if any(x < 0 for x in values) or not compressed or not unpacked or host_copies < 1:
        raise AuditError("space figures must be non-negative, with positive compressed/unpacked bytes and host copies")
    host_need = compressed * host_copies + host_reserve
    guest_need = compressed + unpacked + run_extra + guest_reserve
    return {"host_needed_bytes": host_need, "host_free_bytes": host_free, "host_sufficient": host_need <= host_free,
            "guest_needed_bytes": guest_need, "guest_free_bytes": guest_free, "guest_sufficient": guest_need <= guest_free,
            "assumptions": {"host_simultaneous_archive_copies": host_copies, "guest_archive_copies": 1,
                            "run_extra_bytes": run_extra, "host_reserve_bytes": host_reserve, "guest_reserve_bytes": guest_reserve}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="op", required=True)
    p = sub.add_parser("stage"); p.add_argument("--plan", type=Path, required=True); p.add_argument("--staging", type=Path, required=True); p.add_argument("--logical-root", required=True)
    p = sub.add_parser("capture"); p.add_argument("--root", type=Path, required=True); p.add_argument("--logical-root", required=True); p.add_argument("--provenance", type=Path, required=True); p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser("verify"); p.add_argument("--root", type=Path, required=True); p.add_argument("--manifest", type=Path, required=True); p.add_argument("--expected-manifest-sha256", required=True); p.add_argument("--expected-root", required=True); p.add_argument("--expected-source-sha", required=True); p.add_argument("--expected-source-tree", required=True); p.add_argument("--expected-config", required=True); p.add_argument("--require-mtime", action="store_true")
    p = sub.add_parser("discovery"); p.add_argument("--root", type=Path, required=True); p.add_argument("--logical-root", required=True); p.add_argument("--discovery", type=Path, required=True); p.add_argument("--allowed-outputs", type=Path); p.add_argument("--expected-config", required=True); p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser("results"); p.add_argument("--discovery", type=Path, required=True); p.add_argument("--junit", type=Path, required=True); p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser("space");
    for option in ("compressed", "unpacked", "host-free", "guest-free", "run-extra", "host-reserve", "guest-reserve", "host-copies"):
        p.add_argument("--" + option, type=int, required=True)
    args = parser.parse_args()
    try:
        if args.op == "stage": result = stage_allowlisted(args.plan, args.staging, windows_root(args.logical_root))
        elif args.op == "capture": result = create_manifest(args.root, windows_root(args.logical_root), args.provenance, args.output)
        elif args.op == "verify": result = verify_manifest(args.root, args.manifest, args.require_mtime, args.expected_manifest_sha256, args.expected_root, args.expected_source_sha, args.expected_source_tree, args.expected_config)
        elif args.op == "discovery":
            result = audit_discovery(args.root, windows_root(args.logical_root), args.discovery, args.allowed_outputs, args.expected_config); write_json(args.output, result)
        elif args.op == "results":
            result = audit_results(args.discovery, args.junit); write_json(args.output, result)
            if not result["complete_without_skips_or_failures"]:
                print(json.dumps(result, ensure_ascii=False)); return 2
        else:
            result = space_estimate(args.compressed, args.unpacked, args.host_free, args.guest_free, args.run_extra, args.host_reserve, args.guest_reserve, args.host_copies)
            if not (result["host_sufficient"] and result["guest_sufficient"]):
                print(json.dumps(result, ensure_ascii=False)); return 2
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (AuditError, OSError, ValueError, KeyError, TypeError, ET.ParseError) as exc:
        print(f"native bundle audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
