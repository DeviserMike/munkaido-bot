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
    minutes = int(minutes)
    return f"{minutes//60}h {minutes%60}m"

def is_admin(ctx):
    return ctx.author.guild_permissions.administrator

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
        uid = str(member.id)
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
        uid = str(member.id)
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

# ===== SZOLIPANEL PARANCS =====
@bot.command()
async def szolipanel(ctx):
    # Szerepkör és log csatorna lekérése a guildből
    guild = ctx.guild
    role = discord.utils.get(guild.roles, name="Szolgálatban")  # vagy ID alapján: guild.get_role(ID)
    log_channel = discord.utils.get(guild.channels, name="log")  # vagy ID alapján
    if not role:
        await ctx.send("❌ Nincs Szolgálatban szerepkör beállítva ezen a szerveren!")
        return
    if not log_channel:
        await ctx.send("❌ Nincs log csatorna beállítva ezen a szerveren!")
        return

    embed = discord.Embed(title="🍔 Szolgálati Panel", description="Használd a gombokat", color=discord.Color.blurple())
    view = ServiceView(guild, role.id, log_channel.id)
    await ctx.send(embed=embed, view=view)

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
    embed = discord.Embed(title="Munkaidő lista", description=desc, color=discord.Color.blurple())
    await ctx.send(embed=embed)
    await ctx.send(f"Összes idő: {format_time(total)}")

bot.run(TOKEN)