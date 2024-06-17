from discord.ext import commands
import random

command = {
    "name": "ask",
    "aliases": ["dicey", "8ball"],
    "description": "Find the answers to your most burning questions",
    "parameters": "[query]",
    "usages": ["ask Will I ever find true happiness?"],
}

responses = """
It is certain.
Without a doubt.
It is decidedly so.
Definitely.
You may rely on it.
As I see it, yes.
Most likely.
Outlook good.
Signs point to yes.
Absolutely!
Of course.
For sure.
Yes.
Obviously.
Yes, yes, yes!!!
ye
Indeed.
I personally guarantee it.
Affirmative, captain.
According to ChatGPT, yes.
I wouldn't count on it.
My reply is no.
My sources say no.
Outlook not so good.
Very doubtful.
Definitely not.
Certainly not.
No way.
No shot.
Of course not.
No.
Uhh, nah.
I'm leaning towards no.
The odds are not in your favor.
Unlikely.
Scientifically impossible.
Doubtful.
Ain't gonna happen.
Not in a million years.
According to ChatGPT, no.
How am I supposed to know?
I think you already know...
Do I look like a wizard to you?
Whether I tell you yes or no, all I truly reveal is which one you were hoping for.
You don't want to know, trust me.
SEEK NOT THE ANSWER, YOU KNOW NOT THE COST
Perhaps...
Perchance...
Have you gone outside today?
Would you quit asking these goofy questions and go touch some grass
You woke me up just to ask me... this?
""".split("\n")[1:-1]

class Ask(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def ask(self, ctx):
        await run(ctx)

async def run(ctx):
    await ctx.send(content=random.choice(responses))

async def setup(bot):
    await bot.add_cog(Ask(bot))