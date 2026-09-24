"""Celery application. With no broker configured (or CELERY_EAGER=true) tasks run inline,
so the product works without Redis; in Docker Compose a real worker consumes the queue."""
from __future__ import annotations

from celery import Celery

from app.core.config import get_settings

settings = get_settings()
broker = settings.celery_broker_url or settings.redis_url or "memory://"

celery_app = Celery("pathfinder", broker=broker, backend=(settings.redis_url or "cache+memory://"), include=["app.workers.tasks"])
celery_app.conf.update(
    task_always_eager=settings.celery_eager or broker == "memory://",
    task_eager_propagates=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_time_limit=300,
    worker_max_tasks_per_child=200,
    result_expires=3600,
)


def run_task(task, *args, **kwargs) -> dict:
    """Run inline when eager, otherwise enqueue. Returns a uniform status envelope."""
    if celery_app.conf.task_always_eager:
        return {"status": "completed", "result": task.apply(args=args, kwargs=kwargs).get()}
    res = task.apply_async(args=args, kwargs=kwargs)
    return {"status": "queued", "task_id": res.id}
