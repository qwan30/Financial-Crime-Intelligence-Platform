from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from apps.case_api.main import create_app
from fincrime.cases.import_canvas import import_canvas_case
from fincrime.cases.models import CaseSnapshot
from fincrime.cases.service import CaseService
from fincrime.evidence.store import EvidenceStore


def test_pin_survives_restart_and_unpin_keeps_evidence(postgres_url: str) -> None:
    import_canvas_case(Path("tests/fixtures/forensic_canvas.json"), postgres_url)
    path = "/cases/canvas_vn_01"
    command = {
        "edge_id": "TXN-2026-8804",
        "analyst_id": "analyst_01",
        "is_pinned": True,
        "typology_tag": "SHELL_CORP",
    }
    with TestClient(create_app(database_url=postgres_url)) as first:
        before = first.get(path).json()["data"]
        response = first.post(
            path + "/evidence/pin",
            json=command,
            headers={"If-Match": '"' + before["snapshotHash"] + '"'},
        )
        assert response.status_code == 200
        saved = response.json()["data"]
        assert saved["new_snapshot_hash"] != before["snapshotHash"]
        assert [pin["edgeId"] for pin in saved["pins"]] == ["TXN-2026-8804"]
    with TestClient(create_app(database_url=postgres_url)) as second:
        reopened = second.get(path + "/workbench").json()["data"]
        assert reopened["case"]["snapshotHash"] == saved["new_snapshot_hash"]
        assert [pin["edgeId"] for pin in reopened["pins"]] == ["TXN-2026-8804"]
        command["is_pinned"] = False
        response = second.post(
            path + "/evidence/pin",
            json=command,
            headers={"If-Match": '"' + saved["new_snapshot_hash"] + '"'},
        )
        assert response.status_code == 200
        unpinned = response.json()["data"]
        assert unpinned["pins"] == []
        assert set(saved["case"]["evidenceIds"]) <= set(unpinned["case"]["evidenceIds"])
        assert unpinned["new_snapshot_hash"] != saved["new_snapshot_hash"]
    with TestClient(create_app(database_url=postgres_url)) as third:
        reopened = third.get(path + "/workbench").json()["data"]
        assert reopened["pins"] == []
        assert reopened["case"]["snapshotHash"] == unpinned["new_snapshot_hash"]
        assert set(saved["case"]["evidenceIds"]) <= {
            item["evidenceId"] for item in reopened["evidence"]
        }


def test_pin_requires_if_match_header(postgres_url: str) -> None:
    import_canvas_case(Path("tests/fixtures/forensic_canvas.json"), postgres_url)
    path = "/cases/canvas_vn_01"
    command = {
        "edge_id": "TXN-2026-8804",
        "analyst_id": "analyst_01",
        "is_pinned": True,
        "typology_tag": "SHELL_CORP",
    }
    with TestClient(create_app(database_url=postgres_url)) as client:
        # Missing header -> 428
        res = client.post(path + "/evidence/pin", json=command)
        assert res.status_code == 428
        assert res.json()["error"]["code"] == "SNAPSHOT_REQUIRED"

        # Stale header -> 409
        res2 = client.post(
            path + "/evidence/pin",
            json=command,
            headers={"If-Match": '"' + "0" * 64 + '"'},
        )
        assert res2.status_code == 409
        assert res2.json()["error"]["code"] == "SNAPSHOT_CONFLICT"


def test_pin_edge_not_in_case_returns_404(postgres_url: str) -> None:
    import_canvas_case(Path("tests/fixtures/forensic_canvas.json"), postgres_url)
    path = "/cases/canvas_vn_01"
    with TestClient(create_app(database_url=postgres_url)) as client:
        before = client.get(path).json()["data"]
        command = {
            "edge_id": "TXN-FOREIGN-999",
            "analyst_id": "analyst_01",
            "is_pinned": True,
            "typology_tag": "SHELL_CORP",
        }
        res = client.post(
            path + "/evidence/pin",
            json=command,
            headers={"If-Match": '"' + before["snapshotHash"] + '"'},
        )
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "EDGE_NOT_IN_CASE"


def test_pin_in_memory_returns_503_persistence_unavailable() -> None:
    app = create_app()
    with TestClient(app) as client:
        command = {
            "edge_id": "TXN-2026-8804",
            "analyst_id": "analyst_01",
            "is_pinned": True,
            "typology_tag": "SHELL_CORP",
        }
        res = client.post(
            "/cases/any_case/evidence/pin",
            json=command,
            headers={"If-Match": '"' + "a" * 64 + '"'},
        )
        assert res.status_code == 503
        assert res.json()["error"]["code"] == "PERSISTENCE_UNAVAILABLE"


def test_expand_graph_route(postgres_url: str) -> None:
    import_canvas_case(Path("tests/fixtures/forensic_canvas.json"), postgres_url)
    path = "/cases/canvas_vn_01"
    with TestClient(create_app(database_url=postgres_url)) as client:
        wb = client.get(path + "/workbench").json()["data"]
        known_edges = [e["edgeId"] for e in wb["trace"]["edges"]]
        req = {
            "nodeId": "shell",
            "knownEdgeIds": known_edges,
            "snapshotHash": wb["case"]["snapshotHash"],
        }
        res = client.post(path + "/graph/expand", json=req)
        assert res.status_code == 200
        expanded = res.json()["data"]
        expanded_node_ids = {n["nodeId"] for n in expanded["nodes"]}
        assert "atm" in expanded_node_ids
        assert "crypto" in expanded_node_ids


def test_hypothesis_route_stale_hash_and_llm_off(postgres_url: str) -> None:
    import_canvas_case(Path("tests/fixtures/forensic_canvas.json"), postgres_url)
    path = "/cases/canvas_vn_01"
    with TestClient(create_app(database_url=postgres_url)) as client:
        wb = client.get(path + "/workbench").json()["data"]
        current_hash = wb["case"]["snapshotHash"]

        # Stale hash returns 409
        stale_res = client.post(path + "/hypothesis", json={"snapshotHash": "0" * 64})
        assert stale_res.status_code == 409
        assert stale_res.json()["error"]["code"] == "SNAPSHOT_CONFLICT"

        # LLM_OFF mode returns 200 with AI_UNAVAILABLE status
        res = client.post(path + "/hypothesis", json={"snapshotHash": current_hash})
        assert res.status_code == 200
        hyp_data = res.json()["data"]
        assert hyp_data["snapshotHash"] == current_hash
        assert hyp_data["hypothesis"]["status"] == "AI_UNAVAILABLE"

        # Subsequent workbench GET returns cached hypothesis
        wb_cached = client.get(path + "/workbench").json()["data"]
        assert wb_cached["hypothesis"]["status"] == "AI_UNAVAILABLE"
        assert wb_cached["hypothesisSnapshotHash"] == current_hash
