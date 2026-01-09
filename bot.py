import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import os
import time
import json
from datetime import datetime

# .env betöltése
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

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

# Bot elindult
@bot.event
async def on_ready():
    print(f'Bot elindult: {bot.user}')
    daily_summary.start()  # indítjuk az ütemezett napi összesítést

# Szolgálat kezdete
@bot.command()
async def kezd(ctx):
    user_id = str(ctx.author.id)
    today = datetime.now().strftime("%Y-%m-%d")

    if user_id not in duty_logs:
        duty_logs[user_id] = {}

    duty_logs[user_id]["start"] = time.time()
    duty_logs[user_id]["today"] = today
    save_logs()
    await ctx.send(f"{ctx.author.mention} szolgálatot kezdett!")

# Szolgálat vége
@bot.command()
async def vege(ctx):
    user_id = str(ctx.author.id)
    if user_id in duty_logs and "start" in duty_logs[user_id]:
        duration_seconds = time.time() - duty_logs[user_id]["start"]
        duration_minutes = int(duration_seconds // 60)
        date = duty_logs[user_id]["today"]

        if date not in duty_logs[user_id]:
            duty_logs[user_id][date] = 0

        duty_logs[user_id][date] += duration_minutes
        duty_logs[user_id].pop("start")
        duty_logs[user_id].pop("today")
        save_logs()
        await ctx.send(f"{ctx.author.mention} szolgálatot befejezte. Munkaidő: {format_time(duration_minutes)}")
    else:
        await ctx.send(f"{ctx.author.mention} nem volt szolgálatban!")

# Egyéni munkaidő napokra bontva
@bot.command()
async def status(ctx):
    user_id = str(ctx.author.id)
    if user_id not in duty_logs:
        await ctx.send(f"{ctx.author.mention} nincs rögzített munkaidőd.")
        return

    message = f"{ctx.author.mention} munkaideje napokra bontva:\n"
    for date, minutes in duty_logs[user_id].items():
        if date in ["start", "today"]:
            continue
        message += f"{date}: {format_time(minutes)}\n"
    await ctx.send(message)

# Minden felhasználó napokra bontott munkaideje
@bot.command()
async def list_all(ctx):
    if not duty_logs:
        await ctx.send("Nincs rögzített munkaidő!")
        return

    message = "Összes felhasználó munkaideje napokra bontva:\n"
    for user_id, data in duty_logs.items():
        try:
            user = await bot.fetch_user(int(user_id))
            message += f"{user.mention}:\n"
            for date, minutes in data.items():
                if date in ["start", "today"]:
                    continue
                message += f"  {date}: {format_time(minutes)}\n"
        except:
            message += f"{user_id}: hiba a név lekérésénél\n"

    await ctx.send(message)

# Admin parancs: clean @user
@bot.command()
@commands.has_permissions(administrator=True)
async def clean(ctx, member: discord.Member):
    user_id = str(member.id)
    if user_id in duty_logs:
        duty_logs.pop(user_id)
        save_logs()
        await ctx.send(f"{member.mention} összes munkaidejét töröltem.")
    else:
        await ctx.send(f"{member.mention}-nek nincs rögzített munkaideje.")

# Hibakezelés clean parancshoz
@clean.error
async def clean_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(f"{ctx.author.mention} nincs jogosultságod a parancs használatához!")
        
# Napi összesítés küldése 00:01-kor
@tasks.loop(minutes=1)
async def daily_summary():
    now = datetime.now()
    # Ha pontosan 00:01, akkor küldjük az összesítést
    if now.hour == 0 and now.minute == 1:
        # Csatorna neve
        channel_name = "munkaidö-log"
        # Megkeressük a csatornát minden guildban
        for guild in bot.guilds:
            channel = discord.utils.get(guild.text_channels, name=channel_name)
            if channel:
                message = f"Napi munkaidő összesítés ({now.strftime('%Y-%m-%d')}):\n"
                for user_id, data in duty_logs.items():
                    try:
                        user = await bot.fetch_user(int(user_id))
                        # Csak az adott napot jelenítjük
                        day_minutes = data.get(now.strftime('%Y-%m-%d'), 0)
                        message += f"{user.mention}: {format_time(day_minutes)}\n"
                    except:
                        continue
                await channel.send(message)

# Bot futtatása
bot.run(TOKEN)