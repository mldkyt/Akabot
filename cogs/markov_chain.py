import markovify
from discord import Bot, Cog, Message

from database import engine
from utils.markov import tick_markov, should_trigger_markov, post_markov_run


class MarkovChain(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @Cog.listener()
    async def on_message(self, message: Message):
        if message.author.bot:
            return

        with engine.begin() as c:

            tick_markov(c, message)

            if should_trigger_markov(c, message):
                print("running markov")

                history = await message.channel.history(limit=500).flatten()
                history = [msg for msg in history if not msg.author.bot]

                text = "\n".join([msg.content for msg in history])
                model = markovify.NewlineText(text)
                model.compile(inplace=True)

                print("markov size", len(text))

                output = None
                for _ in range(10000):
                    output = model.make_sentence()
                    if output is not None:
                        break

                if output is not None:
                    await message.channel.send(output)

                    post_markov_run(c, message)
                else:
                    print("run failed")


def setup(bot: Bot):
    if bot.intents.message_content:
        bot.add_cog(MarkovChain(bot))
