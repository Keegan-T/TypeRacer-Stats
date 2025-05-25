from config import bot_owner, bot_admins, supporters
from database.bot.banned import get_banned


def ban_check(ctx):
    if ctx.author.id == bot_owner: return True
    return str(ctx.author.id) not in get_banned()


def owner_check(ctx):
    return ctx.author.id == bot_owner


def admin_check(ctx):
    return ctx.author.id in bot_admins


def echo_check(ctx):
    return ctx.author.id in bot_admins + supporters
