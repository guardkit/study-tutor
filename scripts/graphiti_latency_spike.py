"""Phase 1 prep — three-hop Graphiti latency spike.

Measures the actual P1 stack:
  - FalkorDB on whitestocks (Synology) over Tailscale
  - vLLM Qwen2.5-14B-FP8 on promaxgb10-41b1:8000 (LLM extraction)
  - vLLM nomic-embed-text-v1.5 on promaxgb10-41b1:8001 (embeddings)

Per `docs/research/ideas/phase-1-scope.md §"Latency spike"`:
  - Time `add_episode` on a representative session-shape payload.
  - Time `search_nodes` (NODE_HYBRID_SEARCH_RRF recipe).
  - Time `search_memory_facts` (EDGE_HYBRID_SEARCH_RRF recipe).
  - 1 warm-up + 3 timed runs each. Record min/median/max.

Decision bands (per phase-1-scope.md L83-85):
  - add_episode median > 5s  → SR-08 (async write-back) is critical
  - search_nodes median > 3s → revert ADR-ARCH-017 (sync) → long-running
  - search_nodes median < 1s → ADR-ARCH-017 sync confirmed

Run (from study-tutor repo root):
  /Users/richardwoollcott/Projects/appmilla_github/guardkit/.venv/bin/python \
    scripts/graphiti_latency_spike.py

Output: prints results table to stdout; also writes
`docs/research/ideas/graphiti-latency-spike-results.md`.

Throwaway test data is written to group_id "latency-spike-<ISO-DATE>" and
removed at the end. If cleanup fails, the namespace is logged so it can
be cleared manually with `guardkit graphiti clear`.
"""
from __future__ import annotations

import asyncio
import logging
import statistics
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Coroutine

# Add guardkit's src to import path is automatic since we run via its venv.
from guardkit.knowledge.config import load_graphiti_config
from guardkit.knowledge.graphiti_client import GraphitiClient, GraphitiConfig

from graphiti_core.nodes import EpisodeType
from graphiti_core.search.search_config_recipes import (
    NODE_HYBRID_SEARCH_RRF,
    EDGE_HYBRID_SEARCH_RRF,
)


# Quiet noisy modules during the spike — we want clean stdout.
logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
for noisy in (
    "guardkit",
    "graphiti_core",
    "neo4j",
    "httpx",
    "openai",
):
    logging.getLogger(noisy).setLevel(logging.ERROR)


SPIKE_GROUP = f"latency-spike-{datetime.now(timezone.utc).date().isoformat()}"

# Representative session-shape payload (Shared Kernel B `session.completed`).
SESSION_EPISODE_BODY = (
    'session_completed: {'
    '"session_id": "spike-session-uuid",'
    '"student_id": "lilymay",'
    '"subject": "English Literature",'
    '"topic": "macbeth:act1:witches",'
    '"duration_seconds": 1247,'
    '"aos_touched": ["AO1", "AO2"],'
    '"quality_score": 0.78,'
    '"ended_at": "2026-04-27T10:00:00Z"}'
)


@dataclass
class TimingResult:
    label: str
    runs: list[float]

    @property
    def min(self) -> float:
        return min(self.runs)

    @property
    def median(self) -> float:
        return statistics.median(self.runs)

    @property
    def max(self) -> float:
        return max(self.runs)


async def time_async(
    label: str,
    fn: Callable[[], Coroutine[Any, Any, Any]],
    *,
    n: int = 3,
) -> TimingResult:
    runs: list[float] = []
    for i in range(n):
        t0 = time.perf_counter()
        try:
            await fn()
        except Exception as exc:  # noqa: BLE001
            print(f"  [run {i+1}] FAILED: {exc!r}", file=sys.stderr, flush=True)
            raise
        elapsed = time.perf_counter() - t0
        runs.append(elapsed)
        print(f"  run {i+1}: {elapsed:.2f}s", file=sys.stderr, flush=True)
    return TimingResult(label=label, runs=runs)


def _build_config() -> tuple[GraphitiConfig, Any]:
    """Build a GraphitiConfig from .guardkit/graphiti.yaml — mirrors guardkit CLI."""
    settings = load_graphiti_config()
    config = GraphitiConfig(
        enabled=settings.enabled,
        neo4j_uri=settings.neo4j_uri,
        neo4j_user=settings.neo4j_user,
        neo4j_password=settings.neo4j_password,
        timeout=settings.timeout,
        project_id=settings.project_id,
        graph_store=settings.graph_store,
        falkordb_host=settings.falkordb_host,
        falkordb_port=settings.falkordb_port,
        llm_provider=settings.llm_provider,
        llm_base_url=settings.llm_base_url,
        llm_model=settings.llm_model,
        llm_max_tokens=settings.llm_max_tokens,
        embedding_provider=settings.embedding_provider,
        embedding_base_url=settings.embedding_base_url,
        embedding_model=settings.embedding_model,
        embedding_dimensions=getattr(settings, "embedding_dimensions", None),
    )
    return config, settings


async def _cleanup(client: GraphitiClient) -> None:
    """Delete every node/edge in the spike group via raw cypher.

    Best-effort. Failure is logged, not raised — we don't want cleanup
    issues to invalidate the timing results.
    """
    if not client._graphiti:
        return
    driver = getattr(client._graphiti, "_driver", None) or getattr(
        client._graphiti, "driver", None
    )
    if driver is None:
        print(
            f"  [cleanup] No driver handle — leaving group_id={SPIKE_GROUP!r} "
            f"for manual removal via `guardkit graphiti clear`.",
            file=sys.stderr,
            flush=True,
        )
        return
    # Account for guardkit's project-id prefixing on group_ids.
    prefixed_group = client._apply_group_prefix(SPIKE_GROUP, scope="project")
    try:
        await driver.execute_query(
            "MATCH (n) WHERE n.group_id = $g DETACH DELETE n",
            g=prefixed_group,
        )
        print(
            f"  [cleanup] Removed nodes in group_id={prefixed_group!r}.",
            file=sys.stderr,
            flush=True,
        )
    except Exception as exc:  # noqa: BLE001
        print(
            f"  [cleanup] Failed to drop spike namespace ({exc!r}); "
            f"manually clear group_id={prefixed_group!r}.",
            file=sys.stderr,
            flush=True,
        )


async def main() -> int:
    print("Phase 1 Graphiti latency spike", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    config, settings = _build_config()

    print(
        f"FalkorDB: {settings.falkordb_host}:{settings.falkordb_port}",
        file=sys.stderr,
    )
    print(
        f"LLM:      {settings.llm_provider} {settings.llm_model} "
        f"({settings.llm_base_url})",
        file=sys.stderr,
    )
    print(
        f"Embedder: {settings.embedding_provider} {settings.embedding_model} "
        f"({settings.embedding_base_url})",
        file=sys.stderr,
    )
    print(f"Group:    {SPIKE_GROUP}", file=sys.stderr)
    print("", file=sys.stderr)

    client = GraphitiClient(config)
    initialised = await client.initialize()
    if not initialised or not client.enabled:
        print("ERROR: GraphitiClient failed to initialise.", file=sys.stderr)
        return 1
    print("Connected.", file=sys.stderr)

    # Pre-warm vLLM endpoints so cold-start doesn't dominate run 1.
    if settings.llm_provider in ("vllm", "ollama") or settings.embedding_provider in (
        "vllm",
        "ollama",
    ):
        print("Warming up vLLM endpoints...", file=sys.stderr)
        try:
            await client.wait_for_llm_endpoints(timeout=60.0)
        except Exception as exc:  # noqa: BLE001
            print(f"  warm-up check raised {exc!r}; continuing.", file=sys.stderr)

    # The underlying graphiti-core instance for unwrapped timing.
    g = client._graphiti
    assert g is not None

    # ---- Warm-up add_episode (not timed) -----------------------------------
    print("\nWarm-up add_episode (not timed) ...", file=sys.stderr)
    t0 = time.perf_counter()
    await g.add_episode(
        name=f"warmup-{uuid.uuid4()}",
        episode_body=SESSION_EPISODE_BODY,
        source=EpisodeType.json,
        source_description="latency-spike warm-up",
        reference_time=datetime.now(timezone.utc),
        group_id=SPIKE_GROUP,
    )
    print(f"  warm-up took {time.perf_counter() - t0:.2f}s", file=sys.stderr)

    # ---- 1. add_episode (3 timed runs) -------------------------------------
    print("\nadd_episode (3 timed runs) ...", file=sys.stderr)

    async def add_one() -> None:
        await g.add_episode(
            name=f"spike-{uuid.uuid4()}",
            episode_body=SESSION_EPISODE_BODY,
            source=EpisodeType.json,
            source_description="latency-spike timed run",
            reference_time=datetime.now(timezone.utc),
            group_id=SPIKE_GROUP,
        )

    add_results = await time_async("add_episode", add_one, n=3)

    # ---- 2. search_nodes (NODE_HYBRID_SEARCH_RRF; 3 runs) ------------------
    print("\nsearch_nodes — NODE_HYBRID_SEARCH_RRF (3 timed runs) ...",
          file=sys.stderr)

    async def search_nodes_once() -> None:
        cfg = NODE_HYBRID_SEARCH_RRF.model_copy(deep=True)
        cfg.limit = 10
        await g.search_(
            query="macbeth witches confidence Lilymay",
            config=cfg,
            group_ids=[SPIKE_GROUP],
        )

    search_nodes_results = await time_async("search_nodes", search_nodes_once, n=3)

    # ---- 3. search_memory_facts (EDGE_HYBRID_SEARCH_RRF; 3 runs) -----------
    print("\nsearch_memory_facts — EDGE_HYBRID_SEARCH_RRF (3 timed runs) ...",
          file=sys.stderr)

    async def search_facts_once() -> None:
        cfg = EDGE_HYBRID_SEARCH_RRF.model_copy(deep=True)
        cfg.limit = 10
        await g.search_(
            query="quality_score for Lilymay on Macbeth",
            config=cfg,
            group_ids=[SPIKE_GROUP],
        )

    search_facts_results = await time_async(
        "search_memory_facts", search_facts_once, n=3
    )

    # ---- Cleanup -----------------------------------------------------------
    print("\nCleaning up spike namespace...", file=sys.stderr)
    await _cleanup(client)
    await client.close()

    # ---- Report -----------------------------------------------------------
    rows = [add_results, search_nodes_results, search_facts_results]

    print("\n" + "=" * 60, file=sys.stderr)
    print("RESULTS", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    md_lines: list[str] = []
    md_lines.append("# Graphiti Latency Spike — Results")
    md_lines.append("")
    md_lines.append(
        f"**Date:** {datetime.now(timezone.utc).date().isoformat()}"
    )
    md_lines.append(
        "**Stack measured:** FalkorDB on `"
        f"{settings.falkordb_host}:{settings.falkordb_port}` "
        f"+ vLLM `{settings.llm_model}` on `{settings.llm_base_url}` "
        f"(LLM extraction) + `{settings.embedding_model}` on "
        f"`{settings.embedding_base_url}` (embeddings)."
    )
    md_lines.append(
        "**Generated by:** `scripts/graphiti_latency_spike.py` "
        "(per `phase-1-scope.md §\"Latency spike\"`)."
    )
    md_lines.append("")
    md_lines.append(
        "Note: this run measures the **post-21-Apr vLLM-on-GB10 stack**, "
        "not the original Gemini stack the spec assumed. The 1–3s / 5–8s "
        "expected ranges in `phase-1-scope.md:75` were calibrated for "
        "Gemini API latency; vLLM on Tailscale has a different shape."
    )
    md_lines.append("")
    md_lines.append("## Measurements")
    md_lines.append("")
    md_lines.append("Each operation: 1 warm-up (untimed) + 3 timed runs against a "
                    f"throwaway `group_id={SPIKE_GROUP!r}`.")
    md_lines.append("")
    md_lines.append("| Operation | Min (s) | Median (s) | Max (s) | Runs (s) |")
    md_lines.append("|---|---:|---:|---:|---|")
    for r in rows:
        runs_str = ", ".join(f"{x:.2f}" for x in r.runs)
        md_lines.append(
            f"| `{r.label}` | {r.min:.2f} | {r.median:.2f} | {r.max:.2f} | {runs_str} |"
        )
    md_lines.append("")
    md_lines.append("## Decisions unblocked")
    md_lines.append("")

    add_med = add_results.median
    sn_med = search_nodes_results.median
    sf_med = search_facts_results.median

    if add_med > 5.0:
        md_lines.append(
            f"- **SR-08 (async write-back): CRITICAL.** `add_episode` "
            f"median {add_med:.2f}s > 5s — async write-back is load-bearing "
            "throughout features; consider fire-and-forget from multiple "
            "write points, not just session-end."
        )
    elif add_med > 2.0:
        md_lines.append(
            f"- **SR-08 (async write-back): LOAD-BEARING.** `add_episode` "
            f"median {add_med:.2f}s — async required; defensive shape works."
        )
    else:
        md_lines.append(
            f"- **SR-08 (async write-back): DEFENSIVE.** `add_episode` "
            f"median {add_med:.2f}s — fast enough that sync would also "
            "work, but keep async as defensive shape."
        )

    if sn_med > 3.0:
        md_lines.append(
            f"- **ADR-ARCH-017 / SR-07: REVERT REQUIRED.** `search_nodes` "
            f"median {sn_med:.2f}s > 3s — `tutor_start_session` should be "
            "reclassified back to long-running with `_status`/`_cancel` "
            "companion. Run `/arch-refine --adr=ADR-ARCH-017`."
        )
    elif sn_med < 1.0:
        md_lines.append(
            f"- **ADR-ARCH-017 / SR-07: CONFIRMED.** `search_nodes` "
            f"median {sn_med:.2f}s < 1s — sync classification holds; no "
            "further architecture work required."
        )
    else:
        md_lines.append(
            f"- **ADR-ARCH-017 / SR-07: HOLDS WITH MARGIN.** `search_nodes` "
            f"median {sn_med:.2f}s (1–3s band) — sync classification holds; "
            "document this median in ARCH-017's reversion footnote so the "
            "P1 trigger threshold is concrete."
        )

    md_lines.append(
        f"- **DEC-02 / DEC-08:** resolved by these numbers — "
        f"add_episode {add_med:.2f}s / search_nodes {sn_med:.2f}s / "
        f"search_memory_facts {sf_med:.2f}s."
    )

    md_lines.append("")
    md_lines.append("## Raw run data")
    md_lines.append("")
    for r in rows:
        md_lines.append(f"- `{r.label}`: {[round(x, 2) for x in r.runs]} s")
    md_lines.append("")
    md_lines.append(
        f"_Spike group `{SPIKE_GROUP}` was cleaned up after the run "
        "(see stderr log if anything was left behind)._"
    )

    md_text = "\n".join(md_lines) + "\n"

    out_path = Path("docs/research/ideas/graphiti-latency-spike-results.md")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md_text, encoding="utf-8")

    # Echo the markdown to stdout so the run's STDOUT *is* the report.
    print(md_text)
    print(f"Wrote {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
