"""In-process client for the Railway-AI engine bundled with this backend."""

import logging
from typing import Any

import pandas as pd


logger = logging.getLogger(__name__)
_embedded_engine = None
try:
    from src.services.ml_engine import RailwayMLEngine

    _embedded_engine = RailwayMLEngine()
except Exception as exc:
    logger.warning("Could not initialize embedded Railway-AI engine: %s", exc)


class AIClientError(Exception):
    """Raised when the bundled Railway-AI engine cannot produce a result."""


class RailwayAIClient:
    """Adapter around the in-repository ML engine; no separate service is used."""

    @classmethod
    def is_healthy(cls) -> bool:
        return _embedded_engine is not None

    @classmethod
    def predict_asset_risk(cls, asset_data_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if _embedded_engine is None:
            raise AIClientError("Embedded Railway-AI engine is unavailable.")
        try:
            scored = _embedded_engine.failure_predictor.predict_risk(
                pd.DataFrame(asset_data_list)
            )
            return scored.to_dict(orient="records")
        except Exception as exc:
            raise AIClientError(f"Embedded risk prediction failed: {exc}") from exc

    @classmethod
    def optimize_maintenance_blocks(
        cls,
        tasks: list[dict[str, Any]],
        block_windows: list[dict[str, Any]],
        planning_hours: int = 24,
        max_manpower: int = 12,
    ) -> dict[str, Any]:
        if _embedded_engine is None:
            raise AIClientError("Embedded Railway-AI engine is unavailable.")
        try:
            scored_tasks = _embedded_engine.decision_engine.transform(pd.DataFrame(tasks))
            from src.optimization.block_optimizer import BlockOptimizer

            optimizer = BlockOptimizer(
                planning_hours=planning_hours,
                max_manpower=max_manpower,
            )
            windows = [{
                "block_id": window["block_id"],
                "section_id": window["section_id"],
                "start_slot": 0,
                "end_slot": planning_hours * 2,
            } for window in block_windows]
            allocations = optimizer.optimize(tasks=scored_tasks, block_windows=windows)
            return {
                "status": "OPTIMAL" if not allocations.empty else "INFEASIBLE",
                "allocated_tasks_count": len(allocations),
                "allocations": allocations.to_dict(orient="records"),
            }
        except Exception as exc:
            raise AIClientError(f"Embedded optimization failed: {exc}") from exc
