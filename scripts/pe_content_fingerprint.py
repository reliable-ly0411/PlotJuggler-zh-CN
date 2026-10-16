# SPDX-License-Identifier: MPL-2.0
"""Content identity for reviewed x64 PE DLLs, excluding specific build timestamps.

All file bytes, including code, strings, resource data, headers and any overlay,
participate in SHA-256. Only COFF/debug timestamps and explicitly reviewed Qt RCC
mtime fields may vary. This is a content policy, not a PE signature verifier.
PE layout: https://learn.microsoft.com/en-us/windows/win32/debug/pe-format
Qt 5.15.2 timestamp layout: src/tools/rcc/rcc.cpp, writeDataInfo().
"""
import hashlib
import struct

METHOD = "pe-x64-reviewed-timestamps-v1"


def fingerprint(data, record):
    """Return the bounded canonical SHA-256, or None for an unrecognized layout."""
    try:
        if record.get("method") != METHOD or len(data) != record["file_bytes"]:
            return None
        if len(data) < 64 or data[:2] != b"MZ":
            return None
        pe = struct.unpack_from("<I", data, 60)[0]
        if pe < 64 or data[pe:pe + 4] != b"PE\0\0":
            return None
        machine, count = struct.unpack_from("<HH", data, pe + 4)
        optional_size, flags = struct.unpack_from("<HH", data, pe + 20)
        optional = pe + 24
        if machine != 0x8664 or not 1 <= count <= 96 or not flags & 0x2000:
            return None
        if optional_size < 168 or struct.unpack_from("<H", data, optional)[0] != 0x20b:
            return None
        if struct.unpack_from("<I", data, optional + 108)[0] < 7:
            return None
        table = optional + optional_size
        if table + 40 * count > len(data):
            return None
        sections = []
        for i in range(count):
            at = table + 40 * i
            virtual_size, rva, size, raw = struct.unpack_from("<IIII", data, at + 8)
            if raw + size > len(data):
                return None
            sections.append((data[at:at + 8].rstrip(b"\0"), rva, size, raw))

        def file_offset(rva, size):
            matches = [raw + rva - base for _, base, length, raw in sections
                       if base <= rva and rva + size <= base + length]
            if len(matches) != 1:
                raise ValueError("Ambiguous PE section")
            return matches[0]

        offsets = [(pe + 8, 4)]  # IMAGE_FILE_HEADER.TimeDateStamp
        rva, size = struct.unpack_from("<II", data, optional + 112 + 6 * 8)
        if not rva or not size or size % 28 or size > 28 * 16:
            return None
        debug = file_offset(rva, size)
        for at in range(debug, debug + size, 28):
            # Reviewed Release DLLs have only IMAGE_DEBUG_TYPE_POGO records.
            if struct.unpack_from("<I", data, at + 12)[0] != 13:
                return None
            offsets.append((at + 4, 4))
        qt_offsets = record.get("qt_rcc_mtime_offsets", [])
        if len(qt_offsets) > 16 or len(set(qt_offsets)) != len(qt_offsets):
            return None
        for at in qt_offsets:
            if not isinstance(at, int) or not any(
                    name == b".rdata" and raw <= at and at + 8 <= raw + size
                    for name, _, size, raw in sections):
                return None
            # A Qt resource timestamp is an unsigned big-endian epoch in ms.
            if not 1577836800000 <= struct.unpack_from(">Q", data, at)[0] < 2524608000000:
                return None
            offsets.append((at, 8))
        if any(a + length > b for (a, length), (b, _) in zip(
                sorted(offsets), sorted(offsets)[1:])):
            return None
        canonical = bytearray(data)
        for at, size in offsets:
            canonical[at:at + size] = b"\0" * size
        return hashlib.sha256(canonical).hexdigest()
    except (KeyError, TypeError, ValueError, struct.error, OverflowError):
        return None
