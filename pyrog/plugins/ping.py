from time import time
from pyrogram import Client, filters

from ..helper import _HANDLERS


_HAN = _HANDLERS + ["/"]


@Client.on_message(filters.command("ping", prefixes=_HAN))
@Client.on_edited_message(filters.command("ping", prefixes=_HAN))
async def pong(client, m):
    start = time()
    msg = await m.reply_text("`Pong!`", quote=True)
    end = round((time() - start) * 1000, 3)
    await msg.edit(f"**Pong !!** \n`{end} ms`")
