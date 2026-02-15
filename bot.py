import discord
from discord.ext import commands
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

Thread(target=run).start()

# ===== DISCORD BOT =====
TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("DISCORD_TOKEN nincs beállítva!")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ===== SZOLGÁLATI BEÁLLÍTÁSOK =====
SERVICE_CHANNEL_ID = 1455619759340257300
SERVICE_ROLE_ID = 1472388518914428928

# ===== JSON FÁJL =====
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
    total_minutes = 0
    parts = value.split()
    for part in parts:
        if part.endswith("h"):
            total_minutes += float(part[:-1]) * 60
        elif part.endswith("m"):
            total_minutes += float(part[:-1])
        else:
            total_minutes += float(part)
    return total_minutes

# ===== SZOLGÁLATI GOMBOS VIEW =====
class ServiceView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Szolgálatba áll", emoji="🍔", style=discord.ButtonStyle.success, custom_id="start_service")
    async def start_service(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.user
        role = interaction.guild.get_role(SERVICE_ROLE_ID)
        if role in member.roles:
            await interaction.response.send_message("❌ Már szolgálatban vagy.", ephemeral=True)
            return
        await member.add_roles(role)
        await interaction.response.send_message("🍔 Szolgálatba álltál!", ephemeral=True)

    @discord.ui.button(label="Szolgálat leadása", emoji="🍔", style=discord.ButtonStyle.danger, custom_id="stop_service")
    async def stop_service(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.user
        role = interaction.guild.get_role(SERVICE_ROLE_ID)
        if role not in member.roles:
            await interaction.response.send_message("❌ Nem vagy szolgálatban.", ephemeral=True)
            return
        await member.remove_roles(role)
        await interaction.response.send_message("🍔 Szolgálat leadva!", ephemeral=True)

# ===== BOT READY =====
@bot.event
async def on_ready():
    print(f"Bot csatlakozott: {bot.user} ({bot.user.id})")
    bot.add_view(ServiceView())

# ===== REGISZTRÁCIÓ =====
@bot.command(name="reg")
async def reg(ctx, vezeteknev: str, keresztnev: str):
    try:
        new_name = f"{ctx.author.name} // {vezeteknev} {keresztnev}"
        await ctx.author.edit(nick=new_name)
        await ctx.send(f"✅ Sikeresen átírva a neved: **{new_name}**")
    except Exception as e:
        await ctx.send(f"⛔ Hiba: {e}")

# ===== SZOLGÁLATI PANEL =====
@bot.command(name="szolipanel")
async def szolipanel(ctx):
    if not is_admin(ctx):
        await ctx.send("⛔ Admin jog kell.")
        return
    try:
        channel = await bot.fetch_channel(SERVICE_CHANNEL_ID)
    except:
        await ctx.send("❌ Nem találom a csatornát. Ellenőrizd az ID-t.")
        return
    await channel.send(
        "## 🍔 Szolgálati Panel\nNyomj a gombokra a szolgálat kezeléséhez:",
        view=ServiceView()
    )
    await ctx.send("✅ Panel kirakva.")

# ===== !SZOLI =====
@bot.command(name="szoli")
async def szoli(ctx):
    if not is_admin(ctx):
        await ctx.send("⛔ Admin jog kell.")
        return
    role = ctx.guild.get_role(SERVICE_ROLE_ID)
    if not role or len(role.members) == 0:
        await ctx.send("Senki nincs szolgálatban. Mindenki lusta g*ci...")
        return
    description = ""
    for member in role.members:
        description += f"• {member.mention}\n"
    await ctx.send(f"🍔 **Szolgálatban lévők:**\n{description}")

# ===== IDŐ HOZZÁADÁS / LEVONÁS =====
@bot.command(name="hozzaad")
async def hozzaad(ctx, member: discord.Member, *, amount: str):
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
async def levon(ctx, member: discord.Member, *, amount: str):
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
