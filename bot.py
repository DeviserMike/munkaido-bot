import discord
from discord.ext import commands
import os
import time
import json
from math import ceil

# ===== TOKEN =====
TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("DISCORD_TOKEN nincs beállítva Railway-en!")

# ===== INTENTS =====
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

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
        json.dump(duty_logs, f, indent=4)

# ===== SEGÉDEK =====
def format_time(minutes):
    minutes = int(minutes)
    h = minutes // 60
    m = minutes % 60
    return f"{h}h {m}m"

def is_admin(ctx):
    return ctx.author.guild_permissions.administrator

# =========================
#        PARANCSOK
# =========================

@bot.command()
async def kezd(ctx):
    uid = str(ctx.author.id)

    if uid in duty_logs and "start" in duty_logs[uid]:
        await ctx.send("❌ Már aktív műszakban vagy.")
        return

    duty_logs.setdefault(uid, {})
    duty_logs[uid]["start"] = time.time()
    save_logs()

    await ctx.send(f"🟢 **Műszak elkezdve:** {ctx.author.mention}")

# -------------------------

@bot.command()
async def vege(ctx):
    uid = str(ctx.author.id)

    if uid not in duty_logs or "start" not in duty_logs[uid]:
        await ctx.send("❌ Nincs aktív műszakod.")
        return

    worked_minutes = (time.time() - duty_logs[uid]["start"]) / 60
    duty_logs[uid]["total"] = duty_logs[uid].get("total", 0) + worked_minutes
    duty_logs[uid].pop("start")

    save_logs()

    await ctx.send(
        f"✅ **Műszak lezárva:** {ctx.author.mention}\n"
        f"⏱ Ledolgozott idő: **{format_time(worked_minutes)}**"
    )

# -------------------------

@bot.command()
async def ido(ctx):
    uid = str(ctx.author.id)
    total = duty_logs.get(uid, {}).get("total", 0)

    await ctx.send(
        f"⏱ **{ctx.author.mention} összes munkaideje:** {format_time(total)}"
    )

# -------------------------

@bot.command()
async def delete(ctx, arg=None):
    if not is_admin(ctx):
        await ctx.send("⛔ Ehhez admin jogosultság kell.")
        return

    if arg != "all":
        await ctx.send("Használat: `!delete all`")
        return

    duty_logs.clear()
    save_logs()

    await ctx.send("🧹 **Minden munkaidő törölve lett.**")

# -------------------------

@bot.command()
async def list(ctx, arg=None):
    if arg != "all":
        await ctx.send("Használat: `!list all`")
        return

    users = []
    for uid, data in duty_logs.items():
        total = data.get("total", 0)
        if total > 0:
            try:
                member = await ctx.guild.fetch_member(int(uid))
                users.append((member.display_name, total))
            except:
                users.append((uid, total))

    if not users:
        await ctx.send("📋 Nincs még rögzített munkaidő.")
        return

    users.sort(key=lambda x: x[1], reverse=True)

    msg = "📋 **Munkaidő lista:**\n\n"
    for i, (name, total) in enumerate(users, start=1):
        msg += f"**{i}.** {name} – `{format_time(total)}`\n"

    await ctx.send(msg)

# -------------------------

@bot.command()
async def reg(ctx, vezeteknev: str = None, keresztnev: str = None):
    if vezeteknev is None or keresztnev is None:
        await ctx.send("Használat: `!reg Vezetéknév Keresztnév`")
        return

    if "//" in ctx.author.display_name:
        await ctx.send("❌ Már regisztráltál.")
        return

    new_name = f"{ctx.author.display_name} // {vezeteknev} {keresztnev}"

    try:
        await ctx.author.edit(nick=new_name)
        await ctx.send(f"✅ Regisztráció sikeres: **{new_name}**")
    except:
        await ctx.send("❌ Nem tudtam átírni a neved (nincs jogom).")

# =========================
#        INDÍTÁS
# =========================
bot.run(TOKEN)
