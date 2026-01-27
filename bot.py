import discord
import os
import time

TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("DISCORD_TOKEN nincs beállítva!")

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True  # Szükséges a nick változtatáshoz

client = discord.Client(intents=intents)

duty_logs = {}

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
        await message.channel.send(f"✅ Műszak lezárva: {message.author.mention}\n⏱ Ledolgozott idő: {int(worked_minutes)} perc")
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

client.run(TOKEN)
