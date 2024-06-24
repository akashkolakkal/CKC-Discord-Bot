# bot.py
import os
import discord
from dotenv import load_dotenv
import ttsapi as api
from discord import FFmpegPCMAudio


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
            if vc:
                voice_client = await vc.connect()
                # Create FFmpegPCMAudio instance and play it
                if os.path.exists("output.mp3"):  # Make sure the file exists
                    audio_source = FFmpegPCMAudio("output.mp3")
                    if not voice_client.is_playing():
                        voice_client.play(audio_source, after=lambda e: print('Player error: %s' % e) if e else None)
                    else:
                        await message.channel.send("Already playing audio.")
                else:
                    await message.channel.send("Audio file not found.")
            else:
                await message.channel.send("You are not in a voice channel.")
        else:
            await message.channel.send("You need to be in a voice channel to use this command.")

client.run(TOKEN)