from __future__ import annotations

import hashlib
import re
import subprocess
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from fincrime.monitoring.drift import PSIDriftResult, is_drift_detected

_GIT_SHA_REGEX = re.compile(r"^[0-9a-f]{40}$")
_HEX64_REGEX = re.compile(r"^[0-9a-f]{64}$")

MANDATORY_INVENTORIES: dict[str, tuple[str, ...]] = {
    "RESEARCH_RELEASE": (
        "dataset",
        "split",
        "feature_config",
        "model_weights",
        "trace_report",
    ),
    "FULL_PRODUCT_RELEASE": (
        "dataset",
        "split",
        "feature_config",
        "model_weights",
        "trace_report",
        "agent_eval_report",
        "streaming_replay_log",
        "monitoring_drift_report",
    ),
}


def get_mandatory_inventory(status: str) -> tuple[str, ...]:
    """Return the mandatory artifact names required for the specified release status."""
    if status not in MANDATORY_INVENTORIES:
        raise ValueError(f"Unknown release status: '{status}'")
    return MANDATORY_INVENTORIES[status]


def get_repo_git_sha() -> str:
    """Derive the current commit 40-character lowercase hexadecimal git SHA from the repository."""
    try:
        out = (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                text=True,
                stderr=subprocess.PIPE,
            )
            .strip()
            .lower()
        )
    except (subprocess.SubprocessError, OSError) as exc:
        raise RuntimeError(f"Failed to derive git SHA from repository: {exc}") from exc
    if not _GIT_SHA_REGEX.match(out):
        raise ValueError(f"Derived invalid git SHA from HEAD: '{out}'")
    return out


class ReleaseManifest(BaseModel):
    """Immutable release manifest with exact artifact inventory and verified provenance."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    status: Literal["RESEARCH_RELEASE", "FULL_PRODUCT_RELEASE"]
    git_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    artifact_hashes: tuple[tuple[str, str], ...] = Field(min_length=1)
    psi_drift_result: PSIDriftResult
    actual_cash_cost_vnd: int = Field(ge=0)
    tests_passed: bool
    known_limitations: tuple[str, ...]

    @field_validator("artifact_hashes")
    @classmethod
    def validate_hashes(cls, v: tuple[tuple[str, str], ...]) -> tuple[tuple[str, str], ...]:
        names: set[str] = set()
        for name, h in v:
            if not name.strip():
                raise ValueError("Artifact name must not be blank")
            if name in names:
                raise ValueError(f"Duplicate artifact name '{name}' in manifest")
            names.add(name)
            if not _HEX64_REGEX.match(h):
                raise ValueError(f"Invalid lowercase SHA-256 '{h}' for artifact '{name}'")
        if v != tuple(sorted(v, key=lambda x: x[0])):
            raise ValueError("artifact_hashes must be sorted by name")
        return v

    @model_validator(mode="after")
    def validate_exact_status_inventory(self) -> ReleaseManifest:
        expected_names = set(get_mandatory_inventory(self.status))
        actual_names = self.artifact_names
        if actual_names != expected_names:
            raise ValueError(
                f"ReleaseManifest artifact_names {actual_names} do not match exact mandatory inventory {expected_names} for status '{self.status}'"
            )
        return self

    def get_hash(self, name: str) -> str | None:
        """Retrieve the SHA-256 hash for a specific artifact name, or None if not present."""
        for k, v in self.artifact_hashes:
            if k == name:
                return v
        return None

    @property
    def artifact_names(self) -> set[str]:
        """Return the set of artifact names present in the manifest."""
        return {k for k, _ in self.artifact_hashes}


def hash_file_sha256(path: Path) -> str:
    """Compute the lowercase 64-character hexadecimal SHA-256 hash of a file."""
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Artifact file not found: {path}")
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().lower()


def build_release_manifest(
    status: Literal["RESEARCH_RELEASE", "FULL_PRODUCT_RELEASE"],
    artifacts: Mapping[str, Path],
    psi_drift_result: PSIDriftResult,
    actual_cash_cost_vnd: int,
    tests_passed: bool,
    known_limitations: tuple[str, ...],
    sha_resolver: Callable[[], str] = get_repo_git_sha,
) -> ReleaseManifest:
    """Build a validated ReleaseManifest enforcing exact inventory matching and SHA hashing."""
    final_sha = sha_resolver().lower()
    if not _GIT_SHA_REGEX.match(final_sha):
        raise ValueError(
            f"Invalid git_sha from resolver: must be 40-character lowercase hex, got '{final_sha}'"
        )

    mandatory = set(get_mandatory_inventory(status))
    supplied = set(artifacts.keys())

    missing = mandatory - supplied
    if missing:
        raise ValueError(
            f"Missing mandatory release artifacts: {sorted(missing)} for status '{status}'"
        )

    extra = supplied - mandatory
    if extra:
        raise ValueError(
            f"Unexpected extra release artifacts: {sorted(extra)} for status '{status}' (exact allowed: {sorted(mandatory)})"
        )

    hashes = {name: hash_file_sha256(path) for name, path in artifacts.items()}
    return ReleaseManifest(
        status=status,
        git_sha=final_sha,
        artifact_hashes=tuple(sorted(hashes.items(), key=lambda x: x[0])),
        psi_drift_result=psi_drift_result,
        actual_cash_cost_vnd=actual_cash_cost_vnd,
        tests_passed=tests_passed,
        known_limitations=known_limitations,
    )


def verify_release_manifest(
    manifest: ReleaseManifest,
    artifacts: Mapping[str, Path],
    sha_resolver: Callable[[], str] = get_repo_git_sha,
) -> bool:
    """Verify that a ReleaseManifest matches disk artifacts, repository git SHA, tests, and drift bounds."""
    try:
        target_sha = sha_resolver().lower()
        if not _GIT_SHA_REGEX.match(target_sha):
            return False
        if manifest.git_sha != target_sha:
            return False

        mandatory = set(get_mandatory_inventory(manifest.status))
        if set(artifacts.keys()) != mandatory or manifest.artifact_names != mandatory:
            return False
        if not manifest.tests_passed:
            return False
        if manifest.psi_drift_result.drift_detected:
            return False
        if is_drift_detected(manifest.psi_drift_result.psi, manifest.psi_drift_result.threshold):
            return False

        for name, path in artifacts.items():
            expected = manifest.get_hash(name)
            if expected is None:
                return False
            try:
                actual = hash_file_sha256(path)
            except OSError:
                return False
            if actual != expected:
                return False

        return True
    except Exception:  # noqa: BLE001
        return False
