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
            text = text.replace(literal + "\0", "\0")
        count += sum(1 for _ in PRIVATE_PATH.finditer(text))
    return count


def unknown_public_path_hashes(data, old_literals, observed):
    """Hash normalized complete paths only under an already reviewed CI root/package.

    Hashes support offline source-tree comparison, not classification or approval.
    Strings must be ASCII, NUL-bounded, and contain ordinary path components.
    """
    from package_privacy import PRIVATE_PATH
    if diagnostic_secret_present(diagnostic_views(data)):
        return []
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


# Diagnostic schema v1: SHA256 of ASCII-lowercase, slash-normalized full
# path with the cache's 13 hex characters replaced by the literal {cache}.
# Layout p/ versus p/b/ stays in the input; no unknown preceding bytes enter it.
DIAGNOSTIC_METHOD = "sha256-ascii-lower-slash-cache-token-v1"
REASONS = ("no_bounded_nul_end", "non_ascii", "outside_reviewed_root",
           "unknown_package", "invalid_cache_component", "invalid_components",
           "known_exact_literal", "eligible_unknown_public_path")
DIAGNOSTIC_CACHE = re.compile(r"/\.conan2/p/(?:b/)?([a-z][a-z0-9]*?)([0-9a-f]{13})/")


def diagnostic_views(data):
    return (data.decode("latin1"), data.decode("utf-16le", errors="ignore"),
            data[1:].decode("utf-16le", errors="ignore"))


def diagnostic_secret_present(views):
    from package_privacy import PRIVATE_PATH, GITHUB_TOKEN, PRIVATE_KEY, PERSONAL_CONTACT
    def contains_secret(text):
        return bool(GITHUB_TOKEN.search(text) or PRIVATE_KEY.search(text) or PERSONAL_CONTACT.search(text))
    for text in views:
        if contains_secret(text):
            return True
        # Conservative detection only: a marker may border a contact/token.
        # Do not report the marker, surrounding text, or this temporary view.
        augmented = PRIVATE_PATH.sub(lambda match: "\0" + match.group(), text)
        if contains_secret(augmented):
            return True
    return False


def path_diagnostics(data, old_literals):
    """Read-only marker counts and public path hashes; never authorize a DLL."""
    from package_privacy import PRIVATE_PATH
    keys = set()
    roots = set()
    pairs = set()
    for literal in old_literals:
        key = canonical(literal)
        if key is None:
            raise ValueError("Invalid reviewed literal")
        keys.add(key)
        normalized = literal.translate(str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ\\", "abcdefghijklmnopqrstuvwxyz/"))
        match = DIAGNOSTIC_CACHE.search(normalized)
        if match is None:
            raise ValueError("Invalid reviewed cache record")
        root = normalized[:match.start()]
        roots.add(root)
        pairs.add((root, match.group(1)))
    views = diagnostic_views(data)
    sensitive = diagnostic_secret_present(views)
    counts = {name: 0 for name in REASONS}
    boundary = {"nul_start": 0, "no_nul_start": 0}
    hashes = set()
    for text in views:
        for marker in PRIVATE_PATH.finditer(text):
            start = marker.start()
            boundary["nul_start" if not start or text[start - 1] == "\0" else "no_nul_start"] += 1
            end = text.find("\0", start, min(len(text), start + 4097))
            if end < 0:
                counts["no_bounded_nul_end"] += 1
                continue
            value = text[start:end]
            if not value.isascii():
                counts["non_ascii"] += 1
                continue
            normalized = value.translate(str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ\\", "abcdefghijklmnopqrstuvwxyz/"))
            root = next((r for r in roots if normalized.startswith(r + "/.conan2/")), None)
            if root is None:
                counts["outside_reviewed_root"] += 1
                continue
            match = DIAGNOSTIC_CACHE.match(normalized, len(root))
            if match is None:
                counts["invalid_cache_component"] += 1
                continue
            if (root, match.group(1)) not in pairs:
                counts["unknown_package"] += 1
                continue
            parts = normalized[match.end():].split("/")
            if any(part in ("", ".", "..") or not re.fullmatch(r"[a-z0-9_.+\-]+", part) for part in parts):
                counts["invalid_components"] += 1
                continue
            key = normalized[:match.start(2)] + "{cache}" + normalized[match.end(2):]
            counts["known_exact_literal" if key in keys else "eligible_unknown_public_path"] += 1
            if not sensitive:
                hashes.add(sha(key.encode("ascii")))
    return {"method": DIAGNOSTIC_METHOD, "hash_input": "full normalized path, cache hex replaced by {cache}; p/b retained",
            "count_semantics": "per PRIVATE_PATH match across latin1 and both UTF-16LE alignments; categories exclusive",
            "hashes_suppressed_for_secret": sensitive,
            "reason_counts": counts, "boundary_counts": boundary, "path_sha256": sorted(hashes)}


def rc5_shadow(data, name, records, old_literals, check_metadata):
    """Reproduce rc5 end-only literal discovery/scanner as diagnostics only."""
    views = diagnostic_views(data)
    keys = set()
    for literal in old_literals:
        # CACHE is normalized slash-only; rc5 also required original-case paths.
        # Build the rc5 pattern from the literal without case/slash normalization.
        pattern = re.compile(r"\.conan2[\\/]p[\\/](?:b[\\/])?([a-z][a-z0-9]*?)([0-9a-f]{13})(?=[\\/])")
        matches = list(pattern.finditer(literal))
        if len(matches) != 1:
            raise ValueError("Invalid reviewed literal")
        match = matches[0]
        keys.add(literal[:match.start(2)] + "{cache}" + literal[match.end(2):])
    pattern = re.compile(r"\.conan2[\\/]p[\\/](?:b[\\/])?([a-z][a-z0-9]*?)([0-9a-f]{13})(?=[\\/])")
    from package_privacy import PRIVATE_PATH
    literals = set()
    occurrences = 0
    for text in views:
        for marker in PRIVATE_PATH.finditer(text):
            end = text.find("\0", marker.start(), min(len(text), marker.start() + 4097))
            if end < 0:
                continue
            value = text[marker.start():end]
            matches = list(pattern.finditer(value))
            if len(matches) != 1:
                continue
            match = matches[0]
            key = value[:match.start(2)] + "{cache}" + value[match.end(2):]
            if key in keys:
                occurrences += 1
                literals.add(value)
    result = {"method": "rc5-end-only-shadow-v1", "matched_occurrences": occurrences,
              "passed": False, "rule": "No reviewed public source records observed"}
    if not literals:
        return result
    temporary = copy.deepcopy(records)
    policy = temporary.setdefault("public_ci_source_records", {}).setdefault(name, {})
    policy["observed_plugin_sha256"] = sha(data)
    policy["nul_terminated_literals"] = sorted(literals)
    policy.pop("content_fingerprint", None)
    try:
        check_metadata(data, name, temporary)
    except ValueError as error:
        for rule in ("Unapproved public-source binary content", "Unexpected GitHub credential material",
                     "Unexpected private-key material", "Unexpected personal contact", "Unexpected private path"):
            if str(error).startswith(rule + " in "):
                result["rule"] = rule
                break
        else:
            result["rule"] = "Package privacy scanner rejected file"
    else:
        result.update(passed=True, rule="none")
    return result


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
    # This exact digest is a quarantine scan aid, never a production approval.
    policy["observed_plugin_sha256"] = sha(data)
    policy.pop("content_fingerprint", None)
    policy["nul_terminated_literals"] = literals
    markers = check_metadata(data, name, temporary)
    # Inspect the residual with an independent temporary identity. The original
    # scan above always examines original bytes, including all secret checks.
    # Removing only reviewed literal+NUL can expose a sensitive adjacent prefix
    # whose regex boundary was obscured by the literal's drive letter.
    residual = data
    for literal in literals:
        for encoding in ("utf-16le", "ascii"):
            residual = residual.replace((literal + "\0").encode(encoding), "\0".encode(encoding))
    residual_policy = copy.deepcopy(temporary)
    local = residual_policy["public_ci_source_records"][name]
    local["observed_plugin_sha256"] = sha(residual)
    local["nul_terminated_literals"] = []
    local.pop("content_fingerprint", None)
    check_metadata(residual, name, residual_policy)
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
