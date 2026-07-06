from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_deterministic_case_study_keeps_ai_out_of_v1() -> None:
    case_study = (ROOT / "docs/DETERMINISTIC_CASE_STUDY.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    project_brief = (ROOT / "docs/PROJECT_BRIEF.md").read_text(encoding="utf-8")

    assert "counterexample to premature AI adoption" in case_study
    assert "Slot availability | Deterministic code" in case_study
    assert "Future AI can be considered only as an optional draft" in case_study
    assert "docs/DETERMINISTIC_CASE_STUDY.md" in readme
    assert "Not needed for v1" in project_brief
