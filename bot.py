import discord
from discord.ext import commands, tasks
import os
import time
import json
from datetime import datetime

# Discord token Railway Environment Variable-ból
TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("A DISCORD_TOKEN nincs beállítva! Railway-en a Settings → Variables alatt add meg.")

# Intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# JSON fájl
FILENAME = "duty_logs.json"
if os.path.exists(FILENAME):
    with open(FILENAME, "r") as f:
        duty_logs = json.load(f)
else:
    duty_logs = {}

# Mentés
def save_logs():
    with open(FILENAME, "w") as f:
        json.dump(duty_logs, f)

# Segédfüggvény az óra:perc formátumhoz
def format_time(total_minutes):
    total_minutes = int(total_minutes)
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours}h {minutes}m"
