import discord
from discord.ext import commands
import os
import time
import json
from math import ceil

# === TOKEN ===
TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("A DISCORD_TOKEN nincs beállítva!")

# === INTENTS ===
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # kell a !reg-hez, hogy módosítsa a nickeket
bot = commands.Bot(command_prefix='!', intents=intents)

# === JSON fájl a műszakokhoz ===
FILENAME = "duty_logs.json"
if os.path.exists(FILENAME):
    with open(FILENAME, "r") as f:
        duty_logs = json.load(f)
else:
    duty_logs = {}

def save_logs():
    with open(FILENAME, "w") as f:
        json.dump(duty_logs, f)

def format_time(total_minutes):
    total_minutes = int(total_minutes)
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours}h {minutes}m"

def is_admin(ctx):
    return ctx.author.guild_permissions.administrator

# === DEBUG: látott üzenetek logolása ===
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    print(f"Üzenet látva: {message.content} - {message.author}")
    await bot.process_commands(message)

# === PARANCSOK ===

# Teszt parancs
@bot.command()
async def teszt(ctx):
    await ctx.send("✅ Bot reagál!")

# Műszak kezdés
@bot.command()
async def kezd(ctx):
    user_id = str(ctx.author.id)
    if user_id in duty_logs and "start" in duty_logs[user_id]:
        await ctx.send("❌ Már aktív műszakban vagy.")
        return
    duty_logs.setdefault(user_id, {})
    duty_logs[user_id]["start"] = time.time()
    save_logs()
    await ctx.send(f"🟢 **Műszak elkezdve:** {ctx.author.mention}")

# Műszak lezárás
@bot.command()
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

# Munkaidő lekérdezés
@bot.command()
async def ido(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    user_id = str(member.id)
    total = duty_logs.get(user_id, {}).get("total", 0)
    await ctx.send(f"⏱ **{member.mention} összes munkaideje:** {format_time(total)}")

# Listázás (admin)
@bot.command()
async def list(ctx, action: str = None):
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

    items_per_page = 10
    total_pages = ceil(len(user_times) / items_per_page)
    current_page = 0

    def create_embed(page_num):
        start_idx = page_num * items_per_page
        end_idx = min(start_idx + items_per_page, len(user_times))
        page_users = user_times[start_idx:end_idx]

        embed = discord.Embed(
            title="📋 Munkaidő Lista",
            description=f"**Összes felhasználó:** {len(user_times)}\n**Oldal:** {page_num + 1}/{total_pages}",
            color=discord.Color.blue()
        )

        description_text = ""
        for idx, (name, total_minutes) in enumerate(page_users, start=start_idx + 1):
            description_text += f"**{idx}.** {name} - `{format_time(total_minutes)}`\n"

        embed.description += f"\n\n{description_text}"
        embed.set_footer(text="Használd a ⬅️ ➡️ reakciókat az oldalak közötti váltáshoz")
        return embed

    message = await ctx.send(embed=create_embed(current_page))
    await message.add_reaction("⬅️")
    await message.add_reaction("➡️")

    def check(reaction, user):
        return (
            user == ctx.author
            and reaction.message.id == message.id
            and str(reaction.emoji) in ["⬅️", "➡️"]
        )

    while True:
        try:
            reaction, user = await bot.wait_for("reaction_add", timeout=60.0, check=check)
            if str(reaction.emoji) == "➡️" and current_page < total_pages - 1:
                current_page += 1
                await message.edit(embed=create_embed(current_page))
            elif str(reaction.emoji) == "⬅️" and current_page > 0:
                current_page -= 1
                await message.edit(embed=create_embed(current_page))
            await reaction.remove(user)
        except:
            try:
                await message.clear_reactions()
            except:
                pass
            break

# Delete all (admin)
@bot.command()
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

# Regisztráció (nick változtatás)
@bot.command()
async def reg(ctx, vezeteknev: str, keresztnev: str):
    # Adminok többször is használhatják
    nickname = f"{ctx.author.name} // {vezeteknev} {keresztnev}"
    try:
        await ctx.author.edit(nick=nickname)
        await ctx.send(f"✅ **Nick megváltoztatva:** {nickname}")
    except discord.Forbidden:
        await ctx.send("⛔ A botnak nincs jog a nick módosításához.")

# === BOT INDÍTÁS ===
bot.run(TOKEN)
