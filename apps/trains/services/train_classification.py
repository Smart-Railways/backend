from apps.trains.models import Train


def classify_train(train_name: str) -> tuple[str, int]:
    name = f" {train_name.upper().strip()} "

    # -------------------------------------------------
    # 1. Highest priority — 10
    # -------------------------------------------------

    # Vande Bharat
    if (
        " VANDE BHARAT " in name
        or " VB " in name
        or " V B " in name
    ):
        return Train.TrainType.VB, 10

    # Tejas
    if " TEJAS " in name:
        return Train.TrainType.TEJAS, 10

    # Rajdhani
    if " RAJDHANI " in name:
        return Train.TrainType.RAJDHANI, 10

    # Shatabdi / Jan Shatabdi
    if (
        " SHATABDI " in name
        or " JAN SHATABDI " in name
    ):
        return Train.TrainType.SHATABDI, 10

    # Gatimaan
    if " GATIMAAN " in name:
        return Train.TrainType.EXPRESS, 10

    # -------------------------------------------------
    # 2. Premium Express — 9
    # -------------------------------------------------

    if " DURONTO " in name:
        return Train.TrainType.EXPRESS, 9

    # -------------------------------------------------
    # 3. Humsafar / Superfast — 8
    # -------------------------------------------------

    if (
        " HUMSAFAR " in name
        or " SUPERFAST " in name
        or " SUPER FAST " in name
        or " SF " in name
        or " SFAST " in name
    ):
        return Train.TrainType.EXPRESS, 8

    # -------------------------------------------------
    # 4. Garib Rath — 7
    # -------------------------------------------------

    if " GARIB RATH " in name:
        return Train.TrainType.EXPRESS, 7

    # -------------------------------------------------
    # 5. Normal Express / Mail / Special — 6
    # -------------------------------------------------

    if (
        " EXPRESS " in name
        or " EXPRES " in name
        or " EXP " in name
        or " MAIL " in name
        or " SPL " in name
        or " SPECIAL " in name
    ):
        return Train.TrainType.EXPRESS, 6

    # -------------------------------------------------
    # 6. Freight / Goods — 5
    # -------------------------------------------------

    if (
        " FREIGHT " in name
        or " GOODS " in name
    ):
        return Train.TrainType.FREIGHT, 5

    # -------------------------------------------------
    # 7. Fallback — Passenger
    # -------------------------------------------------

    return Train.TrainType.PASSENGER, 5