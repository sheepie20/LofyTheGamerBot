from dotenv import load_dotenv
import discord
import os
load_dotenv()

TOKEN = os.getenv("TOKEN")
INTENTS = discord.Intents.all()
COMMAND_PREFIX = "$"
STATUS = discord.Status.online