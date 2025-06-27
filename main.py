import discord
import settings
from settings import utils
from discord.ext import commands
import pretty_help
from cogs.tickets import CreateButton, CloseButton, TrashButton


bot = commands.Bot(
    command_prefix=settings.COMMAND_PREFIX, 
    intents=settings.INTENTS,
    help_command=pretty_help.PrettyHelp(typing=False),
    status=settings.STATUS
)

@bot.event
async def on_ready():
    await utils.init_ticket_db()
    await utils.init_economy_db()
    await utils.init_moderation_db()
    await bot.load_extension("cogs.tickets")
    await bot.load_extension("cogs.economy")
    await bot.load_extension("cogs.moderation")
    await bot.load_extension("cogs.owner")
    bot.add_view(CreateButton(bot))
    bot.add_view(CloseButton(bot))
    bot.add_view(TrashButton())
    await bot.change_presence(activity=discord.CustomActivity(name='Type "/tickets open" for support'))
    print(f"logged in as {bot.user} ({bot.user.id})")
    print('------')

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.reply(error)

if __name__ == "__main__":
    bot.run(settings.TOKEN)
