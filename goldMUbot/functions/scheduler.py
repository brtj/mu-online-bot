from apscheduler.schedulers.background import BackgroundScheduler
import datetime
from functions.state_singleton import STATE

def set_run_speedrun_true():
	print(f"[SPEEDRUN] Ustawiam run_speedrun=True o {datetime.datetime.now()}")
	STATE.update_dict('main_player_data', {'run_speedrun': True})

def log_daily_reset_value():
	today = datetime.date.today().isoformat()
	main_player_data = STATE.get('main_player_data', {}) or {}
	reset_value = main_player_data.get('reset')
	if reset_value is None:
		print(f"[RESET-LOG] Brak wartości reset w main_player_data ({today})")
		return

	reset_history = main_player_data.get('reset_history', [])
	if not isinstance(reset_history, list):
		reset_history = []

	entry = {"date": today, "reset": reset_value}
	if reset_history and isinstance(reset_history[-1], dict) and reset_history[-1].get('date') == today:
		reset_history[-1] = entry
	else:
		reset_history.append(entry)

	STATE.update_dict('main_player_data', {'reset_history': reset_history})
	print(f"[RESET-LOG] Zapisano reset={reset_value} dla {today}")

def start_scheduler():
	scheduler = BackgroundScheduler()
	# Codziennie o 04:00 (zmień hour/minute jeśli chcesz inną godzinę)
	scheduler.add_job(set_run_speedrun_true, 'cron', hour=4, minute=0)
	# Logowanie resetów o północy dla wykresu w UI
	scheduler.add_job(log_daily_reset_value, 'cron', hour=0, minute=1)
	scheduler.start()
