import os
import discord
from dotenv import load_dotenv
import ttsapi as api 
from discord import FFmpegPCMAudio, app_commands
import asyncio
from datetime import datetime, timedelta
import json

load_dotenv()

TOKEN = os.getenv('TOKEN')
daily_limit = 1250000  
max_message_length = 200 
disconnect_time = 2  # 2 seconds

usage_file = 'usage.json'

intents = discord.Intents.default() 
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

config_file_path = 'config.json'
# if os.path.exists(config_file_path):
#     with open(config_file_path, 'r') as file:
#         config_data = json.load(file)
# else:
#     config_data = {}

@client.event
async def on_guild_join(guild):
    await guild.system_channel.send("Hello! I am a TTS bot. You can use me to convert text to speech in the TTS channels. \n\n/settts - Set the TTS channel for your server. \n/help - get help regarding all commands \n/stop - stop the audio playback \n/limit - check the remaining character limit for the day \n/stop - stop a playing message midway \n/banfromtts - ban that irritating person from using the bot and spamming messages \n/unbanfromtts - unban banned people and let them use the bot \n/set-voice - change voice style of the bot \n/set-speech-rate - change the speech speed of the bot \n\nPlease note that the character limit is 1250000 characters per day across all servers.")
    
    guild_id = str(guild.id)
    
    new_guild_data = {
        "tts-channel-id": 000,
        "language-code": "en-IN",
        "name": "en-IN-Standard-C",
        "speech-rate": 1.0,
        "pitch": 0.0,
        "banned-user-ids": []
    }
    if os.path.exists(config_file_path):
        with open(config_file_path, 'r') as file:
            config_data = json.load(file)
    else:
        config_data = {}
    config_data[guild_id] = [new_guild_data]

    with open(config_file_path, 'w') as file:
        json.dump(config_data, file, indent=4)
    
def read_usage():
    if os.path.exists(usage_file):
        with open(usage_file, 'r') as file:
            data = json.load(file)
            return data.get('usage', 0)
    else:
        # Create the file with initial usage of 0 if it doesn't exist
        write_usage(0)
        return 0

def write_usage(usage):
    with open(usage_file, 'w') as file:
        json.dump({'usage': usage}, file)

usage = read_usage()

async def reset_usage():
    global usage
    while True:
        now = datetime.now()
        next_reset = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        sleep_time = (next_reset - now).total_seconds()
        await asyncio.sleep(sleep_time)
        usage = 0
        write_usage(usage)
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

@tree.command(
    name='sync', 
    description='Owner only'
)
async def sync(interaction: discord.Interaction):
    owner_ids = {909786287614099486, 691224924915761182}
    if interaction.user.id in owner_ids:
        await tree.sync()
        await interaction.response.send_message('Command tree synced.')
    else:
        await interaction.response.send_message('You must be the owner to use this command!')

@tree.command(
    name="help",
    description="Find instructions on how to use the bot here",
)
async def first_command(interaction):
    await interaction.response.send_message("Hello! I am a TTS bot. You can use me to convert text to speech in the TTS channels. \n\n/settts - Set the TTS channel for your server. \n/help - get help regarding all commands \n/stop - stop the audio playback \n/limit - check the remaining character limit for the day \n/stop - stop a playing message midway \n/banfromtts - ban that irritating person from using the bot and spamming messages \n/unbanfromtts - unban banned people and let them use the bot \n/set-voice - change voice style of the bot \n/set-speech-rate - change the speech speed of the bot \n\nPlease note that the character limit is 1250000 characters per day across all servers.")

@tree.command(
    name="stop",
    description="Stop playing audio"
)
async def stop(interaction: discord.Interaction):
    voice_client = discord.utils.get(client.voice_clients, guild=interaction.guild)
    
    if voice_client and voice_client.is_playing():
        voice_client.stop()
        await interaction.response.send_message("Stopped playing audio.", ephemeral=True)
    else:
        await interaction.response.send_message("Not currently playing audio.", ephemeral=True)

@tree.command(
    name="limit",
    description="Know the daily limit"
)
async def limit(interaction: discord.Interaction):
    remaining_limit = daily_limit - usage
    await interaction.response.send_message(f"Remaining character limit for today: {remaining_limit}")

@tree.command(
    name="settts",
    description="Set a TTS channel",
)
async def settts(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You must be an administrator to use this command.", ephemeral=True)
        return
    
    guild = interaction.guild
    channels = guild.text_channels
    
    select = discord.ui.Select(placeholder="Select a channel...", options=[
        discord.SelectOption(label=channel.name, value=str(channel.id)) for channel in channels
    ])

    async def wait_for_selection(interaction):
        selected_channel_id = int(select.values[0])
        channel = guild.get_channel(selected_channel_id)
        
        if channel:
            try:
                with open(config_file_path, 'r') as file:
                    config_data = json.load(file)
                
                if str(guild.id) not in config_data:
                    config_data[str(guild.id)] = [{"tts-channel-id": selected_channel_id}]
                else:
                    config_data[str(guild.id)][0]["tts-channel-id"] = selected_channel_id
                
                with open(config_file_path, 'w') as file:
                    json.dump(config_data, file, indent=4)

                selected_channel_id = int(select.values[0])
                selected_channel = guild.get_channel(selected_channel_id)
                await interaction.response.send_message(f"TTS channel set to {selected_channel.mention}", ephemeral=True)
                await selected_channel.send("This channel has been set for TTS!")
            except ValueError:
                await interaction.response.send_message("Invalid channel ID.", ephemeral=True)
        else:
            await interaction.response.send_message("Invalid channel selected.", ephemeral=True)

    select.callback = wait_for_selection

    view = discord.ui.View()
    view.add_item(select)

    await interaction.response.send_message("Select a channel to set for TTS:", view=view, ephemeral=True)

voice_dict = {
    "en-IN-Standard-A": "English-India A",
    "en-IN-Standard-B": "English-India B",
    "en-IN-Standard-C": "English-India C",
    "en-IN-Standard-D": "English-India D",
    "en-IN-Standard-E": "English-India E",
    "en-IN-Standard-F": "English-India F",
    "hi-IN-Standard-A": "Hindi A",
    "hi-IN-Standard-B": "Hindi B",
    "hi-IN-Standard-C": "Hindi C",
    "hi-IN-Standard-D": "Hindi D",
    "hi-IN-Standard-E": "Hindi E",
    "hi-IN-Standard-F": "Hindi F",
    "mr-IN-Standard-A": "Marathi A",
    "mr-IN-Standard-B": "Marathi B",
    "mr-IN-Standard-C": "Marathi C"
}

@tree.command(
    name="set-voice",
    description="Set the voice for the TTS",)
async def set_voice(interaction: discord.Interaction):
    guild = interaction.guild
    
    select = discord.ui.Select(placeholder="Select a voice...", options=[        
        discord.SelectOption(label="English-India A", value="en-IN-Standard-A"),
        discord.SelectOption(label="English-India B", value="en-IN-Standard-B"),
        discord.SelectOption(label="English-India C", value="en-IN-Standard-C"),
        discord.SelectOption(label="English-India D", value="en-IN-Standard-D"),
        discord.SelectOption(label="English-India E", value="en-IN-Standard-E"),
        discord.SelectOption(label="English-India F", value="en-IN-Standard-F"),
        discord.SelectOption(label="Hindi A", value="hi-IN-Standard-A"),
        discord.SelectOption(label="Hindi B", value="hi-IN-Standard-B"),
        discord.SelectOption(label="Hindi C", value="hi-IN-Standard-C"),
        discord.SelectOption(label="Hindi D", value="hi-IN-Standard-D"),
        discord.SelectOption(label="Hindi E", value="hi-IN-Standard-E"),
        discord.SelectOption(label="Hindi F", value="hi-IN-Standard-F"),
        discord.SelectOption(label="Marathi A", value="mr-IN-Standard-A"),
        discord.SelectOption(label="Marathi B", value="mr-IN-Standard-B"),
        discord.SelectOption(label="Marathi C", value="mr-IN-Standard-C")
        ])

    async def wait_for_selection(interaction):
        selected_voice = select.values[0]
        print(selected_voice)
        try:
            with open(config_file_path, 'r') as file:
                config_data = json.load(file)
            
            if str(guild.id) not in config_data:
                config_data[str(guild.id)] = [{"language-code": selected_voice[0:5]}]
                config_data[str(guild.id)][0]["name"] = selected_voice
            else:
                config_data[str(guild.id)][0]["language-code"] = selected_voice[0:5]
                config_data[str(guild.id)][0]["name"] = selected_voice
            
            with open(config_file_path, 'w') as file:
                json.dump(config_data, file, indent=4)

            await interaction.response.send_message(f"Voice set to "+voice_dict[selected_voice], ephemeral=True)
        except ValueError:
            await interaction.response.send_message("Invalid voice selected.", ephemeral=True)

    select.callback = wait_for_selection

    view = discord.ui.View()
    view.add_item(select)

    await interaction.response.send_message("Select a voice to set for TTS:", view=view, ephemeral=True)

@tree.command(
    name="set-speech-rate",
    description="Set the speech rate for the TTS",
)
async def set_speech_rate(interaction: discord.Interaction):
    guild=interaction.guild
    with open('config.json', 'r') as file:
                configData = json.load(file)
    currentSpeechRate = configData[str(guild.id)][0]["speech-rate"]
    select = discord.ui.Select(placeholder="Select a speech rate...", options=[
        discord.SelectOption(label="0.25", value="0.25"),
        discord.SelectOption(label="0.5", value="0.5"),
        discord.SelectOption(label="0.75", value="0.75"),
        discord.SelectOption(label="1.0", value="1.0"),
        discord.SelectOption(label="1.25", value="1.25"),
        discord.SelectOption(label="1.5", value="1.5"),
        discord.SelectOption(label="1.75", value="1.75"),
        discord.SelectOption(label="2.0", value="2.0"),
        discord.SelectOption(label="2.25", value="2.25"),
        discord.SelectOption(label="2.5", value="2.5"),
        discord.SelectOption(label="2.75", value="2.75"),
        discord.SelectOption(label="3.0", value="3.0"),
        discord.SelectOption(label="3.25", value="3.25"),
        discord.SelectOption(label="3.5", value="3.5"),
        discord.SelectOption(label="3.75", value="3.75"),
        discord.SelectOption(label="4.0", value="4.0")
    ])
    async def wait_for_selection(interaction):
        selected_speech_rate = float(select.values[0])
        try:
            with open(config_file_path, 'r') as file:
                config_data = json.load(file)
            
            if str(guild.id) not in config_data:
                config_data[str(guild.id)] = [{"speech-rate": selected_speech_rate}]
            else:
                config_data[str(guild.id)][0]["speech-rate"] = selected_speech_rate
            
            with open(config_file_path, 'w') as file:
                json.dump(config_data, file, indent=4)

            await interaction.response.send_message(f"Speech rate set to {selected_speech_rate}", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("Invalid speech rate selected.", ephemeral=True)
    
    select.callback = wait_for_selection

    view = discord.ui.View()
    view.add_item(select)

    await interaction.response.send_message("Select a speech rate to set for TTS:", view=view, ephemeral=True)

@tree.command(
    name="banfromtts",
    description="Ban a user from using the TTS bot",)
async def banfromtts(interaction: discord.Interaction):
    guild=interaction.guild
    with open('config.json', 'r') as file:
                configData = json.load(file)
    select = discord.ui.Select(placeholder="Select a user to ban...", options=[
        discord.SelectOption(label=member.name, value=str(member.id)) for member in guild.members
    ])
    async def wait_for_selection(interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You must be an administrator to use this command.", ephemeral=True)
            return
        selected_user_id = int(select.values[0])
        if "banned-user-ids" not in configData[str(guild.id)][0]:
            configData[str(guild.id)][0]["banned-user-ids"] = [selected_user_id]
        else:
            configData[str(guild.id)][0]["banned-user-ids"].append(selected_user_id)
        with open(config_file_path, 'w') as file:
            json.dump(configData, file, indent=4)
        await interaction.response.send_message(f"User banned from using TTS.", ephemeral=True)    
    select.callback = wait_for_selection

    view = discord.ui.View()
    view.add_item(select)
    await interaction.response.send_message("Select a user to ban from using TTS:", view=view, ephemeral=True)
@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    client.loop.create_task(reset_usage())
    client.loop.create_task(check_disconnect())
    await tree.sync()

@tree.command(
    name="unbanfromtts",
    description="Unban a user from using the TTS bot",)
async def unbanfromtts(interaction: discord.Interaction):
    guild=interaction.guild
    with open('config.json', 'r') as file:
                configData = json.load(file)
    banned_user_ids = configData[str(guild.id)][0]["banned-user-ids"]
    if banned_user_ids == []:
        await interaction.response.send_message("No users are currently banned from using TTS.", ephemeral=True)
        return
    select = discord.ui.Select(placeholder="Select a user to unban...", options=[
        discord.SelectOption(label=member.name, value=str(member.id)) for member in guild.members if member.id in banned_user_ids
    ])
    async def wait_for_selection(interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You must be an administrator to use this command.", ephemeral=True)
            return
        selected_user_id = int(select.values[0])
        configData[str(guild.id)][0]["banned-user-ids"].remove(selected_user_id)
        with open(config_file_path, 'w') as file:
            json.dump(configData, file, indent=4)
        await interaction.response.send_message(f"User unbanned from using TTS.", ephemeral=True)    
    select.callback = wait_for_selection

    view = discord.ui.View()
    view.add_item(select)
    await interaction.response.send_message("Select a user to unban from using TTS:", view=view, ephemeral=True)

@client.event
async def on_guild_remove(guild):
    with open(config_file_path, 'r') as file:
        config_data = json.load(file)
    guild_id = str(guild.id)
    config_data.pop(guild_id)
    with open(config_file_path, 'w') as file:
        json.dump(config_data, file, indent=4)


@client.event
async def on_message(message):
    global usage

    if message.author == client.user or not message.guild:
        return
    
    if message.content == '$help':
        await message.channel.send("Hello! I am a TTS bot. You can use me to convert text to speech in the TTS channels. \n\n/settts - Set the TTS channel for your server. \n/help - get help regarding all commands \n/stop - stop the audio playback \n/limit - check the remaining character limit for the day \n/stop - stop a playing message midway \n/banfromtts - ban that irritating person from using the bot and spamming messages \n/unbanfromtts - unban banned people and let them use the bot \n/set-voice - change voice style of the bot \n/set-speech-rate - change the speech speed of the bot \n\nPlease note that the character limit is 1250000 characters per day across all servers.")
        return

    if message.content.startswith('$setttschannel='):
        if not message.author.guild_permissions.administrator:
            await message.channel.send("You must be an administrator to use this command.")
            return
        channel_id = message.content.split('=')[1]
        try:
            channel = client.get_channel(int(channel_id))
            if channel:  
                with open(config_file_path, 'r') as file:
                    config_data = json.load(file)
                
                # Update the channel ID for the server
                config_data[str(message.guild.id)][0]["tts-channel-id"] = int(channel_id)
                
                # Save the updated JSON
                with open(config_file_path, 'w') as file:
                    json.dump(config_data, file)
                
                await message.channel.send(f"TTS channel set to {channel.mention}")
            else:
                await message.channel.send("Invalid channel ID.")
        except ValueError:
            await message.channel.send("Invalid channel ID.")

    if message.content == "$stop":
        voice_client = discord.utils.get(client.voice_clients, guild=message.guild)
        if voice_client and voice_client.is_playing():
            voice_client.stop()
            await message.channel.send("Stopped playing audio.")
        else:
            await message.channel.send("Not currently playing audio.")
        return  

    if message.content == "$limit":
        remaining_limit = daily_limit - usage
        await message.channel.send(f"Remaining character limit for today: {remaining_limit}")
        return

    with open('config.json', 'r') as file:
                config_data = json.load(file)         
    # Check if the server's ID is in the JSON and get the channel ID
    tts_channel_id = config_data[(str(message.guild.id))][0]["tts-channel-id"]

    # Check if the message is in a TTS channel before processing further
    if message.channel.id != tts_channel_id:
        return

    message_length = len(message.content)
    
    if message_length > max_message_length:
        await message.channel.send("Message is too long. Please limit your message to 200 characters.")
        return
    
    if usage + message_length > daily_limit:
        await message.channel.send("Daily character limit reached. Try again tomorrow.")
        return
    
    usage += message_length
    write_usage(usage)
    api.tts(message.content, message.guild.id)

    voice_client = discord.utils.get(client.voice_clients, guild=message.guild)
    
    if message.author.voice:
        vc = message.author.voice.channel
        if not voice_client:
            voice_client = await vc.connect()
        elif voice_client.channel != vc:
            await voice_client.move_to(vc)
        
        if os.path.exists("output.mp3"): 
            audio_source = FFmpegPCMAudio("output.mp3")
            if not voice_client.is_playing():
                voice_client.play(audio_source, after=lambda e: print('Player error: %s' % e) if e else None)
            else:
                await message.channel.send("Already playing audio. Please wait for the current audio to finish.")
        else:
            await message.channel.send("Audio file not found.")
    else:
        await message.channel.send("You are not in a voice channel.")

@client.event
async def on_voice_state_update(member, before, after):
    if member == client.user and before.channel and not after.channel:
        return

    if after.channel and client.user in [member for member in after.channel.members]:
        voice_client = discord.utils.get(client.voice_clients, guild=member.guild)
        if voice_client and len(after.channel.members) == 1:
            await voice_client.disconnect()
client.run(TOKEN)