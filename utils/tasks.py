import datetime
import json
from typing import Awaitable, Callable

from sqlalchemy import Connection, delete, insert, select, update

from database import tasks

TASK_HANDLERS: dict[str, Callable[..., Awaitable[None]]] = {}

RETRY_DELAYS = [5, 10, 15]
MAX_FAILED_TASKS = 100


def register_task(task_type: str):
    def decorator(func: Callable[..., Awaitable[None]]):
        TASK_HANDLERS[task_type] = func
        return func

    return decorator


def create_task(c: Connection, direction: str, task_type: str, data: dict) -> None:
    c.execute(
        insert(tasks).values(
            direction=direction,
            type=task_type,
            data=json.dumps(data),
            created_at=datetime.datetime.now(datetime.UTC),
        )
    )


def get_pending_tasks(c: Connection, direction: str = "bot"):
    now = datetime.datetime.now(datetime.UTC)

    rows = c.execute(
        select(
            tasks.c.id,
            tasks.c.type,
            tasks.c.data,
            tasks.c.attempts,
            tasks.c.next_attempt,
        )
        .where((tasks.c.direction == direction) & (tasks.c.error.is_(None)))
        .order_by(tasks.c.id)
    ).fetchall()

    pending = []
    for row in rows:
        next_attempt = row[4]
        if next_attempt is not None:
            if next_attempt.tzinfo is None:
                next_attempt = next_attempt.replace(tzinfo=datetime.UTC)

            if next_attempt > now:
                continue

        pending.append(row)

    return pending


def delete_task(c: Connection, task_id: int) -> None:
    c.execute(delete(tasks).where(tasks.c.id == task_id))


def fail_task(c: Connection, task_id: int, error: str) -> None:
    c.execute(update(tasks).where(tasks.c.id == task_id).values(error=error))
    prune_failed_tasks(c)


def retry_or_fail(c: Connection, task_id: int, attempts: int, error: str) -> None:
    if attempts < len(RETRY_DELAYS):
        c.execute(
            update(tasks)
            .where(tasks.c.id == task_id)
            .values(
                attempts=attempts + 1,
                next_attempt=datetime.datetime.now(datetime.UTC)
                + datetime.timedelta(seconds=RETRY_DELAYS[attempts]),
            )
        )
        return

    fail_task(c, task_id, error)


def prune_failed_tasks(c: Connection) -> None:
    ids = c.execute(
        select(tasks.c.id)
        .where(tasks.c.error.is_not(None))
        .order_by(tasks.c.id.desc())
        .offset(MAX_FAILED_TASKS)
    ).fetchall()

    if ids:
        c.execute(delete(tasks).where(tasks.c.id.in_([i[0] for i in ids])))
