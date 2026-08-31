from __future__ import annotations

import shutil
from pathlib import Path, PurePosixPath
from zipfile import ZipFile, ZipInfo

from fincrime.data.provenance import sha256_file


def extract_verified_members(
    archive: Path,
    expected_sha256: str,
    allowed_members: set[str],
    destination: Path,
    max_files: int,
    max_bytes: int,
) -> tuple[Path, ...]:
    if sha256_file(archive) != expected_sha256:
        raise ValueError("archive checksum mismatch")
    with ZipFile(archive) as source:
        members = [member for member in source.infolist() if not member.is_dir()]
        if len(members) > max_files or sum(member.file_size for member in members) > max_bytes:
            raise ValueError("archive exceeds extraction quota")
        safe_members: list[tuple[PurePosixPath, ZipInfo]] = []
        for member in members:
            name = PurePosixPath(member.filename)
            if name.is_absolute() or ".." in name.parts:
                raise ValueError("unsafe archive member")
            if name.as_posix() not in allowed_members:
                raise ValueError("unexpected archive member")
            safe_members.append((name, member))
        root = destination.resolve()
        root.mkdir(parents=True, exist_ok=True)
        outputs: list[Path] = []
        for name, member in safe_members:
            output = (root / name).resolve()
            if root not in output.parents and output != root:
                raise ValueError("unsafe archive member")
            output.parent.mkdir(parents=True, exist_ok=True)
            with source.open(member) as input_file, output.open("xb") as output_file:
                shutil.copyfileobj(input_file, output_file)
            outputs.append(output)
        return tuple(outputs)
