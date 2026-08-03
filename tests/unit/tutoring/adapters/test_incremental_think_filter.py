"""The streaming think filter (2026-08-03 leak fix).

Receipt: Lilymay's session b1eec0dc turn 11 persisted a raw ``<think>``
block — the old respond_stream buffered the whole generation then
re-yielded RAW tokens through a per-token marker check, which model
tokenization defeats ("<th" + "ink>"). These tests pin the incremental
filter: reasoning never emits, visible text streams as it arrives, and
end-of-stream semantics match the canonical batch strip.
"""

from study_tutor.tutoring.adapters.llm_player_adapter import (
    _IncrementalThinkFilter,
    _strip_think_tokens,
)


def _run(tokens: list[str]) -> tuple[list[str], str]:
    filt = _IncrementalThinkFilter()
    deltas = [d for d in (filt.feed(t) for t in tokens) if d]
    return deltas, "".join(deltas) + filt.flush()


def test_marker_split_across_tokens_never_leaks_reasoning() -> None:
    """THE production leak: '<think>' arriving as '<th' + 'ink>'."""
    tokens = [
        "<th",
        "ink>\nThe student is asking for an example",
        " of dramatic irony...</th",
        "ink>",
        "Great question! ",
        "Let's look at Act 1.",
    ]
    deltas, output = _run(tokens)

    assert output == "Great question! Let's look at Act 1."
    assert all("think" not in d.lower() for d in deltas)
    assert all("student is asking" not in d for d in deltas)


def test_visible_text_streams_before_generation_completes() -> None:
    """True streaming: pre-think and post-think text release incrementally."""
    filt = _IncrementalThinkFilter()
    assert filt.feed("Metaphor compares ") == "Metaphor compares "
    assert filt.feed("directly. ") == "directly. "
    # Reasoning starts — held.
    assert filt.feed("<think>secret reasoning") == ""
    assert filt.feed(" continues</think>") == ""
    # Post-think text releases immediately again.
    assert filt.feed("A simile uses like.") == "A simile uses like."
    assert filt.flush() == ""


def test_head_think_block_with_lstrip_matches_batch() -> None:
    raw = "\n<think>plan the answer</think>\n\nHere is the answer."
    tokens = [raw[i : i + 7] for i in range(0, len(raw), 7)]
    _, output = _run(tokens)
    assert output == _strip_think_tokens(raw)
    assert output == "Here is the answer."


def test_lone_angle_bracket_is_released_once_disambiguated() -> None:
    filt = _IncrementalThinkFilter()
    assert filt.feed("2 <") == "2 "
    assert filt.feed("3 means less than.") == "<3 means less than."
    assert filt.flush() == ""


def test_dangling_head_opener_matches_batch_blank_line_rule() -> None:
    raw = "<think>reasoning with no close\n\nThe visible answer."
    tokens = [raw[i : i + 5] for i in range(0, len(raw), 5)]
    _, output = _run(tokens)
    assert output == _strip_think_tokens(raw)
    assert output == "The visible answer."


def test_mid_response_dangling_opener_never_leaks_at_flush() -> None:
    """Stricter than batch here: mid-response reasoning must not release."""
    tokens = ["Intro sentence. ", "<think>never closed reasoning"]
    deltas, output = _run(tokens)
    assert output == "Intro sentence. "
    assert all("reasoning" not in d for d in deltas)


def test_multiple_think_blocks_all_suppressed() -> None:
    raw = (
        "<think>one</think>First. <think>two</think>Second."
    )
    tokens = [raw[i : i + 4] for i in range(0, len(raw), 4)]
    _, output = _run(tokens)
    assert output == _strip_think_tokens(raw)
    assert output == "First. Second."
