WEEKDAY_NAMES = {
    0: "Segunda-feira",
    2: "Quarta-feira",
    4: "Sexta-feira",
}

SCHOOL = "E.E. Madre Serafina de Jesus"
HOME_ADDRESS = "Rua Dr. Carlos Prates, 1332 - Centro"

PICKUP_SCHEDULES = {
    0: (
        ("12:10 até 12:30", SCHOOL),
        ("14:10 até 14:40", SCHOOL),
        ("17:00 até 19:00", HOME_ADDRESS),
    ),
    2: (
        ("12:10 até 12:30", SCHOOL),
        ("13:20 até 14:10", SCHOOL),
        (
            "15:00 até 17:30",
            f"{SCHOOL} (marcar o horário exato pelo WhatsApp)",
        ),
        ("19:00 até 20:00", HOME_ADDRESS),
    ),
    4: (
        ("12:10 até 12:30", SCHOOL),
        ("14:10 até 14:40", SCHOOL),
        ("17:00 até 19:00", HOME_ADDRESS),
    ),
}


def pickup_options_for(pickup_date):
    return PICKUP_SCHEDULES.get(pickup_date.weekday(), ())


def pickup_date_label(pickup_date):
    weekday = WEEKDAY_NAMES.get(pickup_date.weekday(), "")
    return f"{weekday} — {pickup_date:%d/%m/%Y}" if weekday else f"{pickup_date:%d/%m/%Y}"
