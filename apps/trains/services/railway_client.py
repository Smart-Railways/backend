import os

import requests


class RailKitError(Exception):
    """
    Raised when the local railway data service returns an error.

    NOTE:
    The class name is temporarily kept as RailKitError
    to avoid breaking existing imports.
    """

    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class RailKitClient:
    """
    Client for our local Node railway service.

    Local service:
        http://localhost:3001

    This service internally uses indian-rail-mcp.
    """

    def __init__(self):
        self.base_url = os.getenv(
            "INDIAN_RAIL_SERVICE_URL",
            "http://localhost:3001",
        )

        self.session = requests.Session()

        self.session.headers.update({
            "Accept": "application/json",
        })

    def _get(self, endpoint, params=None):
        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.get(
                url,
                params=params,
                timeout=30,
            )

        except requests.RequestException as exc:
            raise RailKitError(
                f"Railway service request failed: {exc}"
            ) from exc

        if not response.ok:
            raise RailKitError(
                (
                    f"Railway service returned HTTP "
                    f"{response.status_code}: "
                    f"{response.text}"
                ),
                status_code=response.status_code,
            )

        try:
            payload = response.json()

        except ValueError as exc:
            raise RailKitError(
                "Railway service returned invalid JSON."
            ) from exc

        if payload.get("success") is False:
            raise RailKitError(
                str(
                    payload.get(
                        "error",
                        "Unknown railway service error",
                    )
                ),
                status_code=response.status_code,
            )

        return payload.get("data")

    # --------------------------------------------------
    # TRAINS BETWEEN TWO STATIONS
    # --------------------------------------------------

    def search_trains_between_stations(
        self,
        from_station: str,
        to_station: str,
        date: str | None = None,
    ):
        params = {
            "from": from_station.upper(),
            "to": to_station.upper(),
        }

        if date:
            params["date"] = date

        return self._get(
            "/trains-between",
            params=params,
        )

    # --------------------------------------------------
    # COMBINED TRAIN INFORMATION + LIVE STATUS
    # --------------------------------------------------

    def get_train(
        self,
        train_number: str,
        date: str | None = None,
    ):
        params = {}

        if date:
            params["date"] = date

        return self._get(
            f"/train/{train_number}",
            params=params,
        )

    # --------------------------------------------------
    # DETAILED LIVE TRACKING
    # --------------------------------------------------

    def track_train(
        self,
        train_number: str,
        date: str | None = None,
    ):
        params = {}

        if date:
            params["date"] = date

        return self._get(
            f"/track/{train_number}",
            params=params,
        )

    # --------------------------------------------------
    # LIVE STATION
    # --------------------------------------------------

    def get_live_station(
        self,
        station_code: str,
    ):
        return self._get(
            f"/station/{station_code.upper()}"
        )