from datetime import time


def parse_time(value: str) -> time:
    """Convert HH:MM into a Python time object."""
    return time.fromisoformat(value)


def parse_timetable_response(response: dict) -> list[dict]:
    """
    Convert RailKit timetable response into our internal format.

    Does not touch the database.
    """

    if not response.get("success"):
        raise ValueError(
            response.get("error", "RailKit request failed.")
        )

    trains = response.get("data", [])

    parsed_trains = []

    for train in trains:
        from_time = parse_time(train["from_time"])
        to_time = parse_time(train["to_time"])

        # Train crosses midnight if arrival time is
        # earlier than departure time.
        crosses_midnight = to_time < from_time

        parsed_trains.append({
            "train_number": train["train_no"],
            "train_name": train["train_name"],

            "from_station": train["from_stn_name"],
            "from_station_code": train["from_stn_code"],

            "to_station": train["to_stn_name"],
            "to_station_code": train["to_stn_code"],

            "scheduled_entry_time": from_time,
            "scheduled_exit_time": to_time,

            "running_days": train.get("running_days", "1111111"),
            "distance_km": float(train.get("distance", 0)),
            "halts": train.get("halts", 0),
            "scheduled_exit_day_offset": int(crosses_midnight),
        })

    return parsed_trains