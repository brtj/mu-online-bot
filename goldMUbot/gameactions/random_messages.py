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
    "{r} reset, mama juz dumna",
    "Spokojnie, tylko {r} reset dzisiaj",
    "{r} reset, zycie to grind",
    "Kolejny {r} reset, dotkne trawy kiedys",
    "{r} reset, nadal bez dropa oczywiscie",
    "Mam {r} reset, a dalej bieda",
    "{r} reset i dalej Lorencia",
    "{r} reset wbity, progres ogromny xd",
    "Tylko {r} reset? myslalem wiecej",
    "{r} reset i dalej nic nie umiem",
    "O nie, znowu {r} reset przypadkiem",
    "{r} reset, jeszcze tylko tysiac",
    "{r} reset i nadal ten sam spot",
    "Po {r} resetach znam kazdy pixel",
    "{r} reset, zycie prywatne offline",
    "{r} reset, server zyje dzieki mnie",
    "{r} reset wbity, idziemy spac (nie)",
    "{r} reset i dalej bez blessow",
    "{r} reset, ekonomia serwera uratowana",
    "{r} reset, achievement bez znaczenia",
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


WARP_MESS = [
    "Dobra zwijam się do {desired_location}",
    "Lecę już do {desired_location}",
    "Zbieram manatki, kierunek {desired_location}",
    "Zmieniam mapę na {desired_location}",
    "Przenoszę się do {desired_location}",
    "Czas na {desired_location}, nara",
    "Idę ogarnąć {desired_location}",
    "Kieruję się do {desired_location}",
    "Skaczę teraz na {desired_location}",
    "Teleport na {desired_location}",
    "Spotykamy się w {desired_location}",
    "Uciekam na {desired_location}",
    "Czas sprawdzić {desired_location}",
    "Znikam stąd, lecę {desired_location}",
    "Przeprowadzka do {desired_location}",
    "Szybki wypad do {desired_location}",
    "Wracam na {desired_location}",
    "Pora odwiedzić {desired_location}",
    "Przerzucam się na {desired_location}",
    "Idę farmić w {desired_location}",
    "Ląduję zaraz w {desired_location}",
]


def generate_warp_message(desired_location: int):
    return random.choice(WARP_MESS).format(desired_location=desired_location)[:50]