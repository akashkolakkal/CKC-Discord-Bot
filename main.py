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
    if message.content == "$stop":
        voice_client = discord.utils.get(client.voice_clients, guild=message.guild)
        if voice_client and voice_client.is_playing():
            voice_client.stop()
            await message.channel.send("Stopped playing audio.")
        else:
            await message.channel.send("Not currently playing audio.")
        return  # Return to prevent further processing
    
    if message.channel.id == tts_channel_id:
        api.tts(message.content)
        # Check if the bot is already connected to a voice channel in the server
        voice_client = discord.utils.get(client.voice_clients, guild=message.guild)
        
        if message.author.voice:
            vc = message.author.voice.channel
            if not voice_client:
                voice_client = await vc.connect()
            elif voice_client.channel != vc:
                await voice_client.move_to(vc)
            
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

@client.event
async def on_voice_state_update(member, before, after):
    if member == client.user and before.channel and not after.channel:
        # This means the bot has left the voice channel, possibly to join another or disconnected.
        return

    # If the bot is the only member in the voice channel, disconnect.
    if after.channel and client.user in [member for member in after.channel.members]:
        voice_client = discord.utils.get(client.voice_clients, guild=member.guild)
        if voice_client and len(after.channel.members) == 1:  # Only the bot is in the channel
            await voice_client.disconnect()

client.run(TOKEN)