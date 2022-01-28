import asyncio
import json
import time
from datetime import datetime
from functools import wraps

from quart import websocket, render_template, abort
from quart import current_app as app

import settings

a = 0


@app.route('/test')
async def test():
    global a
    from nujij_comments.factory import COMMENT_QUEUE
    await COMMENT_QUEUE.put({"dushi": {'author': 'noob', 'body': 'hello there' + str(a)}, "plain": {'author': 'noob', 'body': 'fakka G' + str(a)}})
    a += 1
    return "ok"


@app.route("/")
async def root():
    return await render_template('index.html')


@app.websocket('/ws')
async def ws():
    from nujij_comments.factory import COMMENT_QUEUE, LOCAL_COMMENT_CACHE
    for comment in LOCAL_COMMENT_CACHE:
        await websocket.send_json(comment)

    async for comment in COMMENT_QUEUE.subscribe():
        await websocket.send_json(comment)

    print('disconnected')
