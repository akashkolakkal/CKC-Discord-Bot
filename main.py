# bot.py
import os
from google.cloud import texttospeech
import discord
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('TOKEN')
tts_channel_id = 1254793464269504696

intents = discord.Intents.default() 
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')

@client.event
async def on_message(message):
    if message.author == client.user or not message.guild:
        return

    if message.channel.id == tts_channel_id :
        await message.channel.send('pong')

client.run(TOKEN)