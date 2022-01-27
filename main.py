from typing import Optional, Union, List, Dict, Any
import random
import asyncio
import re
import json
import gzip
from functools import wraps

import aiohttp
import bottom

from utils import asset_id_query, comment_added_query, safu

irc_nick = 'nujij'
irc_host = ''
irc_channel = '#nujij'
irc_port = 6667

fn_database = "comments.db"
re_nu = r"https:\/\/www.nu.nl\/[\W+-+]+\/(\d+)\/"
new_comments = asyncio.Queue()
ldup = lambda x: list(dict.fromkeys(x))


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
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36',
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

    async def _destroy_client(self):
        try:
            await self._ses.close()
        except Exception as ex:
            pass
        self._ses = None
        self._timeout = None


class CommentMonitor(HttpClient):
    def __init__(self):
        super(CommentMonitor, self).__init__()
        self._headers['Origin'] = 'https://talk.nu.nl'
        self._headers['Connection'] = 'Upgrade'
        self._headers['Sec-WebSocket-Version'] = '13'
        self._headers['Sec-WebSocket-Protocol'] = 'graphql-ws'
        self._asset_ids = {}  # article_id: asset_id

    async def start(self):
        await super()._setup_client()

        ws = await self._ses.ws_connect(self.ws)
        await ws.send_json({"type": "connection_init", "payload": {"token": None}})

        for i, (article_id, asset_id) in enumerate(self._asset_ids.items()):
            await ws.send_json({"id": i + 1, "type": "start", "payload": {
                "query": comment_added_query.decode(),
                "variables": {"assetId": asset_id}, "operationName": "CommentAdded"}})

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
                    await new_comments.put((username, body))
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


class IRCBoat:
    def __init__(self, host: str, port: int, nick: str, channel: str):
        self.host: str = host
        self.port: int = port
        self.nick: str = nick
        self.channel: str = channel
        self.bot = None
        self._comment_counter = 0

    async def _setup_client(self):
        self.bot = bottom.Client(host=self.host, port=self.port, ssl=False, loop=asyncio.get_event_loop())

    async def start(self):
        await self._setup_client()

        @self.bot.on('CLIENT_CONNECT')
        async def connect(*args, **kwargs):
            self.bot.send('NICK', nick=self.nick)
            self.bot.send('USER', user=self.nick, realname=self.nick)

            done, pending = await asyncio.wait(
                [self.bot.wait("RPL_ENDOFMOTD"), self.bot.wait("ERR_NOMOTD")],
                loop=self.bot.loop,
                return_when=asyncio.FIRST_COMPLETED
            )
            for future in pending:
                future.cancel()
            self.bot.send('JOIN', channel=self.channel)
            await asyncio.sleep(2)

        @self.bot.on('PING')
        async def keepalive(message, **kwargs):
            self.bot.send('PONG', message=message)

        @self.bot.on('client_disconnect')
        async def reconnect(**kwargs):
            await asyncio.sleep(3)
            asyncio.create_task(self.bot.connect())

        asyncio.create_task(self.bot.connect())
        asyncio.create_task(self.comment_monitor())

    @safu
    async def wrap_message(self, message) -> List[str]:
        spl = []
        max_segment = 400
        while True:
            if len(message) >= max_segment:
                _continue = False
                for _ in ['.', ' ']:
                    try:
                        c = message.index(_, max_segment - 60, max_segment + 60) + 1
                        spl.append(message[:c].strip())
                        message = message[c:]
                        _continue = True
                        break
                    except Exception as ex:
                        pass
                if _continue:
                    continue
                raise Exception("whatever")
            else:
                if message:
                    spl.append(message.strip())
                break
        return [s for s in spl if s]

    @safu
    async def send_comment(self, author, message):
        odd_color = "\x0304,01"
        even_color = "\x0309,01"

        color = [odd_color, even_color][self._comment_counter % 2 == 0]
        author = f"""
        \x02{color}<{author}{color}>\x03\x02
        """.strip()

        wrapped = await self.wrap_message(message)
        if not wrapped:
            return

        for wrapped_message in wrapped:
            self.bot.send("PRIVMSG", target=self.channel, message=f"{author} {wrapped_message}")

        self._comment_counter += 1

    async def comment_monitor(self):
        while True:
            author, comment = await new_comments.get()

            f = open(fn_database, "a")
            f.write(f"{comment}\n")
            f.close()

            await self.send_comment(author, comment)


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
        asyncio.create_task(self._ws.start())

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
                return ldup(re.findall(re_nu, data))[:self._article_limit]


async def main():
    monitor = NuMonitor()
    irc = IRCBoat(host=irc_host, port=irc_port, nick=irc_nick, channel=irc_channel)

    await irc.start()

    while True:
        await monitor.start()
        await asyncio.sleep(1200)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
