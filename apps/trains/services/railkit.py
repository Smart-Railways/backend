import os

import requests
from django.core.exceptions import ImproperlyConfigured


class RailKitError(Exception):
    """Raised when the RailKit API returns an unexpected error."""

    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class RailKitClient:

    def __init__(self):
        self.api_key = os.getenv("RAILKIT_API_KEY")
        self.base_url = os.getenv(
            "RAILKIT_BASE_URL",
            "https://railkit.in",
        )

        if not self.api_key:
            raise ImproperlyConfigured(
                "RAILKIT_API_KEY is not configured."
            )

        self.session = requests.Session()

        self.session.headers.update({
            "Accept": "application/json",
            "x-api-key": self.api_key,
        })

    def _get(self, endpoint, params=None):
        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.get(
                url,
                params=params,
                timeout=15,
            )

        except requests.RequestException as exc:
            raise RailKitError(
                f"RailKit request failed: {exc}"
            ) from exc

        if response.status_code == 429:
            raise RailKitError(
                "RailKit API rate limit exceeded.",
                status_code=429,
            )

        if not response.ok:
            try:
                data = response.json()
                error = data.get("error", "")
            except ValueError:
                error = response.text

            # Expected situation:
            # Train does not have data for this date.
            if (
                response.status_code == 400
                and "Train data not available for date" in error
            ):
                raise RailKitError(
                    str(error),
                    status_code=400,
                )

            # Unexpected API error
            raise RailKitError(
                f"RailKit API returned HTTP {response.status_code}: "
                f"{response.text}",
                status_code=response.status_code,
            )

        try:
            data = response.json()

        except ValueError as exc:
            raise RailKitError(
                "RailKit returned invalid JSON."
            ) from exc

        if data.get("success") is False:
            error = data.get(
                "error",
                "Unknown RailKit error",
            )

            raise RailKitError(
                str(error),
                status_code=response.status_code,
            )

        return data

    def search_trains_between_stations(
        self,
        from_station: str,
        to_station: str,
        date: str | None = None,
    ):
        endpoint = (
            f"/api/searchTrainBetweenStations/"
            f"{from_station.upper()}/"
            f"{to_station.upper()}"
        )

        params = {}

        if date:
            params["date"] = date

        return self._get(
            endpoint,
            params=params,
        )

    def track_train(
        self,
        train_number: str,
        date: str,
    ):
        endpoint = (
            f"/api/trackTrain/"
            f"{train_number}/"
            f"{date}"
        )

        return self._get(endpoint)