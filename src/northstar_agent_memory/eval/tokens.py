"""Token estimates for fixed context budgets (note 09, Implications §2 and §4; DESIGN §8).

Every system is compared at the same token budget, so context is counted before it is
sent. The estimate is offline and conservative: about 3.5 characters a token, which
over-counts ordinary English, so a context that fits the estimate fits the budget.
Exact counts come later from the API's usage records.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Generic, Iterable, TypeVar

CHARS_PER_TOKEN = 3.5
TRUNCATED = "[truncated]"  # ends a block that was cut to fit

T = TypeVar("T")


def estimate_tokens(text: str) -> int:
    """A conservative estimate of the tokens in `text`: ceil(len / 3.5)."""
    return math.ceil(len(text) / CHARS_PER_TOKEN)


@dataclass(slots=True)
class Fitted(Generic[T]):
    """The blocks `fit_to_budget` kept, best first.

    When `truncated` is set, the highest-ranked block alone was too big for the budget:
    `blocks` then holds only it, and `text` is what it adds to the context, cut and
    ending in "[truncated]". Callers say so in their meta.
    """

    blocks: list[T]
    truncated: bool = False
    text: str | None = None


def fit_to_budget(blocks: Iterable[T], budget: int, key: Callable[[T], str] = str) -> Fitted[T]:
    """Keep whole blocks, in the given priority order, while they fit in `budget` tokens.

    `key` gives the text a block adds to the context. A block too large for what is
    left is skipped and later, smaller blocks may still fit. The one exception is the
    highest-ranked block: when it alone is over the budget and nothing is kept yet, it
    is kept cut to the budget and marked "[truncated]", so that a query whose best
    block is long still gets context. The kept blocks come back in priority order.
    """
    kept: list[T] = []
    used = 0
    for block in blocks:
        text = key(block)
        cost = estimate_tokens(text)
        if used + cost <= budget:
            kept.append(block)
            used += cost
        elif not kept:
            cut = _cut_and_mark(text, budget)
            if cut:
                return Fitted([block], True, cut)
    return Fitted(kept)


def _cut_and_mark(text: str, budget: int) -> str:
    """`text` cut so that it and the marker together fit in `budget`; empty when no room is left."""
    marker = "\n" + TRUNCATED
    room = budget - estimate_tokens(marker)
    if room <= 0:
        return ""
    return cut_to_tokens(text, room).rstrip() + marker


def cut_to_tokens(text: str, budget: int) -> str:
    """The longest prefix of `text` whose estimate is at most `budget` tokens."""
    if budget <= 0:
        return ""
    return text[: int(budget * CHARS_PER_TOKEN)]
