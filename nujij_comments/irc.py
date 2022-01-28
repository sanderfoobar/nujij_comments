import asyncio

from nujij_comments.factory import IRC_BOT as bot
from nujij_comments.utils import wrap_message
import settings

COMMENT_COUNTER = 0
DUSHI_ENABLED = False
ODD_COLOR = "\x0304,01"
EVEN_COLOR = "\x0309,01"


@bot.on('CLIENT_CONNECT')
async def connect(*args, **kwargs):
    bot.send('NICK', nick=settings.IRC_NICK)
    bot.send('USER', user=settings.IRC_NICK, realname=settings.IRC_REALNAME)

    done, pending = await asyncio.wait(
        [bot.wait("RPL_ENDOFMOTD"), bot.wait("ERR_NOMOTD")],
        loop=bot.loop,
        return_when=asyncio.FIRST_COMPLETED)
    for future in pending:
        future.cancel()
    bot.send('JOIN', channel=settings.IRC_CHANNEL)


@bot.on('PRIVMSG')
async def message(nick, target, message, **kwargs):
    global DUSHI_ENABLED
    if nick == settings.IRC_NICK:
        return
    if target == settings.IRC_NICK:
        target = nick
    if not message.startswith(settings.IRC_COMMAND_PREFIX):
        return

    message = message[len(settings.IRC_COMMAND_PREFIX):]
    if message.startswith("dushi"):
        DUSHI_ENABLED = not DUSHI_ENABLED
        bot.send("PRIVMSG",
                 target=target,
                 message="Dushi ENABLED!!" if DUSHI_ENABLED else "Dushi DISABLED!!!")


@bot.on('PING')
async def keepalive(message, **kwargs):
    bot.send('PONG', message=message)


@bot.on('client_disconnect')
async def reconnect(**kwargs):
    from quart import current_app as app
    await asyncio.sleep(3)
    asyncio.create_task(bot.connect())
    app.logger.warning("Reconnecting to IRC server")


async def comment_monitor():
    global COMMENT_COUNTER, DUSHI_ENABLED
    from nujij_comments.factory import COMMENT_QUEUE
    async for comment in COMMENT_QUEUE.subscribe():
        blob = comment['dushi' if DUSHI_ENABLED else 'plain']
        author = blob['author']
        body = blob['body']

        color = [ODD_COLOR, EVEN_COLOR][COMMENT_COUNTER % 2 == 0]
        author = f"\x02{color}<{author}{color}>\x03\x02".strip()

        lines = await wrap_message(body)
        for line in lines:
            bot.send("PRIVMSG",
                     target=settings.IRC_CHANNEL,
                     message=f"{author} {line}")

        COMMENT_COUNTER += 1
