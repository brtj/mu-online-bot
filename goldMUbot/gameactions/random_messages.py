import random

OPENERS = [
    "Super party",
    "Fajny spot",
    "Dobry exp",
    "Zapraszam party",
    "Wbijajcie",
    "Ktoś na pt?",
    "Mam miejsce",
    "Brakuje 1 do party",
    "Mega resp",
    "Pusty spot",
    "AFK exp",
    "Szybki lvl",
]

SUFFIXES = [
    "(sub2)",
]

EXTRAS = [
    "",
    "bez ks",
    "dropi bless",
    "zen leci",
    "dobry resp",
    "spokojny spot",
    "można afk",
]

def generate_mu_party_message(map_name, x, y):
    opener = random.choice(OPENERS)
    suffix = random.choice(SUFFIXES)
    extra = random.choice(EXTRAS)
    global_message = "/post"
    # kilka różnych konstrukcji zdań (KLUCZOWE)
    patterns = [
        f"{global_message} {opener} {suffix} na {map_name} ({x},{y})",
        f"{global_message} {opener} {suffix} {map_name} ({x},{y})",
        f"{global_message} {opener} {extra} {suffix} na {map_name} ({x},{y})",
        f"{global_message} {map_name} ({x},{y}) {opener.lower()} {suffix}",
        f"{global_message} {opener.lower()} {suffix} {extra} {map_name} ({x},{y})",
        f"{global_message} {suffix} {opener.lower()} na {map_name} ({x},{y})",
    ]

    # usuwamy podwójne spacje gdy extra == ""
    msg = random.choice(patterns)
    msg = " ".join(msg.split())

    return msg


RESETS_MESS = [
    "U mnie juz {r} reset, ktos dogania?",
    "{r} reset wbity, ile macie?",
    "Zrobilem {r} reset, jak u was?",
    "{r} reset i lecimy dalej",
    "Dobity {r} reset, ktos wiecej?",
    "Mam {r} reset na liczniku",
    "{r} reset wpadl, jak u was?",
    "Dopiero {r} reset, a wy?",
    "No i pyk {r} reset",
    "Skonczylem {r} reset, jeszcze droga :D",
]

def generate_reset_message(resets: int | None = None):
    if resets is None:
        resets = random.randint(80, 220)

    template = random.choice(RESETS_MESS)
    return template.format(r=resets)


SPOT_MESS = [
    "Ja tu tylko na chwilke do {level_max} lvlu i zmykam",
    "Tylko do {level_max} lvlu i ide dalej",
    "Dobije {level_max} lvl i schodze",
    "Do {level_max} lvl posiedze chwile",
    "Tylko wbije {level_max} lvl i uciekam",
    "Chwilka expa do {level_max} lvl i zmykam",
    "Szybko do {level_max} lvl i znikam",
    "Do {level_max} lvl i oddaje spot",
    "Posiedze do {level_max} lvl ok?",
    "Tylko {level_max} lvl i wasz spot",
]

def generate_spot_message(level_max: int):
    return random.choice(SPOT_MESS).format(level_max=level_max)[:50]