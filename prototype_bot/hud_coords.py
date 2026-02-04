HUD_COORDS = [
    {
        "id": "helper_icon",
        "description": "Helper STOP/RUN state icon, click it to run/stop",
        "x": 188,
        "y": 40
    },
    {
        "id": "inventory_icon",
        "description": "Inventory icon to click to open iventory",
        "x": 650,
        "y": 602
    },
    {
        "id": "character_icon",
        "description": "Character icon to click on it to read stats",
        "x": 620,
        "y": 602
    },
    {
        "id": "helper_warning_message",
        "description": "Helper warning message if inventory is opened or something",
        "x": 620,
        "y": 602
    }
]

def get_rect(rect_id: str) -> dict:
    for item in HUD_RECT_COORDS:
        if item["id"] == rect_id:
            return item["rect"]
    raise KeyError(f"HUD rect not found: {rect_id}")

HUD_RECT_COORDS = [
    {
        "id": "location_box",
        "description": "Location box where you can find Map name + coords example: Atlans (183,92)",
        "rect":{
            "x":29,"y":35,"w":110,"h":12
        },
    },
    {
        "id": "helper_state",
        "description": "Location box where helper has icon play/pause, matching image",
        "rect":{
            "x":150,"y":25,"w":50,"h":40
        },
    },
]

