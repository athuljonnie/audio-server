from apscheduler.schedulers.background import BackgroundScheduler
from .utils import cleanup_old_files, INCOMING, CONVERTED
from dotenv import load_dotenv; load_dotenv()
import os, logging

log = logging.getLogger("cleanup")

def start_cleanup(cron_expr: str):
    sched = BackgroundScheduler(daemon=True)
    minute, hour, dom, month, dow = cron_expr.split()
    sched.add_job(
        lambda: (cleanup_old_files(INCOMING), cleanup_old_files(CONVERTED)),
        "cron",
        minute=minute, hour=hour, day=dom, month=month, day_of_week=dow,
    )
    sched.start()
    log.info("Cleanup job scheduled: %s", cron_expr)
