import os
import logging
from typing import Dict, Any, List, Optional
import pandas as pd
import requests

logger = logging.getLogger(__name__)

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "").rstrip("/")
AI_TIMEOUT = int(os.getenv("AI_TIMEOUT_SECONDS", "15"))
PREFER_EMBEDDED_AI = os.getenv("PREFER_EMBEDDED_AI", "True").lower() in ("true", "1", "yes")

# Try initializing the embedded in-memory ML engine
_embedded_engine = None
try:
    from src.services.ml_engine import RailwayMLEngine
    _embedded_engine = RailwayMLEngine()
    logger.info("Embedded Railway-AI ML Engine successfully loaded in-memory.")
except Exception as _exc:
    logger.warning("Could not initialize embedded ML Engine (%s). Will rely on HTTP fallback.", _exc)


class AIClientError(Exception):
    """Base exception for Railway AI Service failures."""
    def __init__(self, message: str, status_code: Optional[int] = None, details: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details


class RailwayAIClient:
    """
    Unified AI Client.
    1. Primary mode: Direct In-Memory execution via embedded RailwayMLEngine (zero HTTP overhead).
    2. Fallback mode: HTTP call to AI_SERVICE_URL if embedded engine is unavailable.
    """

    @classmethod
    def is_healthy(cls) -> bool:
        """Returns True if either in-memory engine or external HTTP service is online."""
        import apps.blocks.ai_client as _self_mod
        prefer_embedded = getattr(_self_mod, "PREFER_EMBEDDED_AI", True)
        service_url = getattr(_self_mod, "AI_SERVICE_URL", "")

        if prefer_embedded and _embedded_engine is not None:
            return True

        if service_url:
            try:
                r = requests.get(f"{service_url}/health", timeout=3)
                return r.status_code == 200 and r.json().get("status") == "ok"
            except Exception:
                return False

        return _embedded_engine is not None if prefer_embedded else False

    @classmethod
    def predict_asset_risk(cls, asset_data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Runs XGBoost failure risk prediction.
        Executes in-memory if embedded engine is available; otherwise calls HTTP service.
        """
        # 1. In-Memory Embedded Execution
        if PREFER_EMBEDDED_AI and _embedded_engine is not None:
            try:
                df = pd.DataFrame(asset_data_list)
                scored_df = _embedded_engine.failure_predictor.predict_risk(df)
                return scored_df.to_dict(orient="records")
            except Exception as exc:
                logger.error("In-memory failure risk prediction error: %s", exc)
                raise AIClientError(f"In-memory prediction failed: {exc}", status_code=500) from exc

        # 2. HTTP Fallback
        if AI_SERVICE_URL:
            url = f"{AI_SERVICE_URL}/predict-failure-risk"
            try:
                resp = requests.post(url, json=asset_data_list, timeout=AI_TIMEOUT)
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.RequestException as exc:
                logger.error("HTTP AI Service failure risk prediction error: %s", exc)
                raise AIClientError(f"AI HTTP service unavailable: {exc}", status_code=502) from exc

        raise AIClientError("No AI engine available (neither embedded nor HTTP)", status_code=503)

    @classmethod
    def optimize_maintenance_blocks(
        cls,
        tasks: List[Dict[str, Any]],
        block_windows: List[Dict[str, Any]],
        planning_hours: int = 6,
        max_manpower: int = 12,
    ) -> Dict[str, Any]:
        """
        Runs Google OR-Tools CP-SAT discrete block optimizer.
        Executes in-memory if embedded engine is available; otherwise calls HTTP service.
        """
        # 1. In-Memory Embedded Execution
        if PREFER_EMBEDDED_AI and _embedded_engine is not None:
            try:
                tasks_df = pd.DataFrame(tasks)
                scored_tasks = _embedded_engine.decision_engine.transform(tasks_df)

                formatted_windows = []
                for w in block_windows:
                    formatted_windows.append({
                        "block_id": w["block_id"],
                        "section_id": w["section_id"],
                        "start_slot": 0,
                        "end_slot": int(planning_hours * 2),  # 30-min slots
                    })

                result_df = _embedded_engine.block_optimizer.optimize(
                    tasks=scored_tasks,
                    block_windows=formatted_windows,
                )

                return {
                    "status": "OPTIMAL" if not result_df.empty else "INFEASIBLE",
                    "allocated_tasks_count": len(result_df),
                    "allocations": result_df.to_dict(orient="records"),
                }
            except Exception as exc:
                logger.error("In-memory CP-SAT block optimization error: %s", exc)
                raise AIClientError(f"In-memory optimization failed: {exc}", status_code=500) from exc

        # 2. HTTP Fallback
        if AI_SERVICE_URL:
            url = f"{AI_SERVICE_URL}/optimize-blocks"
            payload = {
                "planning_hours": planning_hours,
                "max_manpower": max_manpower,
                "tasks": tasks,
                "block_windows": block_windows,
            }
            try:
                resp = requests.post(url, json=payload, timeout=AI_TIMEOUT)
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.RequestException as exc:
                logger.error("HTTP AI Service block optimization error: %s", exc)
                raise AIClientError(f"AI HTTP service unavailable: {exc}", status_code=502) from exc

        raise AIClientError("No AI engine available (neither embedded nor HTTP)", status_code=503)

