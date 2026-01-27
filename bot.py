import discord
from discord.ext import commands
import os
import time
import json
from math import ceil
from flask import Flask
from threading import Thread

# ===== FLASK KEEP ALIVE =====
app = Flask("")

@app.route("/")
def home():
    return "Bot fut!"

def run():
    app.run(host="0.0.0.0", port=8080)

# Indítjuk külön szálon, hogy a bot fusson mellette
t = Thread(target=run)
t.start()

# ===== DISCORD BOT =====

# Token Railway Environment Variable-ból
TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("A DISCORD_TOKEN nincs beállítva! Railway-en a Settings → Variables alatt add meg.")

# Intents
intents = discord.Intents.default()
intents.members = True  # kell a !reg-hez, ha nevet módosítunk
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

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

# Idő formázás
def format_time(total_minutes):
    total_minutes = int(total_minutes)
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours}h {minutes}m"

# Admin ellenőrzés
def is_admin(ctx):
    return ctx.author.guild_permissions.administrator

# ===== PARANCSOK =====

@bot.event
async def on_ready():
    print(f"Bot csatlakozott: {bot.user} ({bot.user.id})")

# ----- REGISZTRÁCIÓ -----
@bot.command(name="reg")
async def reg(ctx, vezeteknev: str, keresztnev: str):
    try:
        new_name = f"{ctx.author.name} // {vezeteknev} {keresztnev}"
        await ctx.author.edit(nick=new_name)
        await ctx.send(f"✅ Sikeresen átírva a neved: **{new_name}**")
    except Exception as e:
        await ctx.send(f"⛔ Hiba: {e}")

# ----- MŰSZAK -----
@bot.command(name="kezd")
async def kezd(ctx):
    user_id = str(ctx.author.id)
    if user_id in duty_logs and "start" in duty_logs[user_id]:
        await ctx.send("❌ Már aktív műszakban vagy.")
        return

    duty_logs.setdefault(user_id, {})
    duty_logs[user_id]["start"] = time.time()
    save_logs()
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
        await ctx.send(f"❌ {member.mention} nincs aktív műszakban.")
        return

    start_time = duty_logs[user_id]["start"]
    worked_minutes = (time.time() - start_time) / 60

    duty_logs[user_id]["total"] = duty_logs[user_id].get("total", 0) + worked_minutes
    duty_logs[user_id].pop("start")
    save_logs()

    await ctx.send(
        f"✅ **Műszak lezárva:** {member.mention}\n"
        f"⏱ Ledolgozott idő: **{format_time(worked_minutes)}**"
    )

# ----- IDŐ -----
@bot.command(name="ido")
async def ido(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    user_id = str(member.id)
    total = duty_logs.get(user_id, {}).get("total", 0)
    await ctx.send(f"⏱ **{member.mention} összes munkaideje:** {format_time(total)}")

# ----- LIST -----
@bot.command(name="list")
async def list_all(ctx, action: str = None):
    if action != "all":
        await ctx.send("Használat: `!list all`")
        return

    user_times = []
    for user_id, data in duty_logs.items():
        total = data.get("total", 0)
        if total > 0:
            try:
                member = await ctx.guild.fetch_member(int(user_id))
                user_times.append((member.display_name, total))
            except:
                user_times.append((f"User {user_id}", total))

    user_times.sort(key=lambda x: x[1], reverse=True)
    if not user_times:
        await ctx.send("📋 **Nincs még rögzített munkaidő.**")
        return

    description_text = ""
    for idx, (name, total_minutes) in enumerate(user_times, start=1):
        description_text += f"**{idx}.** {name} - `{format_time(total_minutes)}`\n"

    await ctx.send(f"📋 Munkaidő Lista:\n{description_text}")

# ----- DELETE -----
@bot.command(name="delete")
async def delete(ctx, action: str = None):
    if not is_admin(ctx):
        await ctx.send("⛔ Ehhez a parancshoz rendszergazda jogosultság kell.")
        return
    if action != "all":
        await ctx.send("Használat: `!delete all`")
        return
    duty_logs.clear()
    save_logs()
    await ctx.send("🧹 **Minden felhasználó munkaideje törölve lett.**")

# ===== BOT INDÍTÁS =====
bot.run(TOKEN)
