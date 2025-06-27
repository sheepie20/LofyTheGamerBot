import discord
from discord.ext import commands, tasks
import aiosqlite
from datetime import datetime, timedelta, timezone

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "moderation.db"
        self.bot.loop.create_task(self.initialize_db())
        self.check_mutes.start()

    async def initialize_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            # Table to track timed mutes
            await db.execute("""
                CREATE TABLE IF NOT EXISTS mutes (
                    guild_id INTEGER,
                    user_id INTEGER,
                    unmute_at TEXT,
                    PRIMARY KEY(guild_id, user_id)
                )
            """)
            # Table to log mod actions
            await db.execute("""
                CREATE TABLE IF NOT EXISTS mod_actions (
                    action_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER,
                    user_id INTEGER,
                    moderator_id INTEGER,
                    action TEXT,
                    reason TEXT,
                    timestamp TEXT
                )
            """)
            await db.commit()

    async def log_action(self, guild_id, user_id, moderator_id, action, reason):
        timestamp = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO mod_actions (guild_id, user_id, moderator_id, action, reason, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (guild_id, user_id, moderator_id, action, reason, timestamp)
            )
            await db.commit()

    def _validate_reason(self, reason: str):
        if not reason or reason.strip() == "":
            return False
        return True

    @commands.hybrid_command(name="purge", description="Delete a number of messages. Reason required.")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int, *, reason: str):
        if amount < 1 or amount > 100:
            return await ctx.send("Please specify an amount between 1 and 100.")
        if not self._validate_reason(reason):
            return await ctx.send("You must provide a valid reason for purging messages.")
        
        deleted = await ctx.channel.purge(limit=amount + 1)  # Include command message
        await ctx.send(f"🧹 Deleted {len(deleted)-1} messages.", delete_after=5)
        
        await self.log_action(ctx.guild.id, None, ctx.author.id, "purge", reason)

    @commands.hybrid_command(name="kick", description="Kick a user from the server. Reason required.")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str):
        if not self._validate_reason(reason):
            return await ctx.send("You must provide a valid reason for kicking.")
        try:
            await member.kick(reason=reason)
            await ctx.send(f"👢 Kicked {member.mention}. Reason: {reason}")
            await self.log_action(ctx.guild.id, member.id, ctx.author.id, "kick", reason)
        except Exception as e:
            await ctx.send(f"❌ Failed to kick: {e}")

    @commands.hybrid_command(name="ban", description="Ban a user from the server. Reason required.")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason: str):
        if not self._validate_reason(reason):
            return await ctx.send("You must provide a valid reason for banning.")
        try:
            await member.ban(reason=reason)
            await ctx.send(f"🔨 Banned {member.mention}. Reason: {reason}")
            await self.log_action(ctx.guild.id, member.id, ctx.author.id, "ban", reason)
        except Exception as e:
            await ctx.send(f"❌ Failed to ban: {e}")

    @commands.hybrid_command(name="unban", description="Unban a user from the server. Reason required.")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user: discord.User, *, reason: str):
        if not self._validate_reason(reason):
            return await ctx.send("You must provide a valid reason for unbanning.")
        try:
            await ctx.guild.unban(user, reason=reason)
            await ctx.send(f"✅ Unbanned {user}. Reason: {reason}")
            await self.log_action(ctx.guild.id, user.id, ctx.author.id, "unban", reason)
        except Exception as e:
            await ctx.send(f"❌ Failed to unban: {e}")

    @commands.hybrid_command(name="banlist", description="List all banned users in the server.")
    async def banlist(self, ctx: commands.Context):
        await ctx.defer()
        bans = [entry async for entry in ctx.guild.bans(limit=2000)]
        banned_users = "\n".join([f"{ban.user.name} (ID: {ban.user.id})" for ban in bans])
        embed = discord.Embed(title="Banned Users", description=banned_users, color=0xFF0000)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="mute", description="Mute a user. Reason required.")
    @commands.has_permissions(manage_roles=True)
    async def mute(self, ctx, member: discord.Member, duration: int = 0, unit: str = "m", *, reason: str):
        if not self._validate_reason(reason):
            return await ctx.send("You must provide a valid reason for muting.")
        guild = ctx.guild
        muted_role = discord.utils.get(guild.roles, name="Muted")
        if muted_role is None:
            muted_role = await guild.create_role(name="Muted", reason="Needed for muting")
            for channel in guild.channels:
                try:
                    await channel.set_permissions(muted_role, speak=False, send_messages=False, add_reactions=False)
                except Exception:
                    pass

        if muted_role in member.roles:
            return await ctx.send(f"{member.mention} is already muted.")

        await member.add_roles(muted_role, reason=reason)

        unmute_at = None
        if duration > 0:
            units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
            seconds = duration * units.get(unit.lower(), 60)
            unmute_at = datetime.utcnow() + timedelta(seconds=seconds)
            unmute_at_str = unmute_at.isoformat()
        else:
            unmute_at_str = None

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO mutes (guild_id, user_id, unmute_at)
                VALUES (?, ?, ?)
            """, (guild.id, member.id, unmute_at_str))
            await db.commit()

        await ctx.send(f"🔇 Muted {member.mention} for {duration}{unit if duration > 0 else ''}. Reason: {reason}")
        await self.log_action(ctx.guild.id, member.id, ctx.author.id, "mute", reason)

    @commands.hybrid_command(name="unmute", description="Unmute a user. Reason required.")
    @commands.has_permissions(manage_roles=True)
    async def unmute(self, ctx, member: discord.Member, *, reason: str):
        if not self._validate_reason(reason):
            return await ctx.send("You must provide a valid reason for unmuting.")
        guild = ctx.guild
        muted_role = discord.utils.get(guild.roles, name="Muted")
        if muted_role is None or muted_role not in member.roles:
            return await ctx.send(f"{member.mention} is not muted.")

        await member.remove_roles(muted_role, reason=reason)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM mutes WHERE guild_id = ? AND user_id = ?", (guild.id, member.id))
            await db.commit()

        await ctx.send(f"🔊 Unmuted {member.mention}. Reason: {reason}")
        await self.log_action(ctx.guild.id, member.id, ctx.author.id, "unmute", reason)

    @commands.hybrid_command(name="timeout", description="Timeout a user. Reason required.")
    @commands.has_permissions(moderate_members=True)
    async def timeout(self, ctx, member: discord.Member, duration: int, unit: str = "m", *, reason: str):
        if not self._validate_reason(reason):
            return await ctx.send("You must provide a valid reason for timeout.")
        units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        seconds = duration * units.get(unit.lower(), 60)
        try:
            until = discord.utils.utcnow() + timedelta(seconds=seconds)
            await member.timeout(until=until, reason=reason)
            await ctx.send(f"⏲️ Timed out {member.mention} for {duration}{unit}. Reason: {reason}")
            await self.log_action(ctx.guild.id, member.id, ctx.author.id, "timeout", reason)
        except Exception as e:
            await ctx.send(f"❌ Failed to timeout: {e}")

    @commands.hybrid_command(name="untimeout", description="Remove timeout from a user. Reason required.")
    @commands.has_permissions(moderate_members=True)
    async def untimeout(self, ctx, member: discord.Member, *, reason: str):
        if not self._validate_reason(reason):
            return await ctx.send("You must provide a valid reason for removing timeout.")
        try:
            await member.timeout(until=None, reason=reason)
            await ctx.send(f"⏲️ Timeout removed from {member.mention}. Reason: {reason}")
            await self.log_action(ctx.guild.id, member.id, ctx.author.id, "untimeout", reason)
        except Exception as e:
            await ctx.send(f"❌ Failed to remove timeout: {e}")

    @tasks.loop(minutes=1)
    async def check_mutes(self):
        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT guild_id, user_id, unmute_at FROM mutes WHERE unmute_at IS NOT NULL") as cursor:
                rows = await cursor.fetchall()
                for guild_id, user_id, unmute_at_str in rows:
                    unmute_at = datetime.fromisoformat(unmute_at_str).replace(tzinfo=timezone.utc)
                    if now >= unmute_at:
                        guild = self.bot.get_guild(guild_id)
                        if guild is None:
                            continue
                        member = guild.get_member(user_id)
                        if member is None:
                            continue
                        muted_role = discord.utils.get(guild.roles, name="Muted")
                        if muted_role in member.roles:
                            try:
                                await member.remove_roles(muted_role, reason="Automatic unmute after mute duration")
                                await self.log_action(guild_id, user_id, self.bot.user.id, "auto_unmute", "Automatic unmute after timed mute expired")
                            except Exception:
                                pass
                        await db.execute("DELETE FROM mutes WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
                await db.commit()

    @check_mutes.before_loop
    async def before_check_mutes(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Moderation(bot))
