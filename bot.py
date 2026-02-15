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
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# ===== SZOLGÁLATI BEÁLLÍTÁSOK =====
SERVICE_CHANNEL_ID = 1455619759340257300
SERVICE_ROLE_ID = 1472388518914428928

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

# ===== SZOLGÁLATI GOMBOS VIEW =====
class ServiceView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🟢 Szolgálatba áll", style=discord.ButtonStyle.success, custom_id="start_service")
    async def start_service(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.user
        role = interaction.guild.get_role(SERVICE_ROLE_ID)

        if role in member.roles:
            await interaction.response.send_message("❌ Már szolgálatban vagy.", ephemeral=True)
            return

        await member.add_roles(role)
        await interaction.response.send_message("🟢 Szolgálatba álltál!", ephemeral=True)

    @discord.ui.button(label="🔴 Szolgálat leadása", style=discord.ButtonStyle.danger, custom_id="stop_service")
    async def stop_service(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.user
        role = interaction.guild.get_role(SERVICE_ROLE_ID)

        if role not in member.roles:
            await interaction.response.send_message("❌ Nem vagy szolgálatban.", ephemeral=True)
            return

        await member.remove_roles(role)
        await interaction.response.send_message("🔴 Szolgálat leadva!", ephemeral=True)

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

# ===== SZOLGÁLATI PANEL PARANCS =====
@bot.command(name="szolipanel")
async def szolipanel(ctx):
    if not is_admin(ctx):
        await ctx.send("⛔ Admin jog kell.")
        return

    channel = bot.get_channel(SERVICE_CHANNEL_ID)
    if not channel:
        await ctx.send("❌ Hibás csatorna ID.")
        return

    await channel.send(
        "## 🚔 Szolgálati Panel\nNyomj gombot a szolgálat kezeléséhez:",
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

    await ctx.send(f"🚔 **Szolgálatban lévők:**\n{description}")

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

# ===== BOT INDÍTÁS =====
bot.run(TOKEN)
