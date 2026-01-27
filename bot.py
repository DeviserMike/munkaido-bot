import discord
from discord.ext import commands
import os
import time
import json

# ===== TOKEN (Railway Environment Variable) =====
TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("A DISCORD_TOKEN nincs beállítva!")

# ===== INTENTS =====
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# ===== MUNKAIDŐ ADATOK =====
DUTY_FILE = "duty_logs.json"
if os.path.exists(DUTY_FILE):
    with open(DUTY_FILE, "r") as f:
        duty_logs = json.load(f)
else:
    duty_logs = {}

def save_duty():
    with open(DUTY_FILE, "w") as f:
        json.dump(duty_logs, f)

def format_time(total_minutes):
    total_minutes = int(total_minutes)
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours}h {minutes}m"

def is_admin(ctx):
    return ctx.author.guild_permissions.administrator

# ===== REGISZTRÁCIÓ ADATOK =====
REG_FILE = "registered.json"
if os.path.exists(REG_FILE):
    with open(REG_FILE, "r") as f:
        registered = json.load(f)
else:
    registered = {}

def save_registered():
    with open(REG_FILE, "w") as f:
        json.dump(registered, f)

# ================= PARANCSOK =================

@bot.command(name="kezd")
async def kezd(ctx):
    user_id = str(ctx.author.id)

    if user_id in duty_logs and "start" in duty_logs[user_id]:
        await ctx.send("❌ Már aktív műszakban vagy.")
        return

    duty_logs.setdefault(user_id, {})
    duty_logs[user_id]["start"] = time.time()
    save_duty()

    await ctx.send(f"🟢 **Műszak elkezdve:** {ctx.author.mention}")

@bot.command(name="vege")
async def vege(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    elif member != ctx.author and not is_admin(ctx):
        await ctx.send("⛔ Más műszakját csak admin zárhatja le.")
        return

    user_id = str(member.id)

    if user_id not in duty_logs or "start" not in duty_logs[user_id]:
        await ctx.send("❌ Nincs aktív műszak.")
        return

    worked_minutes = (time.time() - duty_logs[user_id]["start"]) / 60
    duty_logs[user_id]["total"] = duty_logs[user_id].get("total", 0) + worked_minutes
    duty_logs[user_id].pop("start")

    save_duty()

    await ctx.send(
        f"✅ **Műszak lezárva:** {member.mention}\n"
        f"⏱ Ledolgozott idő: **{format_time(worked_minutes)}**"
    )

@bot.command(name="ido")
async def ido(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    elif not is_admin(ctx):
        await ctx.send("⛔ Más idejét csak admin nézheti.")
        return

    user_id = str(member.id)
    total = duty_logs.get(user_id, {}).get("total", 0)

    await ctx.send(
        f"⏱ **{member.display_name} összes munkaideje:** {format_time(total)}"
    )

@bot.command(name="clean")
async def clean(ctx, target: discord.Role = None):
    if not is_admin(ctx):
        await ctx.send("⛔ Ehhez admin jogosultság kell.")
        return

    if target != ctx.guild.default_role:
        await ctx.send("Használat: `!clean @everyone`")
        return

    duty_logs.clear()
    save_duty()

    await ctx.send("🧹 **Minden munkaidő adat törölve lett.**")

# ===== REG PARANCS =====
@bot.command(name="reg")
async def reg(ctx, vezeteknev: str = None, keresztnev: str = None):
    user_id = str(ctx.author.id)

    if user_id in registered:
        await ctx.send("❌ Már regisztráltál. Ez a parancs csak egyszer használható.")
        return

    if vezeteknev is None or keresztnev is None:
        await ctx.send("❌ Használat: `!reg Vezetéknév Keresztnév`")
        return

    new_nick = f"{ctx.author.name} // {vezeteknev} {keresztnev}"

    try:
        await ctx.author.edit(nick=new_nick)
        registered[user_id] = new_nick
        save_registered()
        await ctx.send(f"✅ **Sikeres regisztráció!**\nÚj név: **{new_nick}**")
    except discord.Forbidden:
        await ctx.send("❌ Nincs jogosultságom a név módosításához.")
    except discord.HTTPException:
        await ctx.send("❌ Hiba történt a név módosításakor.")

# ===== BOT INDÍTÁS =====
bot.run(TOKEN)
