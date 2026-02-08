def get_hud_xy(hud_coords: list, hud_id: str) -> tuple[int, int]:
    for item in hud_coords:
        if item.get("id") == hud_id:
            return item["x"], item["y"]
    raise KeyError(f"HUD id '{hud_id}' not found")

#HUD COORDS for 800x600 resolution, if u play on different resolution, u need to adjust them, they are used to click on specific places on screen, like safe spot, inventory icon, etc
HUD_COORDS = [
    {
        "id": "middle_screen",
        "description": "Center of the screen with 800x600 resolution",
        "x": 400,
        "y": 300
    },
    {
        "id": "safe_spot",
        "description": "Safe spot for mouse top left next to location (not covering it)",
        "x": 9,
        "y": 40
    },
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
        "id": "menu_system_icon",
        "description": "Menu icon to click to open popup menu for system/help/guild",
        "x": 715,
        "y": 602
    },
    {
        "id": "inventory_opened_close_icon",
        "description": "Inventory close X icon to click to close iventory",
        "x": 648,
        "y": 516
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
    },
    {
        "id": "shortcut_r_box",
        "description": "Shortcut R box next to Health",
        "x": 220,
        "y": 600
    },
    {
        "id": "shortcut_e_box",
        "description": "Shortcut E box next to Health",
        "x": 180,
        "y": 600
    },
    {
        "id": "shortcut_w_box",
        "description": "Shortcut W box next to Health",
        "x": 142,
        "y": 600
    },
    {
        "id": "shortcut_q_box",
        "description": "Shortcut Q box next to Health",
        "x": 101,
        "y": 600
    },
    {
        "id": "helper_error_box",
        "description": "Click on Helper Error Box. It appears if helper clicked on safe location like city, etc",
        "x": 407,
        "y": 303
    },
    {
        "id": "chat_over_black_box_hover",
        "description": "Position of black box of chat, if u need to click it or something",
        "x": 533,
        "y": 572
    },
    {
        "id": "jewel_bank_inventory_icon",
        "description": "Icon of jewel bank, where u store all jewels",
        "x": 643,
        "y": 487
    },
    {
        "id": "party_window_create_party_icon",
        "description": "Party window openened, location of Create Party tab",
        "x": 649,
        "y": 68
    },
    {
        "id": "party_window_save_settings_icon",
        "description": "Party window openened, location of Create Party tab, save settings button",
        "x": 713,
        "y": 409
    },
    {
        "id": "party_window_enable_box",
        "description": "Party window enable box, where tick need to be placed, white box",
        "x": 646,
        "y": 113
    },
    {
        "id": "party_window_join_party_button",
        "description": "Party window Join Party button after click on party",
        "x": 717,
        "y": 435
    },
    {
        "id": "dark_horse_icon",
        "description": "Dark horse icon on left, below location, where is health and name",
        "x": 35,
        "y": 70
    },
    {
        "id": "skill_number_1_icon",
        "description": "Skill bar, first skill number 1",
        "x": 325,
        "y": 600
    },
    {
        "id": "jewel_bank_1st_all_icon",
        "description": "Jewel bank, first all icon to click to put chaos jewels in bank",
        "x": 544,
        "y": 274
    },
    {
        "id": "jewel_bank_2nd_all_icon",
        "description": "Jewel bank, 2nd all icon to click to put chaos jewels in bank",
        "x": 544,
        "y": 296
    },
    {
        "id": "jewel_bank_3rd_all_icon",
        "description": "Jewel bank, 3rd all icon to click to put chaos jewels in bank",
        "x": 544,
        "y": 321
    },
    {
        "id": "jewel_bank_4th_all_icon",
        "description": "Jewel bank, 4th all icon to click to put chaos jewels in bank",
        "x": 544,
        "y": 346
    },
    {
        "id": "jewel_bank_5th_all_icon",
        "description": "Jewel bank, 5th all icon to click to put chaos jewels in bank",
        "x": 544,
        "y": 373
    },
    {
        "id": "jewel_bank_6th_all_icon",
        "description": "Jewel bank, 6th all icon to click to put chaos jewels in bank",
        "x": 544,
        "y": 395
    },
    {
        "id": "jewel_bank_7th_all_icon",
        "description": "Jewel bank, 7th all icon to click to put chaos jewels in bank",
        "x": 544,
        "y": 420
    },
    {
        "id": "jewel_bank_8th_all_icon",
        "description": "Jewel bank, 8th all icon to click to put chaos jewels in bank",
        "x": 544,
        "y": 450
    },
    {
        "id": "speedrun_run_icon",
        "description": "Speedrun run icon",
        "x": 298,
        "y": 39
    },
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
    {
        "id": "health_box",
        "description": "Location box where OCR can read health value",
        "rect":{
            "x": 245, "y": 595, "w": 45, "h": 20
        },
    },
    {
        "id": "exppm_box",
        "description": "Location box where OCR can read EXP per minute value",
        "rect":{
            "x": 125, "y": 220, "w": 80, "h": 15
        },
    },
    {
        "id": "mapon_box",
        "description": "Location box where OCR can compare images and check if MAP is ON, Im checking white box ",
        "rect":{
            "x": 410, "y": 565, "w": 10, "h": 10
        },
    },
    {
        "id": "chat_opened_icon_box",
        "description": "Location box of chat_on.png. When chat is opened you see chat cloud (first white icon on left in chat navbar)",
        "rect":{
            "x": 268, "y": 536, "w": 26, "h": 26
        },
    },
    {
        "id": "inventory_state_box",
        "description": "Location box of close Inventory X (when opened)",
        "rect":{
            "x": 630, "y": 496, "w": 30, "h": 40
        },
    },  
]


