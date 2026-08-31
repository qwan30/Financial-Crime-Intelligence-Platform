from __future__ import annotations

import zipfile
from hashlib import sha256
from pathlib import Path

import pytest

from fincrime.data.archive import extract_verified_members


def test_extract_rejects_path_traversal_member(tmp_path: Path) -> None:
    archive = tmp_path / "source.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("../escape.csv", "x")
    with pytest.raises(ValueError, match="unsafe archive member"):
        extract_verified_members(
            archive,
            sha256(archive.read_bytes()).hexdigest(),
            {"transactions.csv"},
            tmp_path / "out",
            1,
            1024,
        )


def test_extract_rejects_absolute_path_member(tmp_path: Path) -> None:
    archive = tmp_path / "source.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("/root/escape.csv", "x")
    with pytest.raises(ValueError, match="unsafe archive member|unexpected archive member"):
        extract_verified_members(
            archive,
            sha256(archive.read_bytes()).hexdigest(),
            {"transactions.csv"},
            tmp_path / "out",
            1,
            1024,
        )


def test_extract_rejects_checksum_mismatch(tmp_path: Path) -> None:
    archive = tmp_path / "source.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("transactions.csv", "data")
    with pytest.raises(ValueError, match="archive checksum mismatch"):
        extract_verified_members(
            archive,
            "0" * 64,
            {"transactions.csv"},
            tmp_path / "out",
            1,
            1024,
        )


def test_extract_rejects_unexpected_member(tmp_path: Path) -> None:
    archive = tmp_path / "source.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("unauthorized.csv", "data")
    with pytest.raises(ValueError, match="unexpected archive member"):
        extract_verified_members(
            archive,
            sha256(archive.read_bytes()).hexdigest(),
            {"transactions.csv"},
            tmp_path / "out",
            1,
            1024,
        )


def test_extract_rejects_max_files_overflow(tmp_path: Path) -> None:
    archive = tmp_path / "source.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("transactions.csv", "data1")
        output.writestr("accounts.csv", "data2")
    with pytest.raises(ValueError, match="archive exceeds extraction quota"):
        extract_verified_members(
            archive,
            sha256(archive.read_bytes()).hexdigest(),
            {"transactions.csv", "accounts.csv"},
            tmp_path / "out",
            max_files=1,
            max_bytes=1024,
        )


def test_extract_rejects_max_bytes_overflow(tmp_path: Path) -> None:
    archive = tmp_path / "source.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("transactions.csv", "x" * 2000)
    with pytest.raises(ValueError, match="archive exceeds extraction quota"):
        extract_verified_members(
            archive,
            sha256(archive.read_bytes()).hexdigest(),
            {"transactions.csv"},
            tmp_path / "out",
            max_files=5,
            max_bytes=1000,
        )


def test_extract_successful_tiny_member(tmp_path: Path) -> None:
    archive = tmp_path / "source.zip"
    content = "sourceNodeId,targetNodeId,value,time\n1,2,10.0,0\n"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("transactions.csv", content)

    out_dir = tmp_path / "extracted"
    extracted_paths = extract_verified_members(
        archive,
        sha256(archive.read_bytes()).hexdigest(),
        {"transactions.csv"},
        out_dir,
        max_files=5,
        max_bytes=10_000,
    )
    assert len(extracted_paths) == 1
    assert extracted_paths[0].is_file()
    assert extracted_paths[0].read_text(encoding="utf-8") == content
