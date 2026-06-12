"""Background scheduler for Uzum API sync (06:00 and 18:00 Asia/Tashkent)."""

from __future__ import annotations

import logging
import threading
from typing import Optional

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
except ImportError as exc:
    raise ImportError(
        "APScheduler is required for Uzum scheduled sync. "
        "Install with: pip install APScheduler>=3.10.4"
    ) from exc

from app.services.uzum_time import UZ_TZ

logger = logging.getLogger(__name__)

_cycle_lock = threading.Lock()
_scheduler: Optional[BackgroundScheduler] = None


def try_acquire_cycle_lock() -> bool:
    return _cycle_lock.acquire(blocking=False)


def release_cycle_lock() -> None:
    if _cycle_lock.locked():
        _cycle_lock.release()


def _run_scheduled_job() -> None:
    from app.services.uzum_sync import run_scheduled_sync_cycle

    run_scheduled_sync_cycle()


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return

    _scheduler = BackgroundScheduler(timezone=UZ_TZ)
    trigger = CronTrigger(hour="6,18", minute=0, timezone=UZ_TZ)
    _scheduler.add_job(
        _run_scheduled_job,
        trigger=trigger,
        id="uzum_scheduled_sync",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )
    _scheduler.start()
    logger.info("Uzum scheduled sync scheduler started (06:00 and 18:00 %s)", UZ_TZ)


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is None:
        return
    _scheduler.shutdown(wait=False)
    _scheduler = None
    logger.info("Uzum scheduled sync scheduler stopped")
