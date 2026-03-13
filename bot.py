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

# ===== BOT =====
TOKEN = os.environ.get("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ===== SZERVER LOG CSATORNÁK =====
# IDE ÍRD A SZERVER ID-KET
LOG_CHANNELS = {
    111111111111111111: 1458925615989260319,  # első discord
    222222222222222222: 1482119191812116651   # második discord
}

# ===== SZERVER SPECIFIKUS SZOLGÁLATI SZEREPKÖR =====
SERVICE_ROLES = {
    111111111111111111: 1472388518914428928,  # első discord
    222222222222222222: 1482120925687316641   # második discord
}

# ===== JSON =====
FILENAME = "duty_logs.json"

if os.path.exists(FILENAME):
    with open(FILENAME,"r") as f:
        duty_logs = json.load(f)
else:
    duty_logs = {}

def save_logs():
    with open(FILENAME,"w") as f:
        json.dump(duty_logs,f)

def format_time(minutes):
    minutes=int(minutes)
    return f"{minutes//60}h {minutes%60}m"

def parse_time(value):
    value=value.lower().replace(",",".")
    total=0
    parts=value.split()
    for p in parts:
        if p.endswith("h"):
            total+=float(p[:-1])*60
        elif p.endswith("m"):
            total+=float(p[:-1])
        else:
            total+=float(p)
    return total

def is_admin(ctx):
    return ctx.author.guild_permissions.administrator

# ===== LOG FUNKCIÓ =====
async def send_log(guild,embed):
    log_id=LOG_CHANNELS.get(guild.id)
    if not log_id:
        return
    channel=guild.get_channel(log_id)
    if channel:
        await channel.send(embed=embed)

# ===== PANEL =====
class ServiceView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Szolgálatba áll", emoji="🍔", style=discord.ButtonStyle.success, custom_id="start_service")
    async def start_service(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.user
        role_id = SERVICE_ROLES.get(interaction.guild.id)
        if not role_id:
            await interaction.response.send_message("❌ Szerepkör nincs beállítva ehhez a szerverhez.", ephemeral=True)
            return
        role = interaction.guild.get_role(role_id)
        if role in member.roles:
            await interaction.response.send_message("❌ Már szolgálatban vagy.", ephemeral=True)
            return

        await member.add_roles(role)
        uid = str(member.id)
        duty_logs.setdefault(uid, {})
        duty_logs[uid]["start"] = time.time()
        save_logs()

        embed = discord.Embed(
            description=f"🟢 {member.mention} szolgálatba állt!",
            color=discord.Color.green()
        )
        await send_log(interaction.guild, embed)
        await interaction.response.send_message("🍔 Szolgálatba álltál!", ephemeral=True)

    @discord.ui.button(label="Szolgálat leadása", emoji="🍔", style=discord.ButtonStyle.danger, custom_id="stop_service")
    async def stop_service(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.user
        role_id = SERVICE_ROLES.get(interaction.guild.id)
        if not role_id:
            await interaction.response.send_message("❌ Szerepkör nincs beállítva ehhez a szerverhez.", ephemeral=True)
            return
        role = interaction.guild.get_role(role_id)
        if role not in member.roles:
            await interaction.response.send_message("❌ Nem vagy szolgálatban.", ephemeral=True)
            return

        await member.remove_roles(role)
        uid = str(member.id)
        if uid in duty_logs and "start" in duty_logs[uid]:
            worked = (time.time() - duty_logs[uid]["start"]) / 60
            duty_logs[uid]["total"] = duty_logs[uid].get("total", 0) + worked
            duty_logs[uid].pop("start")
            save_logs()
        else:
            worked = 0

        embed = discord.Embed(
            description=f"🛑 {member.mention} leadta a szolgálatot!\n⏱ {format_time(worked)}",
            color=discord.Color.orange()
        )
        await send_log(interaction.guild, embed)
        await interaction.response.send_message(f"🍔 Szolgálat leadva! {format_time(worked)}", ephemeral=True)

# ===== READY =====
@bot.event
async def on_ready():
    print("Bot online:", bot.user)
    bot.add_view(ServiceView())

# ===== REG =====
@bot.command()
async def reg(ctx, vezeteknev:str, keresztnev:str):
    try:
        new = f"{ctx.author.name} // {vezeteknev} {keresztnev}"
        await ctx.author.edit(nick=new)
        await ctx.send(f"✅ Neved átírva: {new}")
    except Exception as e:
        await ctx.send(f"Hiba: {e}")

# ===== PANEL PARANCS =====
@bot.command()
async def szolipanel(ctx):
    if not is_admin(ctx):
        await ctx.send("⛔ Admin jog kell")
        return

    embed = discord.Embed(
        title="🍔 Szolgálati Panel",
        description="Használd a gombokat",
        color=discord.Color.blurple()
    )
    await ctx.send(embed=embed, view=ServiceView())

# ===== LISTA =====
@bot.command(name="list")
async def list_all(ctx, action=None):
    if action != "all":
        await ctx.send("Használat: !list all")
        return

    user_times = []
    total = 0
    for uid, data in duty_logs.items():
        t = data.get("total", 0)
        if t > 0:
            try:
                member = await ctx.guild.fetch_member(int(uid))
                name = member.display_name
            except:
                name = uid
            user_times.append((name, t))
            total += t

    if not user_times:
        await ctx.send("Nincs adat")
        return

    desc = ""
    for i, (name, t) in enumerate(user_times, 1):
        desc += f"{i}. {name} - {format_time(t)}\n"

    embed = discord.Embed(
        title="Munkaidő lista",
        description=desc,
        color=discord.Color.blurple()
    )
    await ctx.send(embed=embed)
    await ctx.send(f"Összes idő: {format_time(total)}")

# ===== BOT START =====
bot.run(TOKEN)