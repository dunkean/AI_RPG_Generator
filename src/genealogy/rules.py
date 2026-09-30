"""Extension contract: hazard rules add world mechanics without new person objects."""

from typing import TYPE_CHECKING, Protocol

import numpy as np

if TYPE_CHECKING:
    from .engine import Engine


class HazardRule(Protocol):
    def apply(
        self, engine: "Engine", process: str, ids: np.ndarray, hazards: dict[str, np.ndarray]
    ) -> None:
        """Mutate arrays, preserving lengths and nonnegative finite values.

        processes: births reads fertility/capacity; deaths reads mortality/extra_mortality;
        migrations reads migration/capacity (may also be called for spouses).
        Arrays except capacity align with ids; capacity aligns with settlements.
        Random rules should use engine.stream('unique_rule_name', process), not global RNG.
        """
