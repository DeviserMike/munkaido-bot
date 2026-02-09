import discord
from discord.ext import commands, tasks
import os
import time
import json
from flask import Flask
from threading import Thread

# ===== FLASK KEEP ALIVE =====
app = Flask("")

@app.route("/")
def home():
    return "Bot fut!"

def run():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

t = Thread(target=run)
t.start()

# ===== DISCORD BOT =====
TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("A DISCORD_TOKEN nincs beállítva! Railway-en a Settings → Variables alatt add meg.")

intents = discord.Intents.default()
intents.members = True  # kell a @user parancsokhoz
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# JSON fájl
FILENAME = "duty_logs.json"
if os.path.exists(FILENAME):
    with open(FILENAME, "r") as f:
        duty_logs = json.load(f)
else:
    duty_logs = {}

# ===== SEGÉDFÜGGVÉNYEK =====
def save_logs():
    with open(FILENAME, "w") as f:
        json.dump(duty_logs, f)

def format_time(total_minutes):
    total_minutes = int(total_minutes)
    return f"{total_minutes // 60}h {total_minutes % 60}m"

def is_admin(ctx):
    return ctx.author.guild_permissions.administrator

def parse_time(value: str):
    value = value.lower().replace(",", ".")
    if value.endswith("h"):
        return float(value[:-1]) * 60
    return float(value)

# ===== BOT READY =====
@bot.event
async def on_ready():
    print(f"Bot csatlakozott: {bot.user} ({bot.user.id})")

# ===== REGISZTRÁCIÓ =====
@bot.command(name="reg")
async def reg(ctx, vezeteknev: str, keresztnev: str):
    try:
        new_name = f"{ctx.author.name} // {vezeteknev} {keresztnev}"
        await ctx.author.edit(nick=new_name)
        await ctx.send(f"✅ Sikeresen átírva a neved: **{new_name}**")
    except Exception as e:
        await ctx.send(f"⛔ Hiba: {e}")

# ===== MŰSZAK =====
@bot.command(name="kezd")
async def kezd(ctx):
    uid = str(ctx.author.id)
    if uid in duty_logs and "start" in duty_logs[uid]:
        await ctx.send("❌ Már aktív műszakban vagy.")
        return
    duty_logs.setdefault(uid, {})
    duty_logs[uid]["start"] = time.time()
    save_logs()
    await ctx.send(f"🟢 **Műszak elkezdve:** {ctx.author.mention}")

@bot.command(name="forcekezdes")
async def forcekezdes(ctx, member: discord.Member):
    if not is_admin(ctx):
        await ctx.send("⛔ Admin jog kell.")
        return
    uid = str(member.id)
    if uid in duty_logs and "start" in duty_logs[uid]:
        await ctx.send(f"❌ {member.mention} már műszakban van.")
        return
    duty_logs.setdefault(uid, {})
    duty_logs[uid]["start"] = time.time()
    save_logs()
    await ctx.send(f"🟢 **Admin szolgálatba állította:** {member.mention}")

@bot.command(name="vege")
async def vege(ctx, member: discord.Member = None):
    member = member or ctx.author
    if member != ctx.author and not is_admin(ctx):
        await ctx.send("⛔ Csak admin zárhatja le más műszakát.")
        return
    uid = str(member.id)
    if uid not in duty_logs or "start" not in duty_logs[uid]:
        await ctx.send(f"❌ {member.mention} nincs aktív műszakban.")
        return
    worked = (time.time() - duty_logs[uid]["start"]) / 60
    duty_logs[uid]["total"] = duty_logs[uid].get("total", 0) + worked
    duty_logs[uid].pop("start")
    save_logs()
    await ctx.send(f"✅ **Műszak lezárva:** {member.mention}\n⏱ Ledolgozott idő: **{format_time(worked)}**")

@bot.command(name="forcevege")
async def forcevege(ctx, member: discord.Member):
    if not is_admin(ctx):
        await ctx.send("⛔ Admin jog kell.")
        return
    uid = str(member.id)
    if uid not in duty_logs or "start" not in duty_logs[uid]:
        await ctx.send(f"❌ {member.mention} nincs aktív műszakban.")
        return
    worked = (time.time() - duty_logs[uid]["start"]) / 60
    duty_logs[uid]["total"] = duty_logs[uid].get("total", 0) + worked
    duty_logs[uid].pop("start")
    save_logs()
    await ctx.send(f"🛑 **Admin lezárta a műszakot:** {member.mention}\n⏱ Hozzáadott idő: **{format_time(worked)}**")

# ===== IDŐ HOZZÁADÁS / LEVONÁS =====
@bot.command(name="hozzaad")
async def hozzaad(ctx, member: discord.Member, amount: str):
    if not is_admin(ctx):
        await ctx.send("⛔ Admin jog kell.")
        return
    minutes = parse_time(amount)
    uid = str(member.id)
    duty_logs.setdefault(uid, {})
    duty_logs[uid]["total"] = duty_logs[uid].get("total", 0) + minutes
    save_logs()
    await ctx.send(f"➕ **Hozzáadva:** {member.mention} ({format_time(minutes)})")

@bot.command(name="levon")
async def levon(ctx, member: discord.Member, amount: str):
    if not is_admin(ctx):
        await ctx.send("⛔ Admin jog kell.")
        return
    minutes = parse_time(amount)
    uid = str(member.id)
    duty_logs.setdefault(uid, {})
    duty_logs[uid]["total"] = max(0, duty_logs[uid].get("total", 0) - minutes)
    save_logs()
    await ctx.send(f"➖ **Levonva:** {member.mention} ({format_time(minutes)})")

# ===== IDŐ LEKÉRDEZÉS =====
@bot.command(name="ido")
async def ido(ctx, member: discord.Member = None):
    member = member or ctx.author
    uid = str(member.id)
    total = duty_logs.get(uid, {}).get("total", 0)
    await ctx.send(f"⏱ **{member.mention} összes munkaideje:** {format_time(total)}")

# ===== LISTA =====
@bot.command(name="list")
async def list_all(ctx, action: str = None):
    if action != "all":
        await ctx.send("Használat: `!list all`")
        return
    user_times = []
    for uid, data in duty_logs.items():
        total = data.get("total", 0)
        if total > 0:
            try:
                member = await ctx.guild.fetch_member(int(uid))
                user_times.append((member.display_name, total))
            except:
                user_times.append((f"User {uid}", total))
    user_times.sort(key=lambda x: x[1], reverse=True)
    if not user_times:
        await ctx.send("📋 **Nincs még rögzített munkaidő.**")
        return
    description_text = ""
    for idx, (name, total_minutes) in enumerate(user_times, start=1):
        description_text += f"**{idx}.** {name} - `{format_time(total_minutes)}`\n"
    await ctx.send(f"📋 Munkaidő Lista:\n{description_text}")

# ===== DELETE ALL =====
@bot.command(name="delete")
async def delete(ctx, action: str = None):
    if not is_admin(ctx):
        await ctx.send("⛔ Admin jog kell.")
        return
    if action != "all":
        await ctx.send("Használat: `!delete all`")
        return
    duty_logs.clear()
    save_logs()
    await ctx.send("🧹 **Minden felhasználó munkaideje törölve lett.**")

# ===== BOT INDÍTÁS =====
bot.run(TOKEN)
