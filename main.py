import os
import discord
from dotenv import load_dotenv
import ttsapi as api 
from discord import FFmpegPCMAudio
import asyncio
from datetime import datetime, timedelta

load_dotenv()
TOKEN = os.getenv('TOKEN')
tts_channel_id = 1254793464269504696
daily_limit = 1250000  
usage = 0  
max_message_length = 50  
disconnect_time = 10  

intents = discord.Intents.default() 
intents.message_content = True
client = discord.Client(intents=intents)

async def reset_usage():
    global usage
    while True:
        now = datetime.now()
        next_reset = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        sleep_time = (next_reset - now).total_seconds()
        await asyncio.sleep(sleep_time)
        usage = 0
        print("Usage counter reset.")

async def check_disconnect():
    while True:
        await asyncio.sleep(10) 
        for voice_client in client.voice_clients:
            if len(voice_client.channel.members) == 1:  
                await asyncio.sleep(disconnect_time)
                if len(voice_client.channel.members) == 1:
                    await voice_client.disconnect()
                    print(f"Disconnected from {voice_client.channel} due to inactivity.")

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    client.loop.create_task(reset_usage())
    client.loop.create_task(check_disconnect())

@client.event
async def on_message(message):
    global usage

    if message.author == client.user or not message.guild:
        return

    if message.content == "$stop":
        voice_client = discord.utils.get(client.voice_clients, guild=message.guild)
        if voice_client and voice_client.is_playing():
            voice_client.stop()
            await message.channel.send("Stopped playing audio.")
        else:
            await message.channel.send("Not currently playing audio.")
        return  
    
    if message.channel.id == tts_channel_id:
        message_length = len(message.content)
        
        if message_length > max_message_length:
            await message.channel.send("Message is too long. Please limit your message to 50 characters.")
            return
        
        if usage + message_length > daily_limit:
            await message.channel.send("Daily character limit reached. Try again tomorrow.")
            return
        
        usage += message_length
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
            if os.path.exists("output.mp3"): 
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
