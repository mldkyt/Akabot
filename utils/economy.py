import datetime
from math import floor
from random import randint

from discord import ApplicationContext, User, ButtonStyle, Interaction
from discord.ui import View, button, Button
from sqlalchemy import select, insert, update, delete

from database import engine, economy_money, economy_work


def get_money(uid: int) -> tuple[int, int]:
    with engine.begin() as c:
        money = c.execute(
            select(economy_money.c.wallet, economy_money.c.bank)
            .where(economy_money.c.uid == str(uid))
        ).fetchone()

        if money is not None:
            return money[0], money[1]

    return 0, 1000


def update_money(uid: int, loc: str, amount: int):
    with engine.begin() as c:
        i = c.execute(
            select(economy_money)
            .where(economy_money.c.uid == str(uid))
        ).fetchone()

        if i is None:
            c.execute(
                insert(economy_money)
                .values(uid=str(uid))
            )

        if loc == "wallet":
            wallet = c.execute(
                select(economy_money.c.wallet)
                .where(economy_money.c.uid == str(uid))
            ).fetchone()

            if wallet is None:
                raise ValueError()

            c.execute(
                update(economy_money)
                .where(economy_money.c.uid == str(uid))
                .values(wallet=wallet[0] + amount)
            )

        elif loc == "bank":
            bank = c.execute(
                select(economy_money.c.bank)
                .where(economy_money.c.uid == str(uid))
            ).fetchone()

            if bank is None:
                raise ValueError()

            c.execute(
                update(economy_money)
                .where(economy_money.c.uid == str(uid))
                .values(bank=bank[0] + amount)
            )


async def work(ctx: ApplicationContext) -> tuple[bool, str]:
    # work and return if success and earned money or error message
    # Check expiry first
    with engine.begin() as c:
        c.execute(
            delete(economy_work)
            .where(economy_work.c.expires_at < datetime.datetime.now())
        )

        work_cooldown = c.execute(
            select(economy_work.c.expires_at)
            .where(economy_work.c.uid == str(ctx.author.id))
        ).fetchone()

        if work_cooldown is not None:
            expires_at = work_cooldown[0]
            time_left = expires_at - datetime.datetime.now()

            minutes = floor(time_left.total_seconds() // 60)

            return False, f"You are on work cooldown. Please wait {minutes} minutes before working again."

    # Work
    wage = randint(100, 1000)

    update_money(ctx.author.id, "wallet", wage)

    # Set worked
    with engine.begin() as c:
        c.execute(
            insert(economy_work)
            .values(uid=str(ctx.author.id), expires_at=datetime.datetime.now() + datetime.timedelta(hours=1))
        )

    return True, str(wage)


async def transfer(ctx: ApplicationContext, target: str, amount: int) -> tuple[bool, str]:
    # transfer money, return true if ok with amount, otherwise false with error message
    wallet, bank = get_money(ctx.author.id)

    if target == "wallet":
        # check if we have enough money in the bank to transfer TO wallet
        if amount > bank:
            return False, "Not enough money in the bank"

        update_money(ctx.author.id, "wallet", amount)
        update_money(ctx.author.id, "bank", -amount)

        return True, str(amount)

    elif target == "bank":
        if amount > wallet:
            return False, "Not enough money in the wallet"

        update_money(ctx.author.id, "bank", amount)
        update_money(ctx.author.id, "wallet", -amount)

        return True, str(amount)

    return False, "Invalid target"


async def rob(ctx: ApplicationContext, target: User) -> tuple[bool, str]:
    if ctx.author == target:
        return False, "Cannot rob yourself"

    target_wallet, target_bank = get_money(target.id)

    # 30% success rate
    # +10% chance on top of that to be caught by a police officer (idk)

    if randint(0, 100) < 70:
        wallet, bank = get_money(ctx.author.id)
        if wallet + bank > 300 and randint(0, 100) > 90:
            fine = randint(100, 300)

            update_money(ctx.author.id, "wallet", -min(fine, wallet))
            x = fine - min(fine, wallet)
            update_money(ctx.author.id, "bank", -x)

            return False, f"You failed to rob {target.mention}, and got fined {fine} NekoCoins :("

        return False, f"Unlucky you, you failed to rob {target.mention}. You didn't get caught so you didn't get fined"

    if target_wallet == 0:
        return False, "You tried to rob a person without any money in their wallet"

    # rob between 10 and 50% of money from user (EVIL if they leave their money in the wallet)

    percentage = randint(10, 50)
    stolen = int(target_wallet * (percentage / 100))

    update_money(ctx.author.id, "wallet", stolen)
    update_money(target.id, "wallet", -stolen)

    if stolen < 10:
        return False, "You tried to rob a person but it wasn't worth it"

    return True, str(stolen)


class PayConfirm(View):
    def __init__(self, target: User, amount: int):
        super().__init__()
        self.target = target
        self.amount = amount

    @button(label="Confirm", style=ButtonStyle.primary)
    async def confirm(self, _: Button, ctx: Interaction):
        update_money(ctx.user.id, "bank", -self.amount)
        update_money(self.target.id, "bank", self.amount)

        self.disable_all_items()
        await ctx.edit(view=self)
        await ctx.respond(f"You successfully paid {self.amount} NekoCoins to {self.target.mention}", ephemeral=True)

    @button(label="Cancel", style=ButtonStyle.secondary)
    async def cancel(self, _: Button, ctx: Interaction):
        self.disable_all_items()
        await ctx.edit(view=self)
        await ctx.respond("Canceled", ephemeral=True)


async def pay(ctx: ApplicationContext, target: User, amount: int) -> tuple[bool, str | None]:
    if target == ctx.author:
        return False, "Cannot pay yourself"

    source_wallet, source_bank = get_money(target.id)

    if amount > source_bank:
        return False, "Not enough money in your bank to send"

    await ctx.respond(f"Confirm payment of {amount} NekoCoins to {target.mention}?", view=PayConfirm(target, amount),
                      ephemeral=True)
    return True, None


class DoubleOrNothing(View):
    def __init__(self, amt: int):
        super().__init__()

        self.amt = amt
        self.cashed_out = False

    @button(label="Gamble!", style=ButtonStyle.primary)
    async def gamble(self, _: Button, ctx: Interaction):
        if randint(0, 100) < min(self.amt / 50, 50):
            self.amt = 0
            self.disable_all_items()
            await ctx.edit(content="oops you lost it all :(", view=None)
        else:
            self.amt = self.amt * 2
            await ctx.edit(content=f"Gambling with {self.amt} NekoCoins right now", view=self)

    @button(label="Cash out", style=ButtonStyle.secondary)
    async def cash_out(self, _: Button, ctx: Interaction):
        if self.cashed_out:
            return

        self.cashed_out = True
        self.disable_all_items()

        # the stake is debited when the game starts, so cashing out credits the
        # whole pot rather than the profit
        update_money(ctx.user.id, "bank", self.amt)
        await ctx.edit(content=f"Cashed out {self.amt} NekoCoins", view=None)


async def gamble(ctx: ApplicationContext, amount: int) -> tuple[bool, str | None]:
    wallet, bank = get_money(ctx.author.id)
    if amount > bank:
        return False, "Not enough money in the bank"

    update_money(ctx.author.id, "bank", -amount)

    await ctx.respond(f"Gambling with {amount} NekoCoins right now", view=DoubleOrNothing(amount))
    return True, None
