import builtins
import importlib
import sys


def test_app_imports_without_side_effects(monkeypatch) -> None:
    sys.modules.pop("app.main", None)
    sys.modules.pop("aiogram", None)

    real_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == "aiogram" or name.startswith("aiogram."):
            raise AssertionError("app.main imported aiogram at module import time")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    module = importlib.import_module("app.main")

    assert callable(module.run)
    assert callable(module.main)
    assert "aiogram" not in sys.modules
