import importlib
import sys


def test_app_imports_without_side_effects() -> None:
    sys.modules.pop("app.main", None)
    sys.modules.pop("aiogram", None)

    module = importlib.import_module("app.main")

    assert callable(module.run)
    assert callable(module.main)
    assert "aiogram" not in sys.modules
