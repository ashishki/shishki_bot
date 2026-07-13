from __future__ import annotations

import re
from pathlib import Path

import pytest

WORKFLOW_DIR = Path(".github/workflows")
PINNED_OFFICIAL_ACTIONS = {
    "actions/checkout": "9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0",
    "actions/setup-python": "ece7cb06caefa5fff74198d8649806c4678c61a1",
}


def assert_approved_action_references(text: str) -> None:
    action_references = re.findall(
        r"(?m)^[ \t]*(?:-[ \t]*)?uses:[ \t]+([^\s#]+)",
        text,
    )
    assert action_references
    for reference in action_references:
        action, separator, revision = reference.partition("@")
        assert separator == "@"
        assert action in PINNED_OFFICIAL_ACTIONS
        assert revision == PINNED_OFFICIAL_ACTIONS[action]


def test_all_active_workflows_use_read_only_pinned_actions() -> None:
    workflows = sorted((*WORKFLOW_DIR.glob("*.yml"), *WORKFLOW_DIR.glob("*.yaml")))
    assert workflows

    for workflow_path in workflows:
        text = workflow_path.read_text(encoding="utf-8")
        assert re.findall(r"(?m)^([ \t]*)permissions:[ \t]*$", text) == [""]
        permissions = re.search(
            r"(?m)^permissions:\s*\n(?P<body>(?:^[ \t]+[^\n]*\n?)*)", text
        )
        assert permissions is not None
        assert [
            line.strip()
            for line in permissions.group("body").splitlines()
            if line.strip()
        ] == ["contents: read"]

        assert_approved_action_references(text)

        lines = text.splitlines()
        checkout_steps = 0
        for index, line in enumerate(lines):
            match = re.match(r"^([ \t]*)-[ \t]+uses:[ \t]+actions/checkout@", line)
            if match is None:
                continue
            checkout_steps += 1
            indent = len(match.group(1))
            end = len(lines)
            for candidate_index in range(index + 1, len(lines)):
                if re.match(rf"^[ \t]{{{indent}}}-[ \t]+", lines[candidate_index]):
                    end = candidate_index
                    break
            assert any(
                item.strip() == "persist-credentials: false"
                for item in lines[index:end]
            )
        assert checkout_steps > 0


def test_action_allowlist_rejects_mixed_third_party_mutation() -> None:
    text = next(WORKFLOW_DIR.glob("*.y*ml")).read_text(encoding="utf-8")
    marker = "          persist-credentials: false"
    assert marker in text
    mutated = text.replace(
        marker,
        f"{marker}\n      - uses: untrusted/example@0123456789abcdef",
        1,
    )

    with pytest.raises(AssertionError):
        assert_approved_action_references(mutated)
