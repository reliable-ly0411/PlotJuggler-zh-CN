# SPDX-License-Identifier: MPL-2.0
"""Narrow classification and RCC evidence for Windows review-only artifacts.

The caller must independently supply immutable run/source provenance. A candidate
hash below is used solely to run the existing privacy scanner over previously
reviewed public source-file strings whose Conan cache *hex component* changed.
It is not an accepted production identity and cannot make release gates pass.
"""
import copy
import hashlib
from pathlib import Path
import re
import struct

NAMES = ("DataLoadParquet.dll", "ToolboxMosaico.dll", "ProtobufParser.dll")
CACHE = re.compile(r"/\.conan2/p/(?:b/)?[a-z][a-z0-9]*?([0-9a-f]{13})(?=/)")
QRC_EXPECTED = {"qrc_mosaico_resources.cpp": 1, "qrc_qcodeeditor_resources.cpp": 5}
EPOCH_MIN, EPOCH_MAX = 1577836800000, 2524608000000


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(literal):
    # ASCII-only Windows equivalence; do not normalize path segments.
    if not literal.isascii():
        return None
    value = literal.translate(str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ\\", "abcdefghijklmnopqrstuvwxyz/"))
    matches = list(CACHE.finditer(value))
    if len(matches) != 1:
        return None
    match = matches[0]
    return value[:match.start(1)] + "{cache}" + value[match.end(1):]


def observed_public_literals(data, old_literals):
    from package_privacy import PRIVATE_PATH
    keys = {canonical(value) for value in old_literals}
    if None in keys:
        raise ValueError("Invalid reviewed literal")
    seen = set()
    # All scanner views, including both UTF-16 byte alignments. A candidate is
    # bounded and must terminate at NUL; never normalize incomplete paths.
    for text in (data.decode("latin1"), data.decode("utf-16le", errors="ignore"),
                 data[1:].decode("utf-16le", errors="ignore")):
        for match in PRIVATE_PATH.finditer(text):
            if match.start() and text[match.start() - 1] != "\0":
                continue
            end = text.find("\0", match.start(), min(len(text), match.start() + 4097))
            if end < 0:
                continue
            value = text[match.start():end]
            if canonical(value) in keys:
                seen.add(value)
    return sorted(seen)


def unknown_marker_count(data, literals):
    from package_privacy import PRIVATE_PATH
    count = 0
    for text in (data.decode("latin1"), data.decode("utf-16le", errors="ignore"),
                 data[1:].decode("utf-16le", errors="ignore")):
        for literal in literals:
            text = re.sub(r"(?<![^\x00])" + re.escape(literal + "\0"), "\0", text)
        count += sum(1 for _ in PRIVATE_PATH.finditer(text))
    return count


def unknown_public_path_hashes(data, old_literals, observed):
    """Hash normalized complete paths only under an already reviewed CI root/package.

    Hashes support offline source-tree comparison, not classification or approval.
    Strings must be ASCII, NUL-bounded, and contain ordinary path components.
    """
    from package_privacy import PRIVATE_PATH
    prefixes = set()
    for literal in old_literals:
        key = canonical(literal)
        if key is None:
            raise ValueError("Invalid reviewed literal")
        marker = key.index("{cache}") + len("{cache}")
        prefixes.add(key[:marker] + "/")
    known = {canonical(value) for value in observed}
    hashes = set()
    for text in (data.decode("latin1"), data.decode("utf-16le", errors="ignore"),
                 data[1:].decode("utf-16le", errors="ignore")):
        for match in PRIVATE_PATH.finditer(text):
            start = match.start()
            if start and text[start - 1] != "\0":
                continue
            end = text.find("\0", start, min(len(text), start + 4097))
            if end < 0:
                continue
            value = text[start:end]
            key = canonical(value)
            if key is None or key in known or not any(key.startswith(prefix) for prefix in prefixes):
                continue
            suffix = key.split("{cache}/", 1)[1]
            parts = suffix.split("/")
            if not parts or any(part in ("", ".", "..") or
                                not re.fullmatch(r"[a-z0-9_.+\-]+", part) for part in parts):
                continue
            hashes.add(sha(key.encode("ascii")))
    return sorted(hashes)


def candidate_privacy(data, name, records, check_metadata):
    if name not in NAMES:
        raise ValueError("Not a review-scope DLL")
    temporary = copy.deepcopy(records)
    source_records = temporary.setdefault("public_ci_source_records", {})
    if name == "ProtobufParser.dll":
        old = [literal for record in records["public_ci_source_records"].values()
               for literal in record["nul_terminated_literals"]]
        policy = source_records[name] = {"nul_terminated_literals": old}
    else:
        policy = source_records[name]
        old = policy["nul_terminated_literals"]
    literals = observed_public_literals(data, old)
    # Prevent the scanner's literal replacement from masking a suffix inside a
    # longer string when the same literal is also present at a valid boundary.
    for text in (data.decode("latin1"), data.decode("utf-16le", errors="ignore"),
                 data[1:].decode("utf-16le", errors="ignore")):
        for literal in literals:
            needle = literal + "\0"
            start = 0
            while True:
                pos = text.find(needle, start)
                if pos < 0:
                    break
                if pos and text[pos - 1] != "\0":
                    raise ValueError("Ambiguous source literal boundary")
                start = pos + len(needle)
    # This exact digest is a quarantine scan aid, never a production approval.
    policy["observed_plugin_sha256"] = sha(data)
    policy.pop("content_fingerprint", None)
    policy["nul_terminated_literals"] = literals
    markers = check_metadata(data, name, temporary)
    return literals, markers, temporary


def rdata_bounds(data):
    if len(data) < 64 or data[:2] != b"MZ":
        raise ValueError("Not a PE file")
    pe = struct.unpack_from("<I", data, 60)[0]
    if pe < 64 or data[pe:pe + 4] != b"PE\0\0":
        raise ValueError("Not a recognized PE file")
    if pe + 24 > len(data):
        raise ValueError("Truncated PE header")
    machine, count = struct.unpack_from("<HH", data, pe + 4)
    optional_size, flags = struct.unpack_from("<HH", data, pe + 20)
    optional = pe + 24
    if optional + optional_size > len(data):
        raise ValueError("Truncated PE optional header")
    if (machine != 0x8664 or not flags & 0x2000 or not 1 <= count <= 96 or
            optional_size < 168 or struct.unpack_from("<H", data, optional)[0] != 0x20b):
        raise ValueError("Not a reviewed x64 PE DLL form")
    table = optional + optional_size
    if table + count * 40 > len(data):
        raise ValueError("Truncated PE sections")
    found = []
    for i in range(count):
        at = table + i * 40
        size, raw = struct.unpack_from("<II", data, at + 16)
        if raw + size > len(data):
            raise ValueError("Truncated PE section data")
        if data[at:at + 8].rstrip(b"\0") == b".rdata":
            found.append((raw, raw + size))
    if len(found) != 1:
        raise ValueError("Ambiguous PE .rdata")
    return found[0]


def qrc_struct(source):
    versions = set(re.findall(r"int version = ([0-9]+);", source))
    if versions not in ({"2"}, {"3"}):
        raise ValueError("Not Qt5 RCC v2/v3 generated source")
    matches = re.findall(r"static const unsigned char qt_resource_struct\[\] = \{(.*?)\};", source, re.S)
    if len(matches) != 1:
        raise ValueError("Ambiguous Qt RCC struct")
    body = re.sub(r"/\*.*?\*/|//[^\n]*", "", matches[0], flags=re.S)
    if re.sub(r"0x[0-9a-fA-F]{1,2}|[,\s]", "", body):
        raise ValueError("Unrecognized Qt RCC byte initializer")
    blob = bytes(int(token, 16) for token in re.findall(r"0x([0-9a-fA-F]{1,2})", body))
    if not blob or len(blob) > 65536 or len(blob) % 22:
        raise ValueError("Unrecognized Qt RCC node table")
    mtimes = []
    for at in range(0, len(blob), 22):
        flags = struct.unpack_from(">H", blob, at + 4)[0]
        mtime = struct.unpack_from(">Q", blob, at + 14)[0]
        if flags not in (0, 1, 2, 4):
            raise ValueError("Unrecognized Qt RCC node flags")
        if flags == 2:
            if mtime != 0:
                raise ValueError("Nonzero Qt RCC directory timestamp")
        elif not EPOCH_MIN <= mtime < EPOCH_MAX:
            raise ValueError("Invalid Qt RCC file timestamp")
        else:
            mtimes.append(at + 14)
    return blob, mtimes, int(next(iter(versions)))


def derive_qrc_offsets(data, sources):
    """Derive six fields from exact generated struct blobs, never scan epochs."""
    low, high = rdata_bounds(data)
    offsets, provenance, found = [], [], set()
    for relative, source_bytes in sources:
        basename = Path(relative).name
        if basename not in QRC_EXPECTED:
            raise ValueError("Generated source outside explicit review scope")
        if basename in found:
            raise ValueError("Duplicate generated resource source")
        # Decode bytes directly: read_text() normalizes CRLF on Windows and
        # would mislabel the original generated file's SHA256 provenance.
        source = source_bytes.decode("utf-8")
        blob, mtimes, version = qrc_struct(source)
        if len(mtimes) != QRC_EXPECTED[basename]:
            raise ValueError("Unexpected resource file count")
        start = data.find(blob, low, high)
        if start < 0 or data.find(blob, start + 1, high) >= 0:
            raise ValueError("Resource struct must occur exactly once in .rdata")
        positions = [start + at for at in mtimes]
        offsets.extend(positions)
        found.add(basename)
        provenance.append({"generated_source": relative,
                           "generated_source_sha256": sha(source_bytes),
                           "rcc_format_version": version, "struct_bytes": len(blob),
                           "struct_sha256": sha(blob), "struct_hex": blob.hex(),
                           "struct_offset": start, "node_timestamp_offsets": mtimes,
                           "dll_timestamp_offsets": positions})
    if found != set(QRC_EXPECTED) or len(offsets) != 6 or len(set(offsets)) != 6:
        raise ValueError("Expected two known resource structs and six timestamps")
    return sorted(offsets), provenance
