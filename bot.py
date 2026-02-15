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
if not TOKEN:
    raise ValueError("DISCORD_TOKEN nincs beállítva!")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ===== SZOLGÁLATI BEÁLLÍTÁSOK =====
SERVICE_CHANNEL_ID = 1455619759340257300
SERVICE_ROLE_ID = 1472388518914428928
LOG_CHANNEL_ID = 1472403885246255175

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

# ===== SZOLGÁLATI PANEL VIEW =====
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

        uid = str(member.id)
        duty_logs.setdefault(uid, {})
        duty_logs[uid]["start"] = time.time()
        save_logs()

        log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(description=f"🟢 {member.mention} szolgálatba állt!", color=discord.Color.green())
            await log_channel.send(embed=embed)

        await interaction.response.send_message("🍔 Szolgálatba álltál!", ephemeral=True)

    @discord.ui.button(label="Szolgálat leadása", emoji="🍔", style=discord.ButtonStyle.danger, custom_id="stop_service")
    async def stop_service(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.user
        role = interaction.guild.get_role(SERVICE_ROLE_ID)
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

        log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(description=f"🛑 {member.mention} leadta a szolgálatot!\n⏱ Ledolgozott idő: {format_time(worked)}", color=discord.Color.orange())
            await log_channel.send(embed=embed)

        await interaction.response.send_message(f"🍔 Szolgálat leadva! Ledolgozott idő: {format_time(worked)}", ephemeral=True)

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
        await ctx.send("❌ Nem találom a csatornát.")
        return
    embed = discord.Embed(title="🍔 Szolgálati Panel", description="Nyomj a gombokra a szolgálat kezeléséhez:", color=discord.Color.blurple())
    await channel.send(embed=embed, view=ServiceView())
    await ctx.send("✅ Panel kirakva.")

# ===== SZOLGÁLATBAN LÉVŐK =====
@bot.command(name="szoli")
async def szoli(ctx):
    if not is_admin(ctx):
        await ctx.send("⛔ Admin jog kell.")
        return
    role = ctx.guild.get_role(SERVICE_ROLE_ID)
    embed = discord.Embed(title="🍔 Szolgálatban lévők", color=discord.Color.green())
    if not role or len(role.members) == 0:
        embed.description = "Senki nincs szolgálatban. Mindenki lusta g*ci..."
    else:
        for member in role.members:
            embed.add_field(name=member.display_name, value="Szolgálatban", inline=True)
    await ctx.send(embed=embed)

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
    embed = discord.Embed(description=f"➕ Hozzáadva: {member.mention} ({format_time(minutes)})", color=discord.Color.green())
    await ctx.send(embed=embed)

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
    embed = discord.Embed(description=f"➖ Levonva: {member.mention} ({format_time(minutes)})", color=discord.Color.red())
    await ctx.send(embed=embed)

# ===== LISTA ÉS FIZETÉS ÜZENET ALAPÚ PROMPT =====
@bot.command(name="list")
async def list_all(ctx, action: str = None):
    if action != "all":
        await ctx.send("Használat: `!list all`")
        return

    user_times = []
    total_worked = 0
    for uid, data in duty_logs.items():
        total = data.get("total", 0)
        if total > 0:
            try:
                member = await ctx.guild.fetch_member(int(uid))
                name = member.display_name
            except:
                name = f"User {uid}"
            user_times.append((name, total))
            total_worked += total

    if not user_times:
        await ctx.send("📋 Nincs rögzített munkaidő.")
        return

    embed = discord.Embed(title="📋 Munkaidő Lista", color=discord.Color.blurple())
    for idx, (name, total_minutes) in enumerate(user_times, start=1):
        embed.add_field(name=f"{idx}. {name}", value=format_time(total_minutes), inline=True)
    await ctx.send(embed=embed)

    # Üzenet prompt az órabérhez (csak admin)
    await ctx.send(f"{ctx.author.mention}, írd be a mai órabért $-ban (pl. 15):")

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        msg = await bot.wait_for("message", check=check, timeout=60)
        rate = float(msg.content)
    except:
        await ctx.send("⛔ Érvénytelen szám vagy lejárt az idő.")
        return

    payment_embed = discord.Embed(title="💵 Fizetés lista", color=discord.Color.gold())
    for name, total_minutes in user_times:
        hours = total_minutes / 60
        pay = round(hours * rate)
        payment_embed.add_field(name=name, value=f"${pay}", inline=True)
    payment_embed.set_footer(text=f"Összes ledolgozott idő: {format_time(total_worked)}")
    await ctx.send(embed=payment_embed)

# ===== FORCE KEZD / VEGE =====
@bot.command(name="forcekezd")
async def forcekezd(ctx, member: discord.Member):
    if not is_admin(ctx):
        await ctx.send("⛔ Admin jog kell.")
        return
    uid = str(member.id)
    duty_logs.setdefault(uid, {})
    if "start" in duty_logs[uid]:
        await ctx.send(f"❌ {member.mention} már műszakban van.")
        return
    duty_logs[uid]["start"] = time.time()
    save_logs()
    embed = discord.Embed(description=f"🟢 Admin elindította a műszakot: {member.mention}", color=discord.Color.green())
    await ctx.send(embed=embed)

@bot.command(name="forcevege")
async def forcevege(ctx, member: discord.Member = None, action: str = None):
    if not is_admin(ctx):
        await ctx.send("⛔ Admin jog kell.")
        return
    if action == "all":
        messages = []
        for uid, data in duty_logs.items():
            if "start" in data:
                member_id = int(uid)
                try:
                    member_obj = await ctx.guild.fetch_member(member_id)
                    worked = (time.time() - data["start"]) / 60
                    data["total"] = data.get("total", 0) + worked
                    data.pop("start")
                    messages.append(f"🛑 {member_obj.mention} műszak lezárva! Ledolgozott idő: {format_time(worked)}")
                except:
                    continue
        save_logs()
        await ctx.send("\n".join(messages) if messages else "Senki nincs műszakban.")
        return

    if not member:
        await ctx.send("Használat: `!forcevege @user` vagy `!forcevege all`")
        return

    uid = str(member.id)
    if uid not in duty_logs or "start" not in duty_logs[uid]:
        await ctx.send(f"❌ {member.mention} nincs aktív műszakban.")
        return

    worked = (time.time() - duty_logs[uid]["start"]) / 60
    duty_logs[uid]["total"] = duty_logs[uid].get("total", 0) + worked
    duty_logs[uid].pop("start")
    save_logs()
    embed = discord.Embed(description=f"🛑 Admin lezárta a műszakot: {member.mention}\n⏱ Ledolgozott idő: {format_time(worked)}", color=discord.Color.orange())
    await ctx.send(embed=embed)

# ===== BOT INDÍTÁS =====
bot.run(TOKEN)
