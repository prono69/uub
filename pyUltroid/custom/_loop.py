import asyncio

try:
    import uvloop

    uvloop.install()
except ImportError:
    print


try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
