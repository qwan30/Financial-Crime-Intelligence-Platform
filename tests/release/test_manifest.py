from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from fincrime.monitoring.drift import PSIDriftResult
from fincrime.release.manifest import (
    MANDATORY_INVENTORIES,
    ReleaseManifest,
    build_release_manifest,
    get_mandatory_inventory,
    get_repo_git_sha,
    hash_file_sha256,
    verify_release_manifest,
)


def _create_dummy_files(tmp_path: Path, names: list[str]) -> dict[str, Path]:
    artifacts: dict[str, Path] = {}
    for name in names:
        p = tmp_path / f"{name}.json"
        p.write_text(f'{{"artifact": "{name}"}}', encoding="utf-8")
        artifacts[name] = p
    return artifacts


def test_get_repo_git_sha() -> None:
    sha = get_repo_git_sha()
    assert re.match(r"^[0-9a-f]{40}$", sha) is not None


def test_get_mandatory_inventory() -> None:
    research = get_mandatory_inventory("RESEARCH_RELEASE")
    assert research == (
        "dataset",
        "split",
        "feature_config",
        "model_weights",
        "trace_report",
    )

    full = get_mandatory_inventory("FULL_PRODUCT_RELEASE")
    assert full == (
        "dataset",
        "split",
        "feature_config",
        "model_weights",
        "trace_report",
        "agent_eval_report",
        "streaming_replay_log",
        "monitoring_drift_report",
    )

    with pytest.raises(ValueError, match="Unknown release status"):
        get_mandatory_inventory("INVALID_STATUS")


def test_build_and_verify_research_release(tmp_path: Path) -> None:
    req_names = list(get_mandatory_inventory("RESEARCH_RELEASE"))
    artifacts = _create_dummy_files(tmp_path, req_names)
    drift_res = PSIDriftResult(psi=0.02, threshold=0.1, drift_detected=False, bins=10)
    test_resolver = lambda: "b" * 40

    manifest = build_release_manifest(
        status="RESEARCH_RELEASE",
        artifacts=artifacts,
        psi_drift_result=drift_res,
        actual_cash_cost_vnd=50000,
        tests_passed=True,
        known_limitations=(),
        sha_resolver=test_resolver,
    )

    assert manifest.status == "RESEARCH_RELEASE"
    assert manifest.git_sha == "b" * 40
    assert manifest.actual_cash_cost_vnd == 50000
    assert manifest.tests_passed is True
    assert manifest.artifact_names == set(req_names)

    # Verification passes
    assert verify_release_manifest(manifest, artifacts, sha_resolver=test_resolver) is True

    # Tamper test
    artifacts[req_names[0]].write_text('{"tampered": true}', encoding="utf-8")
    assert verify_release_manifest(manifest, artifacts, sha_resolver=test_resolver) is False


def test_build_and_verify_full_product_release_exact_inventory(tmp_path: Path) -> None:
    req_names = list(get_mandatory_inventory("FULL_PRODUCT_RELEASE"))
    artifacts = _create_dummy_files(tmp_path, req_names)
    drift_res = PSIDriftResult(psi=0.02, threshold=0.1, drift_detected=False, bins=10)

    # Injected test-only resolver returning deterministic mock SHA
    test_resolver = lambda: "a" * 40

    manifest = build_release_manifest(
        status="FULL_PRODUCT_RELEASE",
        artifacts=artifacts,
        psi_drift_result=drift_res,
        actual_cash_cost_vnd=150000,
        tests_passed=True,
        known_limitations=("Local Compose required for streaming",),
        sha_resolver=test_resolver,
    )
    assert manifest.status == "FULL_PRODUCT_RELEASE"
    assert manifest.actual_cash_cost_vnd == 150000
    assert manifest.git_sha == "a" * 40

    # Verification passes with matching resolver
    assert verify_release_manifest(manifest, artifacts, sha_resolver=test_resolver) is True

    # Tamper test: modified file fails
    artifacts[req_names[0]].write_text('{"tampered": true}', encoding="utf-8")
    assert verify_release_manifest(manifest, artifacts, sha_resolver=test_resolver) is False


def test_resolver_mismatch_fails_verification(tmp_path: Path) -> None:
    req_names = list(get_mandatory_inventory("RESEARCH_RELEASE"))
    artifacts = _create_dummy_files(tmp_path, req_names)
    drift_res = PSIDriftResult(psi=0.02, threshold=0.1, drift_detected=False, bins=10)

    manifest = build_release_manifest(
        status="RESEARCH_RELEASE",
        artifacts=artifacts,
        psi_drift_result=drift_res,
        actual_cash_cost_vnd=50000,
        tests_passed=True,
        known_limitations=(),
        sha_resolver=lambda: "c" * 40,
    )

    # Verifier with mismatched resolver fails closed
    assert verify_release_manifest(manifest, artifacts, sha_resolver=lambda: "d" * 40) is False


def test_extra_unexpected_inventory_rejected_on_build_and_verify(tmp_path: Path) -> None:
    req_names = list(get_mandatory_inventory("RESEARCH_RELEASE"))
    artifacts = _create_dummy_files(tmp_path, req_names + ["unexpected_extra"])
    drift_res = PSIDriftResult(psi=0.02, threshold=0.1, drift_detected=False, bins=10)

    # Building with unexpected extra artifact must raise ValueError
    with pytest.raises(ValueError) as exc_info:
        build_release_manifest(
            status="RESEARCH_RELEASE",
            artifacts=artifacts,
            psi_drift_result=drift_res,
            actual_cash_cost_vnd=50000,
            tests_passed=True,
            known_limitations=(),
            sha_resolver=lambda: "c" * 40,
        )
    assert "Unexpected extra release artifacts" in str(exc_info.value)


def test_direct_construction_with_invalid_inventory_rejected() -> None:
    drift_res = PSIDriftResult(psi=0.02, threshold=0.1, drift_detected=False, bins=10)
    with pytest.raises(ValidationError):
        ReleaseManifest(
            status="RESEARCH_RELEASE",
            git_sha="a" * 40,
            artifact_hashes=(("dataset", "a" * 64),),  # Missing other 4 research artifacts
            psi_drift_result=drift_res,
            actual_cash_cost_vnd=0,
            tests_passed=True,
            known_limitations=(),
        )


def test_incomplete_evidence_rejected_for_full_product_release(tmp_path: Path) -> None:
    partial_artifacts = _create_dummy_files(tmp_path, ["dataset", "split"])
    drift_res = PSIDriftResult(psi=0.02, threshold=0.1, drift_detected=False, bins=10)

    with pytest.raises(ValueError) as exc_info:
        build_release_manifest(
            status="FULL_PRODUCT_RELEASE",
            artifacts=partial_artifacts,
            psi_drift_result=drift_res,
            actual_cash_cost_vnd=100,
            tests_passed=True,
            known_limitations=(),
            sha_resolver=lambda: "a" * 40,
        )
    assert "Missing mandatory release artifacts" in str(exc_info.value)


def test_direct_construction_validation_errors() -> None:
    drift_res = PSIDriftResult(psi=0.02, threshold=0.1, drift_detected=False, bins=10)
    valid_hashes = tuple(
        (name, "a" * 64) for name in sorted(MANDATORY_INVENTORIES["RESEARCH_RELEASE"])
    )

    # Invalid git sha (too short)
    with pytest.raises(ValidationError):
        ReleaseManifest(
            status="RESEARCH_RELEASE",
            git_sha="abc",
            artifact_hashes=valid_hashes,
            psi_drift_result=drift_res,
            actual_cash_cost_vnd=0,
            tests_passed=True,
            known_limitations=(),
        )

    # Invalid artifact hash (not 64 hex)
    with pytest.raises(ValidationError):
        ReleaseManifest(
            status="RESEARCH_RELEASE",
            git_sha="a" * 40,
            artifact_hashes=(
                ("dataset", "short_hash"),
                ("feature_config", "a" * 64),
                ("model_weights", "a" * 64),
                ("split", "a" * 64),
                ("trace_report", "a" * 64),
            ),
            psi_drift_result=drift_res,
            actual_cash_cost_vnd=0,
            tests_passed=True,
            known_limitations=(),
        )

    # Blank artifact name
    with pytest.raises(ValidationError):
        ReleaseManifest(
            status="RESEARCH_RELEASE",
            git_sha="a" * 40,
            artifact_hashes=(
                (" ", "a" * 64),
                ("feature_config", "a" * 64),
                ("model_weights", "a" * 64),
                ("split", "a" * 64),
                ("trace_report", "a" * 64),
            ),
            psi_drift_result=drift_res,
            actual_cash_cost_vnd=0,
            tests_passed=True,
            known_limitations=(),
        )

    # Unsorted artifact hashes
    with pytest.raises(ValidationError):
        ReleaseManifest(
            status="RESEARCH_RELEASE",
            git_sha="a" * 40,
            artifact_hashes=(
                ("trace_report", "a" * 64),
                ("dataset", "a" * 64),
                ("feature_config", "a" * 64),
                ("model_weights", "a" * 64),
                ("split", "a" * 64),
            ),
            psi_drift_result=drift_res,
            actual_cash_cost_vnd=0,
            tests_passed=True,
            known_limitations=(),
        )

    # Duplicate artifact names
    with pytest.raises(ValidationError):
        ReleaseManifest(
            status="RESEARCH_RELEASE",
            git_sha="a" * 40,
            artifact_hashes=(
                ("dataset", "a" * 64),
                ("dataset", "b" * 64),
                ("feature_config", "a" * 64),
                ("model_weights", "a" * 64),
                ("split", "a" * 64),
            ),
            psi_drift_result=drift_res,
            actual_cash_cost_vnd=0,
            tests_passed=True,
            known_limitations=(),
        )

    # Negative cash cost
    with pytest.raises(ValidationError):
        ReleaseManifest(
            status="RESEARCH_RELEASE",
            git_sha="a" * 40,
            artifact_hashes=valid_hashes,
            psi_drift_result=drift_res,
            actual_cash_cost_vnd=-10,
            tests_passed=True,
            known_limitations=(),
        )


def test_verify_fails_on_drift_detected(tmp_path: Path) -> None:
    req_names = list(get_mandatory_inventory("RESEARCH_RELEASE"))
    artifacts = _create_dummy_files(tmp_path, req_names)
    test_resolver = lambda: "a" * 40

    # If PSIDriftResult has drift_detected=True (or psi >= threshold)
    drift_res = PSIDriftResult(psi=0.25, threshold=0.1, drift_detected=True, bins=10)
    manifest = ReleaseManifest(
        status="RESEARCH_RELEASE",
        git_sha="a" * 40,
        artifact_hashes=tuple(
            (name, hash_file_sha256(artifacts[name])) for name in sorted(req_names)
        ),
        psi_drift_result=drift_res,
        actual_cash_cost_vnd=1000,
        tests_passed=True,
        known_limitations=(),
    )
    assert verify_release_manifest(manifest, artifacts, sha_resolver=test_resolver) is False


def test_verify_fails_on_tests_not_passed(tmp_path: Path) -> None:
    req_names = list(get_mandatory_inventory("RESEARCH_RELEASE"))
    artifacts = _create_dummy_files(tmp_path, req_names)
    test_resolver = lambda: "a" * 40
    drift_res = PSIDriftResult(psi=0.02, threshold=0.1, drift_detected=False, bins=10)

    manifest = ReleaseManifest(
        status="RESEARCH_RELEASE",
        git_sha="a" * 40,
        artifact_hashes=tuple(
            (name, hash_file_sha256(artifacts[name])) for name in sorted(req_names)
        ),
        psi_drift_result=drift_res,
        actual_cash_cost_vnd=1000,
        tests_passed=False,
        known_limitations=(),
    )
    assert verify_release_manifest(manifest, artifacts, sha_resolver=test_resolver) is False


def test_verify_fails_on_deleted_artifact_file(tmp_path: Path) -> None:
    req_names = list(get_mandatory_inventory("RESEARCH_RELEASE"))
    artifacts = _create_dummy_files(tmp_path, req_names)
    test_resolver = lambda: "a" * 40
    drift_res = PSIDriftResult(psi=0.02, threshold=0.1, drift_detected=False, bins=10)

    manifest = build_release_manifest(
        status="RESEARCH_RELEASE",
        artifacts=artifacts,
        psi_drift_result=drift_res,
        actual_cash_cost_vnd=50000,
        tests_passed=True,
        known_limitations=(),
        sha_resolver=test_resolver,
    )

    # Delete one of the files
    artifacts[req_names[0]].unlink()
    assert verify_release_manifest(manifest, artifacts, sha_resolver=test_resolver) is False


def test_hash_file_sha256(tmp_path: Path) -> None:
    test_file = tmp_path / "sample.txt"
    test_file.write_text("hello world", encoding="utf-8")
    # echo -n "hello world" | sha256sum -> b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9
    digest = hash_file_sha256(test_file)
    assert digest == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"

    missing_file = tmp_path / "missing.txt"
    with pytest.raises(FileNotFoundError):
        hash_file_sha256(missing_file)


def test_build_with_invalid_sha_resolver(tmp_path: Path) -> None:
    req_names = list(get_mandatory_inventory("RESEARCH_RELEASE"))
    artifacts = _create_dummy_files(tmp_path, req_names)
    drift_res = PSIDriftResult(psi=0.02, threshold=0.1, drift_detected=False, bins=10)

    with pytest.raises(ValueError, match="Invalid git_sha from resolver"):
        build_release_manifest(
            status="RESEARCH_RELEASE",
            artifacts=artifacts,
            psi_drift_result=drift_res,
            actual_cash_cost_vnd=50000,
            tests_passed=True,
            known_limitations=(),
            sha_resolver=lambda: "not_a_valid_40_hex_sha",
        )
