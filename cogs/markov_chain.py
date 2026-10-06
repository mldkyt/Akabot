import markovify
from discord import Bot, Cog, Message, slash_command, ApplicationContext
from discord.ext.commands import cooldown, BucketType
from sqlalchemy import select

from database import engine, markov
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

    @slash_command()
    @cooldown(1, 600, BucketType.channel)
    async def markov(self, ctx: ApplicationContext):
        """Run the markov module. Generates random text from this channel when enabled."""
        with engine.begin() as c:
            markov_data = c.execute(
                select(markov.c.mode)
                .where(markov.c.channel_id == str(ctx.channel.id))
            ).fetchone()

            if markov_data is None:
                await ctx.respond("Markov module is disabled", ephemeral=True)
                return

            if markov_data[0] != "command":
                await ctx.respond("The method of posting markov text is not set to command only", ephemeral=True)
                return

            await ctx.defer()

            history = await ctx.channel.history(limit=500).flatten()
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
                await ctx.respond(output)
            else:
                await ctx.respond("Markov couldn't be generated", ephemeral=True)


def setup(bot: Bot):
    if bot.intents.message_content:
        bot.add_cog(MarkovChain(bot))
