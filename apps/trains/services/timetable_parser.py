from datetime import time


WEEKDAY_INDEX = {
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}


def parse_time(value: str) -> time:
    """Convert HH:MM into a Python time object."""
    return time.fromisoformat(value)


def parse_running_days(value) -> str:
    """Normalize API weekday labels to the TrainSchedule Monday-Sunday mask."""
    if not value:
        return "1111111"
    if isinstance(value, str) and len(value) == 7 and set(value) <= {"0", "1"}:
        return value

    days = value.split(",") if isinstance(value, str) else value
    if not isinstance(days, list):
        return "1111111"

    mask = ["0"] * 7
    for day in days:
        index = WEEKDAY_INDEX.get(str(day).strip().lower()[:3])
        if index is not None:
            mask[index] = "1"
    return "".join(mask) if "1" in mask else "1111111"


def parse_timetable_response(response: dict | list) -> list[dict]:
    """
    Convert RailKit timetable response into our internal format.

    Does not touch the database.
    """

    if isinstance(response, dict):
        if response.get("success") is False:
            raise ValueError(response.get("error", "RailKit request failed."))
        trains = response.get("data", [])
    elif isinstance(response, list):
        # RailKitClient._get() unwraps successful API responses.
        trains = response
    else:
        raise ValueError("Railway service returned an invalid timetable response.")

    parsed_trains = []

    for train in trains:
        from_time = parse_time(train.get("from_time") or train["departure"])
        to_time = parse_time(train.get("to_time") or train["arrival"])

        # Train crosses midnight if arrival time is
        # earlier than departure time.
        crosses_midnight = to_time < from_time

        parsed_trains.append({
            "train_number": train.get("train_no") or train["trainNumber"],
            "train_name": train.get("train_name") or train["trainName"],

            "from_station": train.get("from_stn_name") or train["fromStationName"],
            "from_station_code": train.get("from_stn_code") or train["fromStationCode"],

            "to_station": train.get("to_stn_name") or train["toStationName"],
            "to_station_code": train.get("to_stn_code") or train["toStationCode"],

            "scheduled_entry_time": from_time,
            "scheduled_exit_time": to_time,

            "running_days": parse_running_days(
                train.get("running_days") or train.get("runsOn")
            ),
            "distance_km": float(train.get("distance", 0)),
            "halts": train.get("halts", 0),
            "scheduled_exit_day_offset": int(crosses_midnight),
        })

    return parsed_trains
