---
title: '5-Block Prompt Context Assembler (prompt.py)'
type: 'feature'
created: '2026-08-15'
status: 'done'
baseline_commit: '86cbbc2ecbc9102f296cbbf3747d032a13673ef8'
review_loop_iteration: 0
context:
  - 'custom_components/garmin_ha_ai/models.py'
  - 'custom_components/garmin_ha_ai/const.py'
  - 'custom_components/garmin_ha_ai/ai_engine/__init__.py'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** To produce accurate, high-quality, and personalized daily health reports, the AI engine requires structured context containing current metrics, historical trends, user goals, coaching directives, and output formatting rules. Without a structured 5-block prompt assembler, LLMs can output inconsistent formatting, miss trend insights, or exceed token limits.

**Approach:** Implement `custom_components/garmin_ha_ai/ai_engine/prompt.py` providing `assemble_report_prompt` and context truncation utilities. The assembler builds a 5-block prompt:
1. **Block 1 (Current Day Metrics)**: Detailed breakdown of today's `GarminDailyMetrics`.
2. **Block 2 (Historical Trends)**: 7-day metric history context (steps, sleep, HRV, stress trends).
3. **Block 3 (User Goals & Profile)**: User-configured fitness/health goals.
4. **Block 4 (Persona & Directives)**: Coaching tone, focus directives, and style rules.
5. **Block 5 (Output Structure Rules)**: Strict Markdown formatting directives requiring a concise `<summary>` block (for 255-char HA state) and detailed analysis sections.
Include automatic history truncation to prevent context token overflow when historical data is extensive.

## Boundaries & Constraints

**Always:**
- Format prompt into 5 clear, structured Markdown sections / blocks.
- Handle missing optional metrics in `GarminDailyMetrics` gracefully (render "N/A" or "Not recorded").
- Automatically truncate historical trend context if history entries exceed safety threshold length (default 3,000 characters).
- Include strict output directives specifying `<summary>...</summary>` tag format at the beginning of the LLM response for easy extraction.

**Ask First:**
- Modifying default max history safety character limit (default: 3,000 characters).

**Never:**
- Hardcode user API keys, passwords, or personal identity details into prompt templates.
- Fail or throw unhandled exceptions if history entries list is empty or metrics fields are None.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Complete Metrics & 7-day History | Valid today metrics, 7 history entries, user goals, directive | 5-block prompt string generated with all sections formatted | Graceful fallback for missing fields |
| Partial / Missing Metrics | Metrics object with `steps=None`, `sleep_score=None` | Prompt generated with missing values displayed as "N/A" | No exception raised |
| Empty History | `history=[]` | History block indicates "No previous 7-day history recorded yet" | Prompt builds cleanly |
| Overflowing History Length | 30+ days of history provided (>3000 chars) | Truncates history to most recent 7 days or fits within 3,000 char cap | Log warning if truncation occurs |
| Default Goals & Directives | `goals=None`, `directives=None` | Fallback default coaching persona and general wellness goals used | No exception raised |

</frozen-after-approval>

## Code Map

- `custom_components/garmin_ha_ai/models.py` -- `GarminDailyMetrics` dataclass used as input for Block 1 & 2.
- `custom_components/garmin_ha_ai/ai_engine/prompt.py` -- 5-block prompt assembler implementation and truncation helper.
- `custom_components/garmin_ha_ai/ai_engine/__init__.py` -- Export `assemble_report_prompt` helper function.
- `tests/test_prompt.py` -- Unit tests for prompt assembly, missing metric fallbacks, history truncation, and formatting.

## Tasks & Acceptance

**Execution:**
- [x] `custom_components/garmin_ha_ai/ai_engine/prompt.py` -- Implement `assemble_report_prompt` and `truncate_history_context` functions building the 5-block prompt structure.
- [x] `custom_components/garmin_ha_ai/ai_engine/__init__.py` -- Re-export `assemble_report_prompt` from `ai_engine`.
- [x] `tests/test_prompt.py` -- Implement unit test suite verifying 5-block generation, partial metrics, empty history, safety truncation, and default directives.

**Acceptance Criteria:**
- Given current `GarminDailyMetrics`, 7-day history list, user goals, and directives, `assemble_report_prompt` outputs a single string containing all 5 prompt blocks.
- Given missing metrics or empty history, `assemble_report_prompt` renders appropriate placeholders without raising errors.
- Given history data exceeding 3,000 characters, `truncate_history_context` automatically truncates older entries to stay within safety limits.
- The assembled prompt includes structural rules requesting `<summary>` tags for 255-char Home Assistant state compatibility.

## Spec Change Log

*No changes yet.*

## Verification

**Commands:**
- `PYTHONPATH=. pytest tests/test_prompt.py` -- expected: 100% pass on all prompt assembler unit tests.
- `PYTHONPATH=. pytest` -- expected: 100% pass on all integration tests.

## Suggested Review Order

**Prompt Context Assembler**

- 5-block prompt builder, daily metrics formatter, and safety history truncation helper
  [`prompt.py:22`](../../custom_components/garmin_ha_ai/ai_engine/prompt.py#L22)

- Re-export prompt assembly helpers in AI Engine package entry point
  [`__init__.py:16`](../../custom_components/garmin_ha_ai/ai_engine/__init__.py#L16)

**Unit Tests**

- Comprehensive unit test suite covering prompt blocks, missing metrics fallbacks, truncation, and defaults
  [`test_prompt.py:1`](../../tests/test_prompt.py#L1)

