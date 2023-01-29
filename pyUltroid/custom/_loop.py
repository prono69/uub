import asyncio
import secrets

try:
    import uvloop

    uvloop.install()
except ImportError:
    pass


tasks_db = {}


try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)


def run_async_task(func, id=None, *args, **kwargs):
    while not id or id in tasks_db:
        id = secrets.token_hex(nbytes=10)
    task = loop.create_task(func(*args, **kwargs))
    tasks_db[id] = task
    task.add_done_callback(lambda task: tasks_db.pop(id))
    return id
