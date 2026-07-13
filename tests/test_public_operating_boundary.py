import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_public_operating_status_blocks_unverified_claims() -> None:
    status = json.loads(
        (ROOT / "docs/evidence/public_operating_status.json").read_text(
            encoding="utf-8"
        )
    )

    assert status["schema_version"] == "shishki-bot-public-operating-status-v1"
    assert set(status["publicly_verified_counts"].values()) == {0}
    assert status["historical_private_notes"] == {
        "independently_reverified": False,
        "private_backups_published": False,
        "runtime_database_published": False,
        "counted_as_public_evidence": False,
    }
    assert {
        "current deployment",
        "real client adoption",
        "zero double bookings in operation",
        "revenue or business impact",
    } <= set(status["blocked_claims"])


def test_public_docs_do_not_publish_runtime_paths_or_client_receipts() -> None:
    public_docs = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((ROOT / "docs").rglob("*.md"))
        if path.name != "ORCHESTRATOR.md"
    )

    assert "/srv/openclaw-you" not in public_docs
    assert "alexander-time-bug" not in public_docs


def test_case_study_labels_targets_as_unmeasured() -> None:
    case_study = (ROOT / "docs/DETERMINISTIC_CASE_STUDY.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "## Unmeasured Launch Hypotheses" in case_study
    assert "not observed metrics" in case_study
    assert "not current operating evidence" in readme
