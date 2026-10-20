"""Bounded SNG and ZIP extraction. SNG layout: mdsitton/SngFileFormat."""
import configparser
import re
import struct
import zipfile
from pathlib import Path

import numpy as np

MAX_BYTES = 1024 * 1024 * 1024
RESERVED = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", re.I)


def safe_target(root: Path, name: str) -> Path:
    parts = name.replace("\\", "/").split("/")
    if not parts or any(
        p in {"", ".", ".."} or p.endswith((" ", "."))
        or re.search(r'[<>:"|?*\x00-\x1f]', p) or RESERVED.match(p)
        for p in parts
    ):
        raise ValueError(f"Unsafe archive path: {name!r}")
    target = root.joinpath(*parts)
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError("Archive path escapes destination")
    return target


def unpack_sng(source: Path, dest: Path) -> None:
    size = source.stat().st_size
    if size > MAX_BYTES:
        raise ValueError("SNG exceeds 1 GiB limit")
    with source.open("rb") as f:
        def read(n):
            if n < 0 or n > MAX_BYTES:
                raise ValueError("Invalid SNG field length")
            data = f.read(n)
            if len(data) != n:
                raise ValueError("Truncated SNG")
            return data

        def integer(fmt):
            return struct.unpack(fmt, read(struct.calcsize(fmt)))[0]

        if read(6) != b"SNGPKG" or integer("<I") != 1:
            raise ValueError("Unsupported SNG signature/version")
        mask = read(16)
        metadata_end = integer("<Q") + f.tell()
        count = integer("<Q")
        if count > 10000 or metadata_end > size:
            raise ValueError("Invalid SNG metadata")
        metadata = {}
        for _ in range(count):
            key = read(integer("<i")).decode("utf-8")
            value = read(integer("<i")).decode("utf-8")
            if not re.fullmatch(r"[A-Za-z0-9_]+", key) or any(c in value for c in "\r\n\0"):
                raise ValueError("Invalid SNG metadata string")
            metadata[key] = value
        if f.tell() != metadata_end:
            raise ValueError("Invalid metadata section length")
        index_end = integer("<Q") + f.tell()
        count = integer("<Q")
        if count > 10000 or index_end > size:
            raise ValueError("Invalid SNG index")
        entries, names, total = [], set(), 0
        for _ in range(count):
            name = read(integer("<B")).decode("utf-8")
            target = safe_target(dest, name)
            length, offset = integer("<Q"), integer("<Q")
            if name.casefold() in names or name.casefold() == "song.ini":
                raise ValueError("Duplicate SNG file")
            names.add(name.casefold())
            total += length
            entries.append((target, length, offset))
        if f.tell() != index_end or total > MAX_BYTES:
            raise ValueError("Invalid SNG file index")
        data_length = integer("<Q")
        start = f.tell()
        if start + data_length != size or total != data_length:
            raise ValueError("Invalid SNG data length")
        cursor = start
        for _, length, offset in sorted(entries, key=lambda e: e[2]):
            if offset != cursor or offset + length > size:
                raise ValueError("Invalid or overlapping SNG file range")
            cursor += length
        key = np.array([mask[i % 16] ^ i for i in range(256)], dtype=np.uint8)
        dest.mkdir(parents=True, exist_ok=True)
        for target, length, offset in entries:
            target.parent.mkdir(parents=True, exist_ok=True)
            f.seek(offset)
            with target.open("xb") as output:
                while length:
                    # Chunk length is a multiple of 256 except the final chunk.
                    block = read(min(length, 1024 * 1024))
                    output.write((np.frombuffer(block, dtype=np.uint8) ^
                                  np.resize(key, len(block))).tobytes())
                    length -= len(block)
        config = configparser.ConfigParser(interpolation=None)
        config["song"] = metadata
        with (dest / "song.ini").open("x", encoding="utf-8") as out:
            config.write(out)


def unpack_zip(source: Path, dest: Path) -> None:
    with zipfile.ZipFile(source) as archive:
        entries = archive.infolist()
        if len(entries) > 10000 or sum(e.file_size for e in entries) > MAX_BYTES:
            raise ValueError("ZIP exceeds extraction limits")
        seen = set()
        for entry in entries:
            target = safe_target(dest, entry.filename.rstrip("/"))
            if entry.filename.casefold() in seen or (entry.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("Duplicate ZIP path or symbolic link")
            seen.add(entry.filename.casefold())
            if entry.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry) as src, target.open("xb") as out:
                remaining = entry.file_size
                while block := src.read(min(1024 * 1024, remaining + 1)):
                    remaining -= len(block)
                    if remaining < 0:
                        raise ValueError("ZIP entry exceeds declared size")
                    out.write(block)
