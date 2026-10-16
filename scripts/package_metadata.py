# SPDX-License-Identifier: MPL-2.0
"""Read container/compression metadata without executing the packaged application."""
from pathlib import Path
import struct
import zipfile


def package_metadata(filename):
    path = Path(filename)
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as archive:
            return {"format": "ZIP", "compression_method_ids": sorted({m.compress_type for m in archive.infolist()})}
    if path.suffix == ".deb":
        members = []
        with path.open("rb") as source:
            assert source.read(8) == b"!<arch>\n"
            while header := source.read(60):
                assert len(header) == 60 and header[58:] == b"`\n"
                name = header[:16].decode("ascii").strip().rstrip("/")
                size = int(header[48:58])
                members.append({"name": name, "bytes": size})
                source.seek(size + size % 2, 1)
        return {"format": "DEB/ar", "members": members}
    if path.suffix == ".AppImage":
        # The type-2 runtime precedes the SquashFS superblock (normally < 1 MiB).
        with path.open("rb") as source:
            data = source.read(16 * 1024 * 1024)
        offset = 0
        while True:
            offset = data.find(b"hsqs", offset)
            assert offset >= 0, "SquashFS superblock missing"
            if (offset + 96 <= len(data) and struct.unpack_from("<H", data, offset + 28)[0] == 4
                    and 96 < struct.unpack_from("<Q", data, offset + 40)[0] <= path.stat().st_size - offset):
                break
            offset += 4
        method = struct.unpack_from("<H", data, offset + 20)[0]
        return {"format": "AppImage/SquashFS", "squashfs_offset": offset,
                "compression": {1: "gzip", 2: "lzma", 3: "lzo", 4: "xz", 5: "lz4", 6: "zstd"}.get(method, str(method)),
                "block_bytes": struct.unpack_from("<I", data, offset + 12)[0]}
    return {"format": "Qt IFW executable" if path.suffix == ".exe" else path.suffix}
