import discord
import os
import time
import threading
from flask import Flask

# ======= FLASK KEEP-ALIVE =======
app = Flask("")

@app.route("/")
def home():
    return "Bot fut!"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# Flask külön szálon
threading.Thread(target=run_flask).start()

# ======= DISCORD BOT =======
TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("DISCORD_TOKEN nincs beállítva!")

intents = discord.Intents.default()
intents.members = True  # Szükséges a nick változtatáshoz
intents.messages = True
intents.guilds = True

client = discord.Client(intents=intents)

# Munkaidő log
duty_logs = {}

# ======= HELPER =======
def format_time(total_minutes):
    total_minutes = int(total_minutes)
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours}h {minutes}m"

# ======= BOT EVENTS =======
@client.event
async def on_ready():
    print(f"Bot csatlakozott: {client.user} ({client.user.id})")

@client.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.strip()

    # Teszt parancs
    if content == "!teszt":
        await message.channel.send(f"✅ Üzeneted látva: {message.author.mention}")
        return

    # Műszak kezdés
    if content == "!kezd":
        user_id = str(message.author.id)
        if user_id in duty_logs and "start" in duty_logs[user_id]:
            await message.channel.send("❌ Már aktív műszakban vagy.")
            return
        duty_logs.setdefault(user_id, {})
        duty_logs[user_id]["start"] = time.time()
        await message.channel.send(f"🟢 Műszak elkezdve: {message.author.mention}")
        return

    # Műszak vége
    if content == "!vege":
        user_id = str(message.author.id)
        if user_id not in duty_logs or "start" not in duty_logs[user_id]:
            await message.channel.send("❌ Nincs aktív műszakod.")
            return
        start_time = duty_logs[user_id]["start"]
        worked_minutes = (time.time() - start_time) / 60
        duty_logs[user_id].pop("start")
        duty_logs[user_id]["total"] = duty_logs[user_id].get("total", 0) + worked_minutes
        await message.channel.send(
            f"✅ Műszak lezárva: {message.author.mention}\n⏱ Ledolgozott idő: {int(worked_minutes)} perc"
        )
        return

    # Regisztráció
    if content.startswith("!reg "):
        parts = content.split()
        if len(parts) != 3:
            await message.channel.send("Használat: !reg vezetéknév keresztnév")
            return
        vezetek, kereszt = parts[1], parts[2]
        new_name = f"{message.author.display_name} // {vezetek} {kereszt}"
        try:
            await message.author.edit(nick=new_name)
            await message.channel.send(f"✅ Sikeres regisztráció! Új név: {new_name}")
        except:
            await message.channel.send("❌ Nem sikerült átnevezni. Ellenőrizd a bot engedélyeit.")
        return

    # Admin törlés
    if content == "!delete all":
        if not message.author.guild_permissions.administrator:
            await message.channel.send("⛔ Csak admin használhatja.")
            return
        duty_logs.clear()
        await message.channel.send("🧹 Minden felhasználó munkaideje törölve lett!")
        return

    # Munkaidő lista (admin csak)
    if content == "!list all":
        if not message.author.guild_permissions.administrator:
            await message.channel.send("⛔ Csak admin használhatja.")
            return

        if not duty_logs:
            await message.channel.send("📋 Nincs még rögzített munkaidő.")
            return

        msg = "📋 **Munkaidő lista:**\n"
        for uid, data in duty_logs.items():
            member_name = str(uid)
            try:
                member = await message.guild.fetch_member(int(uid))
                member_name = member.display_name
            except:
                pass
            total = int(data.get("total", 0))
            msg += f"- {member_name}: {total} perc\n"

        await message.channel.send(msg)
        return

# ======= BOT INDÍTÁS =======
client.run(TOKEN)
