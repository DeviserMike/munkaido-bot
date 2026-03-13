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

# ===== JSON FILES =====
DUTY_FILE = "duty_logs.json"
CONFIG_FILE = "guild_config.json"

if os.path.exists(DUTY_FILE):
    with open(DUTY_FILE, "r") as f:
        duty_logs = json.load(f)
else:
    duty_logs = {}

if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r") as f:
        GUILDS = json.load(f)
else:
    GUILDS = {}

def save_logs():
    with open(DUTY_FILE,"w") as f:
        json.dump(duty_logs,f)

def save_config():
    with open(CONFIG_FILE, "w") as f:
        json.dump(GUILDS, f)

def format_time(minutes):
    minutes = int(minutes)
    return f"{minutes//60}h {minutes%60}m"

# ===== PANEL VIEW =====
class ServiceView(discord.ui.View):
    def __init__(self, guild, role_id, log_channel_id):
        super().__init__(timeout=None)
        self.guild = guild
        self.role_id = role_id
        self.log_channel_id = log_channel_id

    async def _send_log(self, embed):
        channel = self.guild.get_channel(self.log_channel_id)
        if channel:
            await channel.send(embed=embed)

    async def _check_guild(self, interaction):
        if interaction.guild != self.guild:
            await interaction.response.send_message("❌ Ez a gomb nem érvényes itt.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Szolgálatba áll", emoji="🍔", style=discord.ButtonStyle.success)
    async def start_service(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._check_guild(interaction):
            return
        member = interaction.user
        role = interaction.guild.get_role(self.role_id)
        if role in member.roles:
            await interaction.response.send_message("❌ Már szolgálatban vagy.", ephemeral=True)
            return
        await member.add_roles(role)

        uid = f"{interaction.guild.id}_{member.id}"
        duty_logs.setdefault(uid, {})["start"] = time.time()
        save_logs()

        embed = discord.Embed(description=f"🟢 {member.mention} szolgálatba állt!", color=discord.Color.green())
        await self._send_log(embed)
        await interaction.response.send_message("🍔 Szolgálatba álltál!", ephemeral=True)

    @discord.ui.button(label="Szolgálat leadása", emoji="🍔", style=discord.ButtonStyle.danger)
    async def stop_service(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._check_guild(interaction):
            return
        member = interaction.user
        role = interaction.guild.get_role(self.role_id)
        if role not in member.roles:
            await interaction.response.send_message("❌ Nem vagy szolgálatban.", ephemeral=True)
            return
        await member.remove_roles(role)

        uid = f"{interaction.guild.id}_{member.id}"
        worked = 0
        if uid in duty_logs and "start" in duty_logs[uid]:
            worked = (time.time() - duty_logs[uid].pop("start")) / 60
            duty_logs[uid]["total"] = duty_logs[uid].get("total", 0) + worked
            save_logs()

        embed = discord.Embed(description=f"🛑 {member.mention} leadta a szolgálatot!\n⏱ {format_time(worked)}", color=discord.Color.orange())
        await self._send_log(embed)
        await interaction.response.send_message(f"🍔 Szolgálat leadva! {format_time(worked)}", ephemeral=True)

# ===== READY =====
@bot.event
async def on_ready():
    print("Bot online:", bot.user)

# ===== GUILD CONFIG PARANCS =====
@bot.command()
async def config(ctx, log_channel: discord.TextChannel, role: discord.Role):
    # Csak adminok használhatják
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ Ehhez a parancshoz admin jogosultság kell.")
        return

    GUILDS[ctx.guild.id] = {
        "log_channel": log_channel.id,
        "service_role": role.id
    }
    save_config()
    await ctx.send(f"✅ Konfigurálva a guild: {ctx.guild.name}\nLog csatorna: {log_channel.mention}\nSzerepkör: {role.mention}")

# ===== SZOLIPANEL PARANCS =====
@bot.command()
async def szolipanel(ctx):
    config = GUILDS.get(ctx.guild.id)
    if not config:
        await ctx.send("❌ Ez a guild nincs konfigurálva a bot számára! Használd az `!config` parancsot.")
        return

    role_id = config["service_role"]
    log_channel_id = config["log_channel"]

    # 🔹 Megkeressük a "🕒munkaidő" nevű csatornát a guildban
    target_channel = discord.utils.get(ctx.guild.text_channels, name="🕒munkaidő")
    if not target_channel:
        await ctx.send("❌ Nem található a 🕒munkaidő csatorna!")
        return

    embed = discord.Embed(title="🍔 Szolgálati Panel", description="Használd a gombokat", color=discord.Color.blurple())
    view = ServiceView(ctx.guild, role_id, log_channel_id)
    await target_channel.send(embed=embed, view=view)  # 🔹 ide küldjük a panelt
# ===== LISTA =====
@bot.command(name="list")
async def list_all(ctx, action=None):
    if action != "all":
        await ctx.send("Használat: !list all")
        return
    user_times = []
    total = 0
    for uid, data in duty_logs.items():
        guild_id, user_id = uid.split("_")
        if int(guild_id) != ctx.guild.id:
            continue
        t = data.get("total", 0)
        if t > 0:
            try:
                member = await ctx.guild.fetch_member(int(user_id))
                name = member.display_name
            except:
                name = user_id
            user_times.append((name, t))
            total += t
    if not user_times:
        await ctx.send("Nincs adat")
        return
    desc = ""
    for i, (name, t) in enumerate(user_times, 1):
        desc += f"{i}. {name} - {format_time(t)}\n"
    embed = discord.Embed(title="Munkaidő lista", description=desc, color=discord.Color.blurple())
    await ctx.send(embed=embed)
    await ctx.send(f"Összes idő: {format_time(total)}")

bot.run(TOKEN)