import os
import asyncio

from asyncio_multisubscriber_queue import MultisubscriberQueue
from quart import Quart
import bottom

import dushi
import settings

IRC_BOT = None
NUJIJ = None
dushi.load(os.path.join(settings.cwd, "dushi", "dushi.db"))
DUSHIFY = dushi.bezem
COMMENT_QUEUE = MultisubscriberQueue()
LOCAL_COMMENT_CACHE_MAX = 50
LOCAL_COMMENT_CACHE = []


async def _setup_irc(app: Quart):
    global IRC_BOT
    IRC_BOT = bottom.Client(
        host=settings.IRC_HOST,
        port=settings.IRC_PORT,
        ssl=settings.IRC_SSL,
        loop=asyncio.get_event_loop())
    from nujij_comments.irc import comment_monitor
    asyncio.create_task(IRC_BOT.connect())
    asyncio.create_task(comment_monitor())


async def _setup_web(app: Quart):
    import nujij_comments.routes


async def _setup_nujii(app: Quart):
    global NUJIJ
    from nujij_comments.nu import NuMonitor
    NUJIJ = NuMonitor()
    while True:
        await NUJIJ.start()
        await asyncio.sleep(5)


async def _setup_db_logger(app: Quart):
    async for comment in COMMENT_QUEUE.subscribe():
        blob = comment['plain']

        f = open(settings.PATH_DB, "a")
        f.write(f"{blob['body']}\n")
        f.close()


async def _setup_local_cache(app: Quart):
    async for comment in COMMENT_QUEUE.subscribe():
        LOCAL_COMMENT_CACHE.append(comment)
        if len(LOCAL_COMMENT_CACHE) > LOCAL_COMMENT_CACHE_MAX:
            LOCAL_COMMENT_CACHE.pop(0)


def create_app():
    global app
    app = Quart(__name__)

    @app.before_serving
    async def startup():
        if settings.IRC_ENABLED:
            await _setup_irc(app)

        if settings.NUJIJ_ENABLED:
            asyncio.create_task(_setup_nujii(app))

        asyncio.create_task(_setup_local_cache(app))
        asyncio.create_task(_setup_db_logger(app))
        await _setup_web(app)

    return app
