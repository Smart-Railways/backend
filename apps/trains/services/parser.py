from datetime import datetime


def parse_railkit_date(value: str) -> datetime:
    """
    Convert RailKit date/time strings into Python datetime objects.

    Example:
        "16:58 02-Sep"
    """
    return datetime.strptime(value, "%H:%M %d-%b")


def get_stoppage_stations(timeline: list[dict]) -> list[dict]:
    """
    Return only stations where the train has a stoppage.
    """

    return [
        station
        for station in timeline
        if station.get("type") == "stoppage"
    ]


def parse_live_train_response(response: dict) -> dict:
    """
    Normalize a RailKit live-tracking response.

    This function does NOT save anything to the database.
    """

    if not response.get("success"):
        raise ValueError(
            response.get("error", "RailKit request failed.")
        )

    data = response["data"]

    timeline = data.get("timeline", [])

    stoppages = get_stoppage_stations(timeline)

    return {
        "train_number": data["trainNo"],
        "train_name": data["trainName"],
        "service_date": data["date"],
        "status_note": data.get("statusNote"),
        "last_update": data.get("lastUpdate"),
        "current_station_code": data.get("currentStationCode"),
        "total_stations": data.get("totalStations"),
        "stoppages": stoppages,
    }