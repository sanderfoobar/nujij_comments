#!/usr/bin/python3
#
# Minimal example of how to get a stream of comments in the terminal.
# 1) Given an article_id, look up the asset_id (needed for websocket server)
# 2) Connect to websocket server @ /live
# 3) Monitor for comments (ignore comment replies)
#
# Needs `pip install aiohttp`

import asyncio
import sys
import os
import json

sys.path.append(os.path.dirname(os.path.realpath(__file__)))
user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36'


def print_usage():
    print(f"Usage: ./{sys.argv[0]} <article_id>")
    sys.exit(1)

try:
    import aiohttp
except:
    print("requires: pip install aiohttp")
    sys.exit(1)

from utils import asset_id_query, comment_added_query


async def main(article_id: int):
    timeout = aiohttp.ClientTimeout(total=5)
    ses = aiohttp.ClientSession(headers={
        'User-Agent': user_agent,
        'Origin': 'https://nu.nl'
    }, timeout=timeout)

    # get the asset_id

    data = {
        "query": asset_id_query.decode(),
        "operationName": "CoralEmbedStream_Embed",
        "variables": {
            "assetId": "",
            "assetUrl": f"https://www.nu.nl/artikel/{article_id}/redirect.html",
            "commentId": "",
            "hasComment": False,
            "excludeIgnored": False,
            "sortBy": "CREATED_AT",
            "sortOrder": "DESC"
        }
    }

    async with ses.post('https://talk.nu.nl/api/v1/graph/ql', json=data) as resp:
        resp.raise_for_status()
        blob = await resp.json()
        asset_id = blob['data']['asset']['id']
        print(f"got asset_id: {asset_id}")

    await ses.close()

    # contact websocket server

    timeout = aiohttp.ClientTimeout(total=5)
    ses = aiohttp.ClientSession(headers={
        'User-Agent': user_agent,
        'Origin': 'https://talk.nu.nl',
        'Connection': 'Upgrade',
        'Sec-WebSocket-Version': '13',
        'Sec-WebSocket-Protocol': 'graphql-ws'
    }, timeout=timeout)

    print('connecting to websocket server')
    ws = await ses.ws_connect('wss://talk.nu.nl/api/v1/live')
    await ws.send_json({"type": "connection_init", "payload": {"token": None}})

    await ws.send_json({"id": 1, "type": "start", "payload": {
        "query": comment_added_query.decode(),
        "variables": {"assetId": asset_id}, "operationName": "CommentAdded"}})

    print('connected, monitoring comments')

    while True:
        msg = await ws.receive()

        if msg.type in [aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED]:
            print("disconnected")
            break
        elif msg.type == aiohttp.WSMsgType.TEXT:
            try:
                blob = json.loads(msg.data)
                comment = blob['payload']['data']['commentAdded']
                if comment['parent']:
                    continue  # ignore replies
                username = comment['user']['username']
                body = comment['body'].replace("\n", "")
                print(f"<{username}> {body}")
            except:
                pass


if __name__ == '__main__':
    if len(sys.argv) <= 1 or not sys.argv[1].isdigit():
        print_usage()

    article_id = int(sys.argv[1])
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(article_id))
