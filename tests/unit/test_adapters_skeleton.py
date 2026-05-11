"""Smoke test for PH1-001: study_tutor.adapters package is importable."""
from __future__ import annotations


def test_adapters_package_importable():
    import study_tutor.adapters  # noqa: F401


def test_adapters_manifest_module_importable():
    from study_tutor.adapters import manifest  # noqa: F401


def test_adapters_command_router_module_importable():
    from study_tutor.adapters import command_router  # noqa: F401
