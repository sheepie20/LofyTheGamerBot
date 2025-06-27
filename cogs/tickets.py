import discord
from discord.ext import commands
from discord.ui import Button, button, View
import asyncio
import io
import chat_exporter
import aiosqlite
import uuid
import aiohttp

async def get_ticket_settings(guild_id):
    async with aiosqlite.connect("ticket_system.db") as db:
        async with db.execute('SELECT admin_role_id, opened_tickets_category_id, closed_tickets_category_id, log_channel_id FROM ticket_settings WHERE guild_id = ?', (guild_id,)) as cursor:
            return await cursor.fetchone()

async def get_transcript(channel: discord.TextChannel, bot: commands.Bot):
    unique_id = str(uuid.uuid4())
    
    transcript = await chat_exporter.export(
        channel,
        tz_info="UTC",
        military_time=True,
        bot=bot,
    )

    if transcript is None:
        return

    transcript_bytes = io.BytesIO(transcript.encode('utf-8'))
    transcript_filename = f"{unique_id}_{channel.topic.split(' ')[0]}_ticket.html"
    
    async with aiohttp.ClientSession() as session:
        form_data = aiohttp.FormData()
        form_data.add_field(
            'file',
            transcript_bytes,
            filename=transcript_filename,
            content_type='text/html'
        )
        
        async with session.post("https://sheepie.pythonanywhere.com/upload", data=form_data) as response:
            response_text = await response.text()
            if response.status == 200:
                _, _, _, log_channel_id = await get_ticket_settings(channel.guild.id)
                log_channel = channel.guild.get_channel(log_channel_id)
                embed = discord.Embed(
                    title="Ticket closed.",
                    description=f"Click [here](https://sheepie.pythonanywhere.com/uploads/{transcript_filename}) for the transcript.",
                    color=discord.Color.red()
                )
                await log_channel.send(embed=embed)
                await channel.send(embed=embed)
            else:
                print(f"Failed to upload file. Status code: {response.status}")
                print(f"Response text: {response_text}")

class CreateButton(View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @button(label="Create Ticket", style=discord.ButtonStyle.blurple, emoji="🎫", custom_id="ticketopen")
    async def ticket(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)

        settings = await get_ticket_settings(interaction.guild.id)
        if not settings:
            await interaction.followup.send("Ticket system is not configured for this server. Run ``/tickets setup``", ephemeral=True)
            return
        
        admin_role_id, opened_tickets_category_id, _, log_channel_id = settings
        
        category: discord.CategoryChannel = discord.utils.get(interaction.guild.categories, id=opened_tickets_category_id)
        for ch in category.text_channels:
            if ch.topic == f"{interaction.user.id} DO NOT CHANGE THE TOPIC OF THIS CHANNEL!":
                await interaction.followup.send(f"You already have a ticket open in {ch.mention}", ephemeral=True)
                return
        
        r1: discord.Role = interaction.guild.get_role(admin_role_id)
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            r1: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        channel = await category.create_text_channel(
            name=f"{interaction.user}-ticket",
            topic=f"{interaction.user.id} DO NOT CHANGE THE TOPIC OF THIS CHANNEL!",
            overwrites=overwrites
        )

        await channel.send(f"<@&{admin_role_id}>", embed=discord.Embed(
            title="Ticket Created!", 
            description="A staff member will assist you shortly.",
            color=discord.Color.random()), view=CloseButton(self.bot))
        await interaction.followup.send(f"Created your ticket in {channel.mention}", ephemeral=True)

        log_channel = interaction.guild.get_channel(log_channel_id)
        if log_channel:
            await log_channel.send(f"Ticket created by {interaction.user.mention} in {channel.mention} ({channel.name})")

class CloseButton(View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @button(label="Close the ticket", style=discord.ButtonStyle.red, custom_id="closeticket", emoji="🔒")
    async def close(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)

        settings = await get_ticket_settings(interaction.guild.id)
        if not settings:
            await interaction.followup.send("Ticket system is not configured for this server.", ephemeral=True)
            return

        admin_role_id, _, closed_tickets_category_id, log_channel_id = settings

        await interaction.channel.send("Closing this ticket in 3 seconds...")
        await asyncio.sleep(3)

        category: discord.CategoryChannel = discord.utils.get(interaction.guild.categories, id=closed_tickets_category_id)
        r1: discord.Role = interaction.guild.get_role(admin_role_id)
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            r1: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        await interaction.channel.edit(category=category, overwrites=overwrites)
        await interaction.channel.send(embed=discord.Embed(description="Ticket Closed!", color=discord.Color.random()), view=TrashButton())

        log_channel = interaction.guild.get_channel(log_channel_id)
        if log_channel:
            await get_transcript(interaction.channel, self.bot)

class TrashButton(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Delete the ticket", style=discord.ButtonStyle.red, emoji="🗑️", custom_id="trash")
    async def trash(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        await interaction.channel.send("Deleting the ticket in 3 seconds...")

        await asyncio.sleep(3)

        settings = await get_ticket_settings(interaction.guild.id)
        log_channel_id = settings[3]

        log_channel = interaction.guild.get_channel(log_channel_id)
        if log_channel:
            await log_channel.send(f"Ticket **{interaction.channel.name}** deleted by {interaction.user.mention}")

        await interaction.channel.delete()

class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot

    @commands.hybrid_group(name="tickets", description="Ticket management commands", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def tickets_group(self, ctx: commands.Context):
        """Default response when no subcommand is provided."""
        await ctx.send("Use `/tickets setup`, `/tickets panel`, or `/tickets reset-settings` to manage the ticket system. For more help, type `/tickets help`")

    @tickets_group.command(name="setup", description="Setup ticket system.")
    @commands.has_permissions(administrator=True)
    async def setup_tickets(self, ctx: commands.Context, admin_role: discord.Role):
        await ctx.defer()
        settings = await get_ticket_settings(ctx.guild.id)
        if settings:
            await ctx.reply("Ticket system is already set up for this server. Use `/tickets reset-settings` to reset the configuration if needed.", ephemeral=True)
            return

        open_category = await ctx.guild.create_category("Opened Tickets")
        closed_category = await ctx.guild.create_category("Closed Tickets")

        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            admin_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        log_channel = discord.utils.get(ctx.guild.text_channels, name="transcripts")
        
        if log_channel:
            await log_channel.edit(overwrites=overwrites)
            await ctx.send(f"Found existing channel {log_channel.mention}. Updated its permissions.")
        else:
            log_channel = await ctx.guild.create_text_channel("transcripts", overwrites=overwrites)

        async with aiosqlite.connect("ticket_system.db") as db:
            await db.execute('''
                INSERT OR REPLACE INTO ticket_settings (guild_id, admin_role_id, opened_tickets_category_id, closed_tickets_category_id, log_channel_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (ctx.guild.id, admin_role.id, open_category.id, closed_category.id, log_channel.id))
            await db.commit()

        embed = discord.Embed(
            title="Success.",
            description=f"Created categories called \"Opened Tickets\" and \"Closed Tickets\"\nUsing {log_channel.mention} for transcripts.\nNow you can use `/tickets panel` to send the button to create a ticket.",
            color=discord.Color.green()
        )
        await ctx.reply(embed=embed)

    @tickets_group.command(name="panel", description="Display ticket panel.")
    @commands.has_permissions(administrator=True)
    async def ticket_panel(self, ctx: commands.Context):
        await ctx.reply("Sending panel...", ephemeral=True)
        await ctx.channel.send(
            embed=discord.Embed(
                description="Press the button to create a new ticket!"
            ),
            view=CreateButton(self.bot)
        )
        

    @tickets_group.command(name="reset-settings", description="Clear the ticket system settings for this server.")
    @commands.has_permissions(administrator=True)
    async def clear_tickets(self, ctx: commands.Context):
        async with aiosqlite.connect("ticket_system.db") as db:
            await db.execute('DELETE FROM ticket_settings WHERE guild_id = ?', (ctx.guild.id,))
            await db.commit()

        await ctx.send("Ticket system settings have been cleared for this server.")

    @tickets_group.command(name="help", description="Tutorial for setting-up the ticket system")
    async def tickets_help(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Ticket system.",
            description="Run ``/tickets setup [admin-role]`` to setup. \nIf you want to reset the settings, type ``/tickets reset-settings``\nTo send the button to create a ticket, type ``/tickets panel``"
        )
        await ctx.send(embed=embed)
    
    @tickets_group.command(name="open", description="Open a ticket")
    async def open_ticket(self, ctx: commands.Context):
        await ctx.send(
            embed=discord.Embed(
                description="Press the button to create a new ticket!"
            ),
            view=CreateButton(self.bot),
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))
