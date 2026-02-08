from functions.host_api import send_message, activate_window
import time


def main_player_add_stats(player_info="", main_player_reset=0):
    activate_window(player_info=player_info)

    sleept = 0.2
    if main_player_reset <= 161:
        send_message("/addene 3000", player_info=player_info); time.sleep(sleept)
        send_message("/addstr 29978", player_info=player_info); time.sleep(sleept)
        send_message("/addagi 29975", player_info=player_info); time.sleep(sleept)
        send_message("/addvit 29980", player_info=player_info); time.sleep(sleept)
    send_message("/re auto", player_info=player_info)


def second_player_add_stats(player_info="", second_player_reset=0):
    activate_window(player_info=player_info)

    sleept = 0.2
    if second_player_reset <= 161:
        send_message("/addene 150", player_info=player_info); time.sleep(sleept)
        send_message("/addstr 300", player_info=player_info); time.sleep(sleept)
        send_message("/addagi 300", player_info=player_info); time.sleep(sleept)
        send_message("/addvit 200", player_info=player_info); time.sleep(sleept)
    send_message("/re auto", player_info=player_info)