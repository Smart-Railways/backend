def parse_train_response(response: dict) -> dict:
    """
    Normalize the combined /train/:trainNumber response.

    Expected response is already the inner "data" object because
    RailwayClient._get() unwraps the API response.
    """

    if not isinstance(response, dict) or not response:
        raise ValueError(
            "Railway service returned an empty response."
        )

    status = response.get("status") or {}
    route = response.get("route") or []

    if not isinstance(status, dict):
        status = {}
    if not isinstance(route, list):
        route = []

    normalized_route = []

    for station in route:
        if not isinstance(station, dict):
            continue
        normalized_route.append({
            "position": station.get("position"),
            "station_name": station.get("stationName"),
            "station_code": station.get("stationCode"),
            "day": station.get("day"),
            "arrival": station.get("arrival"),
            "departure": station.get("departure"),
            "halt_minutes": station.get("haltMinutes"),
            "distance_km": station.get("distanceKm"),
        })

    delay_minutes = status.get("delayMinutes")
    if delay_minutes is not None:
        try:
            delay_minutes = int(delay_minutes)
        except (TypeError, ValueError):
            delay_minutes = None

    classes = response.get("classes", [])
    if not isinstance(classes, list):
        classes = []

    status_label = status.get("label")
    if status_label is not None and not isinstance(status_label, str):
        status_label = str(status_label)

    return {
        "train_number": response.get("trainNumber"),
        "train_name": response.get("trainName"),
        "from_station_name": response.get("fromStationName"),
        "to_station_name": response.get("toStationName"),
        "travel_time": response.get("travelTime"),
        "runs_on": response.get("runsOn"),
        "train_type": response.get("type"),
        "classes": classes,

        "delay_minutes": delay_minutes,
        "status_label": status_label,

        "route": normalized_route,
    }
