import datetime

import markovify
from discord import Bot, Cog, Message
from sqlalchemy import select, update

from database import engine, markov


class MarkovChain(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @Cog.listener()
    async def on_message(self, message: Message):
        if message.author.bot:
            return

        with engine.begin() as c:
            row = c.execute(
                select(markov.c.period, markov.c.period_num).where(
                    (markov.c.channel_id == str(message.channel.id))
                    & (
                        (markov.c.next_send < datetime.datetime.now())
                        | (markov.c.next_send == None)
                    )
                )
            ).fetchone()

            if not row:
                return

            history = await message.channel.history(limit=500).flatten()
            history = [msg for msg in history if not msg.author.bot]

            text = "\n".join([msg.content for msg in history])
            model = markovify.NewlineText(text)
            model.compile(inplace=True)

            output = None
            for _ in range(10000):
                output = model.make_sentence()
                if output is not None:
                    break

            if output is not None:
                await message.channel.send(output)

            period, period_num = row
            if period == "minutely":
                next_send = datetime.datetime.now() + datetime.timedelta(
                    minutes=period_num
                )
            elif period == "hourly":
                next_send = datetime.datetime.now() + datetime.timedelta(
                    hours=period_num
                )
            elif period == "daily":
                next_send = datetime.datetime.now() + datetime.timedelta(
                    days=period_num
                )
            else:
                next_send = datetime.datetime.now() + datetime.timedelta(days=1)

            c.execute(
                update(markov)
                .where(markov.c.channel_id == str(message.channel.id))
                .values(next_send=next_send)
            )


def setup(bot: Bot):
    bot.add_cog(MarkovChain(bot))
