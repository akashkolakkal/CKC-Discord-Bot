import os
import discord
from dotenv import load_dotenv
import ttsapi as api 
from discord import FFmpegPCMAudio, app_commands
import asyncio
from datetime import datetime, timedelta
import json
import logging
from logging.handlers import RotatingFileHandler
import aiohttp

load_dotenv()

TOKEN = os.getenv('TOKEN')
DISCORD_LOG_WEBHOOK = os.getenv('DISCORD_LOG_WEBHOOK')

# Configure logging
log_file = 'bot.log'
max_log_size = 5 * 1024 * 1024  # 5MB
backup_count = 3

logger = logging.getLogger('CKCBot')
logger.setLevel(logging.DEBUG)

# File handler with rotation
file_handler = RotatingFileHandler(log_file, maxBytes=max_log_size, backupCount=backup_count)
file_handler.setLevel(logging.DEBUG)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
                             datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)
import sys, threading

# Capture warnings emitted via the `warnings` module
logging.captureWarnings(True)

# Global uncaught exception handler for the main thread
def _handle_uncaught(exc_type, exc_value, exc_tb):
    logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_tb))

sys.excepthook = _handle_uncaught

# Thread exception handler (Python 3.8+)
def _thread_excepthook(args):
    logger.error("Uncaught thread exception", exc_info=(args.exc_type, args.exc_value, args.exc_traceback))

try:
    threading.excepthook = _thread_excepthook
except AttributeError:
    # Older Python versions may not expose threading.excepthook
    pass

# Asyncio loop-level exception handler
def _asyncio_exception_handler(loop, context):
    exc = context.get('exception')
    if exc:
        logger.error("Asyncio exception caught", exc_info=(type(exc), exc, exc.__traceback__))
    else:
        logger.error("Asyncio context error: %s", context.get('message'))

asyncio.get_event_loop().set_exception_handler(_asyncio_exception_handler)

def _log_task_exceptions(task: asyncio.Task):
    if task.cancelled():
        return
    try:
        exc = task.exception()
    except asyncio.CancelledError:
        return
    if exc:
        logger.error("Unhandled task exception", exc_info=(type(exc), exc, exc.__traceback__))

# Voice connection state tracking per guild (fixes WebSocket 4006 race condition)
# States: "idle" (not connected), "connecting" (handshake in progress), "playing" (audio playing)
voice_connection_states = {}  # {guild_id: {"state": str, "last_activity": datetime}}
VOICE_STATE_IDLE = "idle"
VOICE_STATE_CONNECTING = "connecting"
VOICE_STATE_PLAYING = "playing"
INACTIVITY_TIMEOUT = 30  # Increased from 2 seconds; allows 3-5s cloud handshake + buffer

def get_voice_state(guild_id):
    """Get voice state for a guild, defaulting to idle."""
    return voice_connection_states.get(guild_id, {
        "state": VOICE_STATE_IDLE,
        "last_activity": datetime.now()
    })

def set_voice_state(guild_id, state):
    """Set voice state for a guild with timestamp."""
    voice_connection_states[guild_id] = {
        "state": state,
        "last_activity": datetime.now()
    }

async def safe_disconnect_after_playback(guild_id, voice_client):
    """Safely disconnect after playback finishes using inactivity timer.
    Prevents disconnects during handshake and honors cloud latency (3-5s).
    """
    try:
        logger.debug(f"Playback finished for guild {guild_id}, starting {INACTIVITY_TIMEOUT}s inactivity timer")
        set_voice_state(guild_id, VOICE_STATE_IDLE)
        
        # Wait for inactivity timeout
        await asyncio.sleep(INACTIVITY_TIMEOUT)
        
        # Check if still idle (no new audio started during timeout)
        current_state = get_voice_state(guild_id)
        if current_state.get("state") == VOICE_STATE_IDLE and voice_client and voice_client.is_connected():
            logger.info(f"Disconnecting from {voice_client.channel} in {voice_client.guild.name} after {INACTIVITY_TIMEOUT}s inactivity")
            await voice_client.disconnect()
            voice_connection_states.pop(guild_id, None)
        else:
            logger.debug(f"Voice activity resumed for guild {guild_id}, aborting auto-disconnect")
    except Exception as e:
        logger.error(f"Error in safe_disconnect_after_playback for guild {guild_id}: {str(e)}", exc_info=True)

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

@client.event
async def on_guild_join(guild):
    try:
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
        
        logger.info(f"Bot joined guild {guild.name} (ID: {guild_id}). Config initialized.")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse config.json on guild join for {guild.name}: {str(e)}", exc_info=True)
    except Exception as e:
        logger.error(f"Error on guild join event for {guild.name}: {str(e)}", exc_info=True)
    
def read_usage():
    try:
        if os.path.exists(usage_file):
            with open(usage_file, 'r') as file:
                data = json.load(file)
                return data.get('usage', 0)
        else:
            # Create the file with initial usage of 0 if it doesn't exist
            write_usage(0)
            return 0
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse usage.json: {str(e)}", exc_info=True)
        write_usage(0)
        return 0
    except Exception as e:
        logger.error(f"Error reading usage file: {str(e)}", exc_info=True)
        return 0

def write_usage(usage):
    try:
        with open(usage_file, 'w') as file:
            json.dump({'usage': usage}, file)
    except Exception as e:
        logger.error(f"Error writing to usage file: {str(e)}", exc_info=True)

usage = read_usage()

async def send_critical_logs_to_discord():
    """Send critical logs to Discord webhook every 24 hours and clear log file."""
    global logger
    await asyncio.sleep(60)  # Wait 60 seconds before first run to ensure bot is ready
    
    while True:
        try:
            await asyncio.sleep(86400)  # 24 hours
            
            logger.debug("Webhook task triggered: checking conditions for log send")
            
            # Validate webhook URL
            if not DISCORD_LOG_WEBHOOK:
                logger.warning("Webhook task: DISCORD_LOG_WEBHOOK env var is not set or empty")
                continue
            
            # Validate log file exists
            if not os.path.exists(log_file):
                logger.warning(f"Webhook task: log file '{log_file}' does not exist")
                continue
            
            logger.debug(f"Webhook task: reading from {log_file}")
            
            # Read log file
            with open(log_file, 'r') as f:
                log_contents = f.read()
            
            log_size = len(log_contents)
            logger.debug(f"Webhook task: log file size is {log_size} bytes")
            
            # Filter for CRITICAL logs only
            critical_logs = [line for line in log_contents.split('\n') if 'CRITICAL' in line]
            critical_count = len(critical_logs)
            logger.debug(f"Webhook task: found {critical_count} CRITICAL log lines")
            
            if not critical_logs:
                logger.info("Webhook task: no CRITICAL logs found, skipping webhook send")
            else:
                # Format message for Discord (max 2000 chars per message)
                critical_text = '\n'.join(critical_logs[-20:])  # Last 20 critical logs
                if len(critical_text) > 1900:
                    critical_text = critical_text[-1900:]
                
                message = f"```\n🚨 CRITICAL LOGS FROM LAST 24 HOURS\n\n{critical_text}\n```"
                logger.debug(f"Webhook task: formatted message length {len(message)} chars")
                
                # Send to webhook
                logger.debug(f"Webhook task: posting to webhook URL (first 30 chars): {DISCORD_LOG_WEBHOOK[:30]}...")
                async with aiohttp.ClientSession() as session:
                    webhook_data = {
                        'content': message,
                        'username': 'CKC Bot Logger'
                    }
                    try:
                        async with session.post(DISCORD_LOG_WEBHOOK, json=webhook_data, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                            if resp.status in [200, 204]:
                                logger.info(f"Critical logs sent to Discord webhook successfully (status {resp.status})")
                            else:
                                logger.error(f"Webhook request failed with status {resp.status}")
                                response_text = await resp.text()
                                logger.error(f"Webhook response: {response_text[:200]}")
                    except asyncio.TimeoutError:
                        logger.error("Webhook request timed out after 10 seconds")
                    except aiohttp.ClientConnectorError as e:
                        logger.error(f"Webhook connection error (network/DNS issue): {str(e)}")
                    except Exception as e:
                        logger.error(f"Failed to send logs to webhook: {str(e)}", exc_info=True)
            
            # Clear the log file
            logger.debug("Webhook task: clearing log file")
            with open(log_file, 'w') as f:
                f.write("")
            logger.info("Log file cleared after webhook task cycle")
            
        except Exception as e:
            logger.error(f"Error in send_critical_logs_to_discord: {str(e)}", exc_info=True)

async def reset_usage():
    global usage
    while True:
        now = datetime.now()
        next_reset = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        sleep_time = (next_reset - now).total_seconds()
        await asyncio.sleep(sleep_time)
        usage = 0
        write_usage(usage)
        logger.info("Usage counter reset.")

async def check_disconnect():
    """Monitor voice connections and disconnect only when safe.
    Never disconnects during connecting/playing states or while audio is playing.
    Uses inactivity timeout to prevent race conditions with voice handshake.
    """
    while True:
        try:
            await asyncio.sleep(15)  # Check every 15 seconds
            
            for voice_client in client.voice_clients:
                guild_id = voice_client.guild.id
                state = get_voice_state(guild_id)
                
                # NEVER disconnect if connecting or playing
                if state.get("state") in [VOICE_STATE_CONNECTING, VOICE_STATE_PLAYING]:
                    logger.debug(f"Guild {guild_id} is {state.get('state')}, skipping disconnect check")
                    continue
                
                # NEVER disconnect if audio is currently playing
                if voice_client.is_playing():
                    logger.debug(f"Guild {guild_id} is playing audio, updating state")
                    set_voice_state(guild_id, VOICE_STATE_PLAYING)
                    continue
                
                # Disconnect only if idle and bot is alone, respecting inactivity timeout
                if len(voice_client.channel.members) == 1:
                    time_since_activity = (datetime.now() - state.get("last_activity", datetime.now())).total_seconds()
                    
                    if time_since_activity >= INACTIVITY_TIMEOUT:
                        logger.info(f"Disconnecting from {voice_client.channel} in {voice_client.guild.name} due to {time_since_activity:.1f}s inactivity")
                        try:
                            await voice_client.disconnect()
                            voice_connection_states.pop(guild_id, None)
                        except Exception as e:
                            logger.error(f"Error disconnecting from guild {guild_id}: {str(e)}", exc_info=True)
                    else:
                        logger.debug(f"Guild {guild_id}: inactivity timer {time_since_activity:.1f}s / {INACTIVITY_TIMEOUT}s")
        except Exception as e:
            logger.error(f"Error in check_disconnect loop: {str(e)}", exc_info=True)

@tree.command(
    name='get-config',
    description='get the config information for this server'
)
async def get_config(interaction: discord.Interaction):
    with open(config_file_path, 'r') as file:
        config_data = json.load(file)
    guild_id = str(interaction.guild.id)
    tts_channel_id = config_data[guild_id][0]["tts-channel-id"]
    tts_channel = interaction.guild.get_channel(tts_channel_id)
    language = voice_dict[config_data[guild_id][0]["name"]]
    speech_rate = config_data[guild_id][0]["speech-rate"]
    banned_user_ids = config_data[guild_id][0]["banned-user-ids"]
    banned_users = [interaction.guild.get_member(user_id).name for user_id in banned_user_ids]
    if guild_id in config_data:
        await interaction.response.send_message("The server data for CKC is:", ephemeral=True)
        await interaction.channel.send(f"TTS Channel : {tts_channel} \nVoice : {language} \nSpeech Rate : {speech_rate} \nBanned Users : {banned_users}")
    else:
        await interaction.response.send_message("No config data found for this server.", ephemeral=True)


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
                logger.info(f"TTS channel set to {selected_channel.name} in {guild.name} by {interaction.user}")
                await interaction.response.send_message(f"TTS channel set to {selected_channel.mention}", ephemeral=True)
                await selected_channel.send("This channel has been set for TTS!")
            except ValueError as e:
                logger.error(f"ValueError when setting TTS channel: {str(e)}")
                await interaction.response.send_message("Invalid channel ID.", ephemeral=True)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse config.json when setting TTS channel: {str(e)}", exc_info=True)
                await interaction.response.send_message("Error reading configuration. Please try again.", ephemeral=True)
            except Exception as e:
                logger.error(f"Error setting TTS channel: {str(e)}", exc_info=True)
                await interaction.response.send_message("An error occurred. Please try again.", ephemeral=True)
        else:
            logger.warning(f"Invalid channel ID selected: {selected_channel_id} in {guild.name}")
            await interaction.response.send_message("Invalid channel selected.", ephemeral=True)

    select.callback = wait_for_selection

    view = discord.ui.View()
    view.add_item(select)

    await interaction.response.send_message("Select a channel to set for TTS:", view=view, ephemeral=True)



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
        logger.debug(f"Voice selected: {selected_voice}")
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

            logger.info(f"Voice set to {voice_dict[selected_voice]} in {guild.name} by {interaction.user}")
            await interaction.response.send_message(f"Voice set to "+voice_dict[selected_voice], ephemeral=True)
        except ValueError as e:
            logger.error(f"ValueError when setting voice: {str(e)}")
            await interaction.response.send_message("Invalid voice selected.", ephemeral=True)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse config.json when setting voice: {str(e)}", exc_info=True)
            await interaction.response.send_message("Error reading configuration. Please try again.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error setting voice: {str(e)}", exc_info=True)
            await interaction.response.send_message("An error occurred. Please try again.", ephemeral=True)

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

            logger.info(f"Speech rate set to {selected_speech_rate} in {guild.name} by {interaction.user}")
            await interaction.response.send_message(f"Speech rate set to {selected_speech_rate}", ephemeral=True)
        except ValueError as e:
            logger.error(f"ValueError when setting speech rate: {str(e)}")
            await interaction.response.send_message("Invalid speech rate selected.", ephemeral=True)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse config.json when setting speech rate: {str(e)}", exc_info=True)
            await interaction.response.send_message("Error reading configuration. Please try again.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error setting speech rate: {str(e)}", exc_info=True)
            await interaction.response.send_message("An error occurred. Please try again.", ephemeral=True)
    
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
            logger.warning(f"Non-admin user {interaction.user} attempted to ban from TTS in {guild.name}")
            await interaction.response.send_message("You must be an administrator to use this command.", ephemeral=True)
            return
        selected_user_id = int(select.values[0])
        try:
            selected_user = guild.get_member(selected_user_id)
            if "banned-user-ids" not in configData[str(guild.id)][0]:
                configData[str(guild.id)][0]["banned-user-ids"] = [selected_user_id]
            else:
                configData[str(guild.id)][0]["banned-user-ids"].append(selected_user_id)
            with open(config_file_path, 'w') as file:
                json.dump(configData, file, indent=4)
            logger.warning(f"User {selected_user.name} (ID: {selected_user_id}) banned from TTS in {guild.name} by {interaction.user}")
            await interaction.response.send_message(f"User banned from using TTS.", ephemeral=True)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse config.json when banning user: {str(e)}", exc_info=True)
            await interaction.response.send_message("Error reading configuration. Please try again.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error banning user: {str(e)}", exc_info=True)
            await interaction.response.send_message("An error occurred. Please try again.", ephemeral=True)    
    select.callback = wait_for_selection

    view = discord.ui.View()
    view.add_item(select)
    await interaction.response.send_message("Select a user to ban from using TTS:", view=view, ephemeral=True)
@client.event
async def on_ready():
    logger.info(f'{client.user} has connected to Discord!')
    t1 = client.loop.create_task(reset_usage())
    t1.add_done_callback(_log_task_exceptions)
    t2 = client.loop.create_task(check_disconnect())
    t2.add_done_callback(_log_task_exceptions)
    t3 = client.loop.create_task(send_critical_logs_to_discord())
    t3.add_done_callback(_log_task_exceptions)
    await tree.sync()
    logger.info("All background tasks started and command tree synced.")

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
            logger.warning(f"Non-admin user {interaction.user} attempted to unban from TTS in {guild.name}")
            await interaction.response.send_message("You must be an administrator to use this command.", ephemeral=True)
            return
        selected_user_id = int(select.values[0])
        try:
            selected_user = guild.get_member(selected_user_id)
            configData[str(guild.id)][0]["banned-user-ids"].remove(selected_user_id)
            with open(config_file_path, 'w') as file:
                json.dump(configData, file, indent=4)
            logger.info(f"User {selected_user.name} (ID: {selected_user_id}) unbanned from TTS in {guild.name} by {interaction.user}")
            await interaction.response.send_message(f"User unbanned from using TTS.", ephemeral=True)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse config.json when unbanning user: {str(e)}", exc_info=True)
            await interaction.response.send_message("Error reading configuration. Please try again.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error unbanning user: {str(e)}", exc_info=True)
            await interaction.response.send_message("An error occurred. Please try again.", ephemeral=True)    
    select.callback = wait_for_selection

    view = discord.ui.View()
    view.add_item(select)
    await interaction.response.send_message("Select a user to unban from using TTS:", view=view, ephemeral=True)

@client.event
async def on_guild_remove(guild):
    try:
        with open(config_file_path, 'r') as file:
            config_data = json.load(file)
        guild_id = str(guild.id)
        config_data.pop(guild_id, None)
        with open(config_file_path, 'w') as file:
            json.dump(config_data, file, indent=4)
        logger.info(f"Bot removed from guild {guild.name} (ID: {guild_id}). Config cleaned up.")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse config.json on guild remove for {guild.name}: {str(e)}", exc_info=True)
    except Exception as e:
        logger.error(f"Error on guild remove event for {guild.name}: {str(e)}", exc_info=True)


@client.event
async def on_message(message):
    global usage

    if message.author == client.user or not message.guild:
        return
    
    logger.debug(f"Message received from {message.author} in {message.guild.name}: {message.content[:50]}")
    
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
        logger.debug(f"Message from {message.author} not in TTS channel, ignoring")
        return

    banned_user_ids = config_data[(str(message.guild.id))][0]["banned-user-ids"]
    if message.author.id in banned_user_ids:
        logger.warning(f"Banned user {message.author} (ID: {message.author.id}) attempted to use TTS in {message.guild.name}")
        await message.channel.send("You have been banned from using the TTS bot.")
        return

    message_length = len(message.content)
    
    if message_length > max_message_length:
        logger.warning(f"Message from {message.author} in {message.guild.name} exceeded length limit ({message_length} > {max_message_length})")
        await message.channel.send("Message is too long. Please limit your message to 200 characters.")
        return
    
    if usage + message_length > daily_limit:
        logger.warning(f"Daily character limit reached in {message.guild.name}. Current usage: {usage}, requested: {message_length}")
        await message.channel.send("Daily character limit reached. Try again tomorrow.")
        return
    
    usage += message_length
    write_usage(usage)
    logger.info(f"TTS synthesis requested by {message.author} in {message.guild.name}. Characters: {message_length}, Total usage: {usage}")
    content = message.content
    for user in message.mentions:
        content = content.replace(f'<@{user.id}>', user.name)
    
    # Call TTS API with error handling
    try:
        api.tts(content, message.guild.id)
    except ValueError as e:
        logger.error(f"Invalid TTS request from {message.author} in {message.guild.name}: {str(e)}")
        await message.channel.send("Error: Invalid TTS request. Please check the configuration.")
        return
    except KeyError as e:
        logger.error(f"Guild configuration missing for {message.guild.name}: {str(e)}")
        await message.channel.send("Error: Guild not properly configured. Please run /settts first.")
        return
    except Exception as e:
        logger.error(f"TTS API error for {message.author} in {message.guild.name}: {str(e)}", exc_info=True)
        await message.channel.send("Error: Failed to generate TTS audio. Please try again later.")
        return

    voice_client = discord.utils.get(client.voice_clients, guild=message.guild)
    
    if message.author.voice:
        vc = message.author.voice.channel
        
        # Only connect if not already connected; prevent concurrent connects
        if not voice_client:
            set_voice_state(message.guild.id, VOICE_STATE_CONNECTING)
            try:
                voice_client = await asyncio.wait_for(vc.connect(), timeout=10.0)
                logger.debug(f"Successfully connected to {vc.name} in {message.guild.name}")
                # Wait for voice handshake to fully complete (especially important on cloud VMs with 3-5s latency)
                logger.debug("Waiting for voice handshake to complete (up to 10s)...")
                deadline = asyncio.get_event_loop().time() + 10.0
                while not voice_client.is_connected():
                    if asyncio.get_event_loop().time() > deadline:
                        logger.error(f"Voice connection did not become ready within timeout for {vc.name}")
                        await message.channel.send("Error: Voice connection timed out. Please try again.")
                        set_voice_state(message.guild.id, VOICE_STATE_IDLE)
                        return
                    await asyncio.sleep(0.5)
                logger.debug("Voice handshake complete, proceeding to playback")
            except asyncio.TimeoutError:
                logger.error(f"Voice connection timeout to {vc.name} in {message.guild.name}")
                await message.channel.send("Error: Voice connection timed out. Please try again.")
                set_voice_state(message.guild.id, VOICE_STATE_IDLE)
                return
            except Exception as e:
                logger.error(f"Failed to connect to voice channel {vc.name}: {str(e)}", exc_info=True)
                await message.channel.send("Error: Failed to connect to voice channel.")
                set_voice_state(message.guild.id, VOICE_STATE_IDLE)
                return
        elif voice_client.channel != vc:
            # Move to different channel
            try:
                await voice_client.move_to(vc)
                logger.debug(f"Moved bot to {vc.name} in {message.guild.name}")
            except Exception as e:
                logger.error(f"Failed to move to voice channel {vc.name}: {str(e)}", exc_info=True)
                await message.channel.send("Error: Failed to move to voice channel.")
                return
        
        # Play audio only after connection is fully established
        if os.path.exists("messageOutput/output.mp3"):
            if not voice_client.is_playing():
                try:
                    set_voice_state(message.guild.id, VOICE_STATE_PLAYING)
                    audio_source = FFmpegPCMAudio("messageOutput/output.mp3")
                    
                    # Safe disconnect callback using asyncio.run_coroutine_threadsafe
                    # Ensures disconnect respects inactivity timeout and doesn't interrupt handshake
                    def on_playback_finish(error):
                        if error:
                            logger.error(f"Player error: {error}")
                        guild_id = message.guild.id
                        # Schedule safe disconnect in the event loop using coroutine-safe method
                        asyncio.run_coroutine_threadsafe(
                            safe_disconnect_after_playback(guild_id, voice_client),
                            client.loop
                        )
                    
                    voice_client.play(audio_source, after=on_playback_finish)
                    logger.info(f"Started playing audio in {message.guild.name}")
                except Exception as e:
                    logger.error(f"Error playing audio: {str(e)}", exc_info=True)
                    await message.channel.send("Error: Failed to play audio.")
                    set_voice_state(message.guild.id, VOICE_STATE_IDLE)
            else:
                await message.channel.send("Already playing audio. Please wait for the current audio to finish.")
        else:
            await message.channel.send("Audio file not found.")
    else:
        await message.channel.send("You are not in a voice channel.")

@client.event
async def on_voice_state_update(member, before, after):
    """Track voice state changes.
    
    IMPORTANT: Never disconnect based on member presence alone.
    Disconnects are now handled safely by check_disconnect() and playback callbacks.
    This prevents race conditions with voice handshake (WebSocket 4006 errors).
    """
    if member == client.user:
        # Only log bot voice state changes for debugging
        if before.channel and not after.channel:
            logger.info(f"Bot disconnected from {before.channel.name} in {member.guild.name}")
            voice_connection_states.pop(member.guild.id, None)
        elif after.channel:
            logger.debug(f"Bot voice state changed in {after.channel.name} ({member.guild.name})")
    
    # Do NOT auto-disconnect based on other members leaving or joining
    # Disconnect responsibility is now with check_disconnect() and playback callbacks
client.run(TOKEN)