"""Eval harness scripts (A/B generation, judging, golden-quote fabrication).

Package marker so hermetic tests can import the harness modules
(``from scripts.eval import run_fabrication_eval``) via the repo-root
``pythonpath`` entry in ``pyproject.toml`` — the same mechanism
``tests/unit/scripts`` uses for ``scripts.ingest_corpus``.
"""
