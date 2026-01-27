import discord
from discord.ext import commands
import os
import time
import json
from math import ceil

# ===== TOKEN =====
TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("DISCORD_TOKEN nincs beállítva")

# ===== INTENTS =====
intents = discord.Intents.default()
intents.message_content = True  # kell a parancsokhoz
intents.members = True  # kell a nick módosításhoz

bot = commands.Bot(command_prefix='!', intents=intents)

# ===== ADATFÁJL =====
FILENAME = "duty_logs.json"
if os.path.exists(FILENAME):
    with open(FILENAME, "r") as f:
        duty_logs = json.load(f)
else:
    duty_logs = {}

def save_logs():
    with open(FILENAME, "w") as f:
        json.dump(duty_logs, f)

def format_time(minutes):
    minutes = int(minutes)
    return f"{minutes//60}h {minutes%60}m"

def is_admin(ctx):
    return ctx.author.guild_permissions.administrator

# ===== TESZT PARANCS =====
@bot.command()
async def teszt(ctx):
    await ctx.send("✅ A bot működik és reagál!")

# ===== MUNKAIDŐ PARANCSOK =====
@bot.command()
async def kezd(ctx):
    uid = str(ctx.author.id)
    if uid in duty_logs and "start" in duty_logs[uid]:
        return await ctx.send("❌ Már műszakban vagy.")

    duty_logs.setdefault(uid, {})
    duty_logs[uid]["start"] = time.time()
    save_logs()
    await ctx.send(f"🟢 Műszak elkezdve: {ctx.author.mention}")

@bot.command()
async def vege(ctx):
    uid = str(ctx.author.id)
    if uid not in duty_logs or "start" not in duty_logs[uid]:
        return await ctx.send("❌ Nincs aktív műszakod.")

    worked = (time.time() - duty_logs[uid]["start"]) / 60
    duty_logs[uid]["total"] = duty_logs[uid].get("total", 0) + worked
    duty_logs[uid].pop("start")
    save_logs()

    await ctx.send(f"✅ Műszak lezárva — {format_time(worked)}")

@bot.command()
async def ido(ctx, member: discord.Member = None):
    member = member or ctx.author
    total = duty_logs.get(str(member.id), {}).get("total", 0)
    await ctx.send(f"⏱ {member.display_name}: {format_time(total)}")

@bot.command()
async def delete(ctx, arg=None):
    if not is_admin(ctx):
        return await ctx.send("⛔ Admin only.")
    if arg != "all":
        return await ctx.send("Használat: !delete all")

    duty_logs.clear()
    save_logs()
    await ctx.send("🧹 Minden munkaidő törölve.")

@bot.command()
async def list(ctx, arg=None):
    if arg != "all":
        return await ctx.send("Használat: !list all")

    data = []
    for uid, d in duty_logs.items():
        if "total" in d:
            try:
                m = await ctx.guild.fetch_member(int(uid))
                data.append((m.display_name, d["total"]))
            except:
                pass

    if not data:
        return await ctx.send("Nincs adat.")

    data.sort(key=lambda x: x[1], reverse=True)

    text = ""
    for i, (name, mins) in enumerate(data, 1):
        text += f"**{i}.** {name} — {format_time(mins)}\n"

    await ctx.send(text)

# ===== REGISZTRÁCIÓ =====
@bot.command()
async def reg(ctx, vezeteknev=None, keresztnev=None):
    if not vezeteknev or not keresztnev:
        return await ctx.send("Használat: !reg Vezetéknév Keresztnév")

    base_name = ctx.author.display_name.split("//")[0].strip()
    new_nick = f"{base_name} // {vezeteknev} {keresztnev}"

    try:
        await ctx.author.edit(nick=new_nick)
        await ctx.send("✅ Sikeres regisztráció.")
    except:
        await ctx.send("❌ Nincs jogom nevet módosítani.")

# ===== BOT INDÍTÁS =====
bot.run(TOKEN)
