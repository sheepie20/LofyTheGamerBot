from discord.ext import commands
import discord

class Owner(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot

    @commands.hybrid_command(name="sync-tree", description="Sync application commands.")
    @commands.is_owner()
    async def sync_tree(self, ctx: commands.Context) -> None:
        self.bot.tree.copy_global_to(guild=ctx.guild)
        await self.bot.tree.sync()
        print("Tree loaded successfully")
        await ctx.send("✅ Command tree synced.")

    @commands.hybrid_command(name="load", description="Load a cog.")
    @commands.is_owner()
    async def load_cog(self, ctx: commands.Context, cog: str):
        try:
            await self.bot.load_extension(f"cogs.{cog}")
            await ctx.send(f"✅ Loaded cog: `{cog}`")
        except Exception as e:
            await ctx.send(f"❌ Failed to load cog `{cog}`: `{e}`")

    @commands.hybrid_command(name="unload", description="Unload a cog.")
    @commands.is_owner()
    async def unload_cog(self, ctx: commands.Context, cog: str):
        try:
            await self.bot.unload_extension(f"cogs.{cog}")
            await ctx.send(f"✅ Unloaded cog: `{cog}`")
        except Exception as e:
            await ctx.send(f"❌ Failed to unload cog `{cog}`: `{e}`")

    @commands.hybrid_command(name="reload", description="Reload a cog.")
    @commands.is_owner()
    async def reload_cog(self, ctx: commands.Context, cog: str):
        try:
            await self.bot.reload_extension(f"cogs.{cog}")
            await ctx.send(f"🔄 Reloaded cog: `{cog}`")
        except Exception as e:
            await ctx.send(f"❌ Failed to reload cog `{cog}`: `{e}`")

async def setup(bot: commands.Bot):
    await bot.add_cog(Owner(bot))
