import json
import subprocess
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


def test_tracked_text_does_not_publish_runtime_paths_or_client_receipts() -> None:
    tracked = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout.split(b"\0")
    public_text: list[str] = []
    for encoded_path in tracked:
        if not encoded_path:
            continue
        contents = (ROOT / encoded_path.decode()).read_bytes()
        try:
            public_text.append(contents.decode("utf-8"))
        except UnicodeDecodeError:
            continue

    searchable = "\n".join(public_text)
    private_host_root = "/" + "srv" + "/" + "openclaw-you"
    client_receipt = "alexander" + "-time-bug"
    client_identifier = "client `" + "#10" + "`"
    notification_identifier = "notification `" + "#8" + "`"

    assert private_host_root not in searchable
    assert client_receipt not in searchable
    assert client_identifier not in searchable
    assert notification_identifier not in searchable


def test_case_study_labels_targets_as_unmeasured() -> None:
    case_study = (ROOT / "docs/DETERMINISTIC_CASE_STUDY.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "## Unmeasured Launch Hypotheses" in case_study
    assert "not observed metrics" in case_study
    assert "not current operating evidence" in readme
