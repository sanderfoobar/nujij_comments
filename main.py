from typing import Optional, Union, List, Dict, Any
import random
import asyncio
import re
import json
import gzip
from functools import wraps

import aiohttp
import bottom

irc_nick = 'nujij'
irc_host = ''
irc_channel = '#nujij'
irc_port = 6667

re_nu = r"https:\/\/www.nu.nl\/[\W+-+]+\/(\d+)\/"
new_comments = asyncio.Queue()
ldup = lambda x: list(dict.fromkeys(x))
comment_counter = 0
odd_color = "\x0304,01"
even_color = "\x0309,01"


# yolo
comment_added_query = gzip.decompress(bytes.fromhex(
    "1f8b0800000000000003bd574d6fe23010bdf32bbc520f5da9ea656fbd51da9590b65555dab36592815a4d6cd61f5251c57f5f3b38c1716"
    "c1368b5488013deccbcf18cdf04a997b21074a3286768c6eb1a989a9625949717444a50f3f206cdef7e5ca10bf8282a5dc27ccdb80073f7"
    "96f30a08fb893e270815be656388a9c1b43ef6208436441894bb4088966e81b1da6e80911a9a1bbbe6f3fafa7ac605a9eeeb25940b2580d"
    "4d87db9709381ed6eb29b4c5682acedcfe888393aa4dc506ae84845949666a12508c7d4f10c22c5193a871e45cf2c4b2eb00cd9e5822d28"
    "5b5730eb420ad85414e4e55f0d627b833e2b5a5375837e5da1b08a4159776da5182f4176853a25b67d7d3dfe90c3393cbe8f4b9ccfb99c2"
    "23ddfbe76bdab37221fe1433d91751f65ba54a89916928bde7d6065e46e34941f280238fc1ce3108b3f8c3d70db3a8d9ef7304e18a3ef7f"
    "70184f3d66bdda44a560c9cbadd53663a6a0c444f9f260db6a3be3baa9ab22ebb631ccb26b112ff368c6831c869a63ef745603fc9e0d7ea"
    "35271b16d19184c1c4e0a2bf358eaba268276bd1c702b5c5266a585d56becd1ca8bb67d434995d95a87b75750764bb2ace095295a2505f5"
    "8554ef8b8aabb64e73b6e2b744787a1a014d9bc4641ef40c640c6caad51b178f86d418dc8ba97c1e37e34cf5078203f94d7927c84a4dcdf"
    "27458a2ef8f9a862d9ff193a947644a598b07239582d8dd4e96e6b73955dac8acb396d86ce5b8b492cebf3cd0bfeb1c67c8e7d20ef9ff07"
    "3a99539428ed13889a5494bde35bad94919351354b59454b3692efe04047183f83dc40a1c6528dc2a31cc769a96160ad9ddbfd062f1a936"
    "d57ce83de2614d7d3dcd366ea29b51fa85ea2fc7be003308da34a99899735cdc891cbdfdb93fc54f445f810d30a574aaa0fa850ae8eef99"
    "3f01127b76ffb101a1fe902554d85f8f13f1bc7118d2db254f3efa02d29390531fd3ce5597600ea6d4a5d26bca92a333a73019cb30987bb"
    "23bc63cd13ca9990766dc0af3585900f6d6d674e45c3bee2053edde99e83db39e51b3e48148e4beffcbf46a28e0c3726f3a2ef7110e32b9"
    "67fea0279d9b1659513394bec831e6e638d3bc80f539fc03c0e8ce21a3110000"))
asset_id_query = gzip.decompress(bytes.fromhex(
    "1f8b0800000000000003ed5add4fe338107fe7af08ab7b0009f1726f7d5a2845425a3eae2d279d4ea7c84d4cb1c847b11d2dbd15fffbd98"
    "e9338893d715258edc321a1a6cecc783c9ef9cd07bc1698ee83794e51b24837385e718a511aaae793df106398dfc4b3e0e6ea2c28bf3dd2"
    "6416082a926dc55294a729ce34c9b15878466c5eaecd82cb3c4f30cae4327e8b9222c637db2ca738ae5f89372ca7fc722f44de2fd7e1fcf"
    "ef67671b75e85977f1deb77f734c654bfbe5f5e2d96c7a7c18fa32048b1fa080212ab0fc611af96ca6f05abbf0641c130cd508a8da58aca"
    "580843bedf6149572fbed74f1b9465383e40004abea33d7ba038cd0f11c30a26de3192672d2145c649e22ba3f7b27ad579512eb716e592f"
    "28413222eb27291b3a0908e51fbc8a9d6edfcfcbce75cf33c7b22db82e250513be9f4074c7451f03c459c4417926c9ee4ac2db8a73bb013"
    "cd73eea068745644ef47474f146da59ff783c79016884b5a8acf3f5498b5fcf67f87fd3c872525ce3c0a1b3636d540e160a10290ec0e233"
    "c890bb4ab04e5748b32f2af70b93cbbab64d8bc6c8d9297559273ed0f6bb47940196686977528ae49c23185bd50416b4562ec0a3aa4c906"
    "78e404ab81e7d6dbde644ff925a2b6736b0a11c3cf3995c6ec109987b8a2e8895f88c731340e0bc17c7d13f91ada442c2945619292a0136"
    "5899975d63c0dbe924c65c613f23433b327849ffa434b51643b44a542d5a5015c4cb87282e7066f8f7b34bf45c204199f9bb2941f73c255"
    "948b5c2597984c1758be88845e1cc721e2fd8017e087a90af7324aa43be76f8b0c6d3462e8159122787d1f0a33bf91ec851984af0566524"
    "e9bdd58354518cb3791de3b52faae498af3821b2bb79831b42dc5c58449d1dabae21cf65593257a46749e0b3c36b4aad74a74c4af05a178"
    "912292a85448d3c6223d5bf39ca3446fa564045fd90bd9f57cbc890b76f22a836d16fc48484a44edf8fb59d0ad193b45e4596094874da95"
    "82ecb8a529796efa78eddf5f566e27a994fe4442d7fb57a9d907e87dff84365589127299f175468a2bee32c36bef9250d997f05555cd734"
    "406a7193e8dc621038b344453336bb5850af75421581407eb0295f2588483a9bfd7c9a6489d1309191684a2a1f34d7f72e4fa6c5a8b3a9e"
    "3d485902cd7da0d8957e159d9aef1adb1567768076db6eac0aff0af84e00921f8ee1f43aebd4b703974ffbe0e53f4f8385decfa4cd5c902"
    "37d5cf7beb5b177eaa9f2e0c553f6d3802b7323702d3b44d07dbfefdbdc725f803a1766c98b5eec60a059b3cdef72a890a1ea45bedab74c"
    "a515d5b88c7da458c93fb95347dcca99a463b7da94df84c18cf75612b34103476f2124f4356a429a2a4f6e58e6e515d23440595456068a8"
    "05b70ff217c74456239a5e7ec371fd288b91c7ba4b1cd36b34780a641390a8c927b0ac26a378d0adc5cdc374ba02ec13d9db95d164a31b2"
    "2477e19d911b1c1f0f9a84cda0551ff4037073c600be8a81275d7e033203249a7779b9d391a507a5907679274a5ac2ea3062c0d6b853daa"
    "26abdcb66eea5ecbcee5426e693462de7ed5d2c8221e6ee226f6677523e6e8d926a719608a099b0e8867d7eca9ef701a3bae45e612dbc63"
    "a7858a8d93c862920eb70305945b4865d831bc2332edb86d0040ab0a531a5735af24f82bf0be7bbdf9519a4f375d89cc3fcdea8014de39c"
    "fadfd6d152e5ca619ded3cd0b8d181ee9e07e95c99f32c25dd2dce8ab03f6704f672f38d70af4648cb9070a8b63bfe76fc03a13ad4b8c37"
    "ced6d9e3a74aa749df5073b27b2969d057f7fb95e5cac1f978bab2fffb8c62de3c16adcf115dc4c3441c36b41dbae2d66fda155df0abed3"
    "a9e1bef22c8831de09dbd3028f1d658148f9d3e6594e0da6dcd6c0dcc3d98afd121dd8afdc674cb9048fbaf3e3e774c064d30a167032f5f"
    "0410f014e1bf8a462b7eafd9ceaa1ae83c9826cbe99d62d46ebf980698a12514d879705e779e6a3a69da72dbefc3b8da79a1dcfea29bac4"
    "6c8723eea7a185f8000376dcd96a437bbde1614880f120b7744f96ed5ed6c31b4ba6ddfa018e53f8c1a3838f42fe7105c6d6a5ff4f50079"
    "87c39aeb617995e77e6e2b25ed9e890766bdc8ed44155ade4561dfde69f4203d50f94624b03af14cbbebece6646ea98921a73d27173f069"
    "fd127cfd763cf1f20190151821eaf31b36f1afa39a3d2570b9ca9e7e2356d10ddbccaca61c365bbced30e5dfd00627a1f9ec37788599bb5"
    "b1a5632e0a30d202d0839f87f273c3dac5353bad02529b6249b5286429cddcd740b30a4b9bd3f77ce12ca9e4cfe8354d83c969c1e138521"
    "ee4f98953882c395d371bac17445b20887c6b31ae3fae5ed61018037b762bed5bc1d7472bfa4075d8ed7d93d04006707fed4e1146efe23c"
    "e013adac40c6b0a03744b87ff00a72a06e9642e0000"))


def safu(func):
    # safety first guiz
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except:
            pass
    return wrapper


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
        global comment_counter

        color = [odd_color, even_color][comment_counter % 2 == 0]
        author = f"""
        \x02{color}<{author}{color}>\x03\x02
        """.strip()

        wrapped = await self.wrap_message(message)
        if not wrapped:
            return

        for wrapped_message in wrapped:
            self.bot.send("PRIVMSG", target=self.channel, message=f"{author} {wrapped_message}")

        comment_counter += 1

    async def comment_monitor(self):
        while True:
            author, comment = await new_comments.get()
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
        await asyncio.sleep(3600)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
