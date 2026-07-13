from __future__ import annotations

import re
from pathlib import Path

WORKFLOW_DIR = Path(".github/workflows")
PINNED_OFFICIAL_ACTIONS = {
    "actions/checkout": "9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0",
    "actions/setup-python": "ece7cb06caefa5fff74198d8649806c4678c61a1",
}


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

        action_steps = re.findall(
            r"(?m)^[ \t]*(?:-[ \t]*)?uses:[ \t]+(actions/[^@\s]+)@([^\s#]+)",
            text,
        )
        assert action_steps
        for action, revision in action_steps:
            assert action in PINNED_OFFICIAL_ACTIONS
            assert revision == PINNED_OFFICIAL_ACTIONS[action]

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
