import re
from typing import Optional, Union, List, Dict, Any
import asyncio
import json

import aiohttp

from nujij_comments.utils import comment_added_query, asset_id_query, safu, ldup

USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36'
RE_NU = r"https:\/\/www.nu.nl\/[\W+-+]+\/(\d+)\/"


class HttpClient(object):
    def __init__(self):
        self.ql = "https://talk.nu.nl/api/v1/graph/ql"
        self.ws = 'wss://talk.nu.nl/api/v1/live'
        self._max_concurrency = 15
        self._semaphore = asyncio.Semaphore(self._max_concurrency)
        self._headers = {
            'Pragma': 'no-cache',
            'Origin': 'https://nu.nl',
            'Accept-Language': 'en-US,en;q=0.9',
            'User-Agent': USER_AGENT,
            'Cache-Control': 'no-cache',
            'Connection': 'Upgrade',
        }
        self._timeout: Optional[aiohttp.ClientTimeout] = None
        self._ses: Optional[aiohttp.ClientSession] = None

    async def _setup_client(self):
        self._timeout = aiohttp.ClientTimeout(total=5)
        self._ses = aiohttp.ClientSession(
            headers=self._headers,
            timeout=self._timeout)

    @safu
    async def _destroy_client(self):
        self._timeout = None
        await self._ses.close()


class NuMonitor(HttpClient):
    def __init__(self):
        super(NuMonitor, self).__init__()
        self._ws = CommentMonitor()
        self.feeds = [
            "https://www.nu.nl/rss/Algemeen",
            "https://www.nu.nl/rss/Economie",
            "https://www.nu.nl/rss/Sport",
            "https://www.nu.nl/rss/Achterklap",
            "https://www.nu.nl/rss/Opmerkelijk",
            "https://www.nu.nl/rss/Wetenschap",
            "https://www.nu.nl/rss/Tech",
            "https://www.nu.nl/rss/Gezondheid"
        ]
        self._article_limit = 10  # most recent articles per feed

    async def start(self):
        """Fetch latest articles and pass them to CommentMonitor"""
        await self._ws.destroy()
        await super()._destroy_client()
        await super()._setup_client()

        print('fetching new articles')
        article_ids = await self.article_ids()
        if not article_ids:
            return

        asset_ids = await asyncio.gather(
            *[self._fetch_asset_id(article_id=a_id) for a_id in article_ids]
        )

        for i, a_id in enumerate(article_ids):
            val = asset_ids[i]
            if isinstance(val, str):
                self._ws[a_id] = val

        print(f"{len(self._ws)} articles found")
        await self._ws.start()

    @safu
    async def article_ids(self):
        article_ids = await asyncio.gather(
            *[self._fetch_article_ids(rss_feed=url) for url in self.feeds]
        )
        return ldup(int(url) for inner in article_ids if inner for url in inner if url.isdigit())

    @safu
    async def _fetch_asset_id(self, article_id: int) -> Optional[int]:
        async with self._semaphore:
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

            async with self._ses.post(self.ql, json=data) as resp:
                blob: dict = await resp.json()
                return blob['data']['asset']['id']

    @safu
    async def _fetch_article_ids(self, rss_feed) -> Optional[List[str]]:
        async with self._semaphore:
            async with self._ses.get(rss_feed) as resp:
                data = await resp.text()
                return ldup(re.findall(RE_NU, data))[:self._article_limit]


class CommentMonitor(HttpClient):
    def __init__(self):
        super(CommentMonitor, self).__init__()
        self._headers['Origin'] = 'https://talk.nu.nl'
        self._headers['Connection'] = 'Upgrade'
        self._headers['Sec-WebSocket-Version'] = '13'
        self._headers['Sec-WebSocket-Protocol'] = 'graphql-ws'
        self._asset_ids = {}  # article_id: asset_id
        self._timer = 0
        self._timer_max = 60 * 15  # reconnect every 15min
        asyncio.create_task(self.killtimer())

    async def killtimer(self):
        while True:
            self._timer += 1
            if self._timer > self._timer_max:
                self._timer = 0
                await self.destroy()
            await asyncio.sleep(1)

    async def start(self):
        from nujij_comments.factory import DUSHIFY, COMMENT_QUEUE
        await super()._setup_client()

        print("ws connecting to NU talk")
        ws = await self._ses.ws_connect(self.ws)
        await ws.send_json({"type": "connection_init", "payload": {"token": None}})

        for i, (article_id, asset_id) in enumerate(self._asset_ids.items()):
            await ws.send_json({"id": i + 1, "type": "start", "payload": {
                "query": comment_added_query.decode(),
                "variables": {"assetId": asset_id}, "operationName": "CommentAdded"}})

        while True:
            msg = await ws.receive()

            if msg.type in [aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED]:
                print("ws disconnected")
                self._timer = 0
                break
            elif msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    blob = json.loads(msg.data)
                    comment = blob['payload']['data']['commentAdded']
                    if comment['parent']:
                        continue  # ignore replies

                    username = comment['user']['username']
                    body = comment['body']

                    # sad attempt at normalization
                    body = body.replace("\n\n", " ")
                    body = body.replace("\n \n", " ")
                    body = body.replace("\n", " ")
                    body = body.replace("  ", " ")

                    dushified = DUSHIFY(body)
                    await COMMENT_QUEUE.put({
                        'plain': {'author': username, 'body': body},
                        'dushi': {'author': username, 'body': dushified}
                    })
                except:
                    pass

    async def destroy(self):
        await super()._destroy_client()
        self._asset_ids = {}
        await asyncio.sleep(2)

    def __len__(self):
        return len(self._asset_ids.keys())

    def __setitem__(self, key, value):
        self._asset_ids[key] = value
