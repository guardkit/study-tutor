"""``scripts/`` package marker so seam + unit tests can import.

The repo's hatchling config (``pyproject.toml`` ``[tool.hatch.build.targets.wheel]``)
only ships ``src/study_tutor`` to site-packages — operational scripts under
``scripts/`` are deliberately not installed. This ``__init__.py`` exists
purely so pytest, with ``pythonpath = ["."]``, can resolve
``from scripts.seed_student_model import ...`` for the seam tests that
exercise the student-model seeding script.
"""
