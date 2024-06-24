# bot.py
import os
from google.cloud import texttospeech
import discord
from dotenv import load_dotenv
import ttsapi as api

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

    if message.channel.id == tts_channel_id:
        api.tts(message.content)
        # Join the user's voice channel
        if message.author.voice:
            vc = message.author.voice.channel
            voice_client = await vc.connect()

            # Play the 'output.mp3' file
            voice_client.play(discord.FFmpegPCMAudio('output.mp3'), after=lambda e: print('done', e))

            # Wait for the audio to play before disconnecting
            while voice_client.is_playing():
                pass

            await voice_client.disconnect()
        else:
            await message.channel.send("You are not in a voice channel.")

client.run(TOKEN)