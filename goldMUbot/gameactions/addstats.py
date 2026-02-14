from functions.host_api import send_message, activate_window
import time


def main_player_add_stats(player_info="", main_player_reset=0):
    activate_window(player_info=player_info)

    sleept = 0.2
    if main_player_reset <= 161:
        send_message("/addene 3000", player_info=player_info)
        time.sleep(sleept)
        send_message("/addstr 29978", player_info=player_info)
        time.sleep(sleept)
        send_message("/addagi 29975", player_info=player_info)
        time.sleep(sleept)
        send_message("/addvit 29980", player_info=player_info)
        time.sleep(sleept)
    send_message("/re auto", player_info=player_info)


def second_player_add_stats(player_info="", second_player_reset=0):
    activate_window(player_info=player_info)

    # atleast 3-5 resets put on vitality to survive aida2 atleast 2000 points

    sleept = 0.2
    if second_player_reset <= 161:
        send_message("/addene 2000", player_info=player_info)
        time.sleep(sleept)
        send_message("/addstr 23000", player_info=player_info)
        time.sleep(sleept)
        send_message("/addagi 8500", player_info=player_info)
        time.sleep(sleept)
        send_message("/addvit 4000", player_info=player_info)
        time.sleep(sleept)
    send_message("/re auto", player_info=player_info)
