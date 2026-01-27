import discord
from discord.ext import commands
import os

# Token a Railway környezetből
TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("A DISCORD_TOKEN nincs beállítva!")

# Intents beállítása
intents = discord.Intents.default()
intents.message_content = True  # Kötelező a parancsokhoz
intents.members = True  # Kell a !reg parancshoz

# Bot létrehozása
bot = commands.Bot(command_prefix="!", intents=intents)

# ===== TESZT PARANCS =====
@bot.command()
async def teszt(ctx):
    await ctx.send(f"✅ Üzeneted látva: {ctx.author.mention}")

# ===== MŰSZAK PARANCSOK =====
duty_logs = {}

@bot.command()
async def kezd(ctx):
    user_id = str(ctx.author.id)
    if user_id in duty_logs and "start" in duty_logs[user_id]:
        await ctx.send("❌ Már aktív műszakban vagy.")
        return
    duty_logs.setdefault(user_id, {})
    duty_logs[user_id]["start"] = ctx.message.created_at.timestamp()
    await ctx.send(f"🟢 Műszak elkezdve: {ctx.author.mention}")

@bot.command()
async def vege(ctx):
    user_id = str(ctx.author.id)
    if user_id not in duty_logs or "start" not in duty_logs[user_id]:
        await ctx.send("❌ Nincs aktív műszakod.")
        return
    start_time = duty_logs[user_id]["start"]
    worked_minutes = (ctx.message.created_at.timestamp() - start_time) / 60
    duty_logs[user_id].pop("start")
    await ctx.send(f"✅ Műszak lezárva: {ctx.author.mention}\n⏱ Ledolgozott idő: {int(worked_minutes)} perc")

# ===== REGISZTRÁCIÓ PARANCS =====
@bot.command()
async def reg(ctx, vezetek: str, kereszt: str):
    new_name = f"{ctx.author.display_name} // {vezetek} {kereszt}"
    try:
        await ctx.author.edit(nick=new_name)
        await ctx.send(f"✅ Sikeres regisztráció! Új név: {new_name}")
    except:
        await ctx.send("❌ Nem sikerült átnevezni. Ellenőrizd a bot engedélyeit.")

# ===== BOT INDÍTÁS =====
bot.run(TOKEN)
