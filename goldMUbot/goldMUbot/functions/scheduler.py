from apscheduler.schedulers.background import BackgroundScheduler
import datetime
from functions.state_singleton import STATE

def set_run_speedrun_true():
	print(f"[SPEEDRUN] Ustawiam run_speedrun=True o {datetime.datetime.now()}")
	STATE.update_dict('player_data', {'run_speedrun': True})

def start_scheduler():
	scheduler = BackgroundScheduler()
	# Codziennie o 04:00 (zmień hour/minute jeśli chcesz inną godzinę)
	scheduler.add_job(set_run_speedrun_true, 'cron', hour=4, minute=0)
	scheduler.start()
