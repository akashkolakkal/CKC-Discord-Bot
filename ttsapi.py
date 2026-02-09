import os
from google.oauth2 import service_account
from google.cloud import texttospeech
import json
import logging

logger = logging.getLogger('CKCBot')


def tts(text_block, guildId):
    """Convert text to speech using Google Cloud TTS API."""
    try:
        logger.debug(f"TTS synthesis started for guild {guildId}, text length: {len(text_block)}")
        
        # Load guild configuration
        try:
            with open('config.json') as f:
                config_data = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse config.json: {str(e)}", exc_info=True)
            raise
        except FileNotFoundError:
            logger.error("config.json file not found")
            raise
        except Exception as e:
            logger.error(f"Error reading config.json: {str(e)}", exc_info=True)
            raise
        
        # Validate guild exists in config
        if str(guildId) not in config_data:
            logger.error(f"Guild {guildId} not found in config.json")
            raise KeyError(f"Guild {guildId} not configured")
        
        try:
            guildData = config_data[str(guildId)]
            lang_code = guildData[0]["language-code"]
            voice_name = guildData[0]["name"]
            voice_speed = guildData[0]["speech-rate"]
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Invalid guild configuration for {guildId}: {str(e)}", exc_info=True)
            raise

        # Retrieve and validate environment variables
        env_vars = {
            'GOOGLE_CLOUD_PROJECT': os.getenv('GOOGLE_CLOUD_PROJECT'),
            'GOOGLE_CLOUD_CLIENT_EMAIL': os.getenv('GOOGLE_CLOUD_CLIENT_EMAIL'),
            'GOOGLE_CLOUD_CLIENT_ID': os.getenv('GOOGLE_CLOUD_CLIENT_ID'),
            'GOOGLE_CLOUD_PRIVATE_KEY_ID': os.getenv('GOOGLE_CLOUD_PRIVATE_KEY_ID'),
            'GOOGLE_CLOUD_PRIVATE_KEY': os.getenv('GOOGLE_CLOUD_PRIVATE_KEY')
        }
        
        missing_vars = [var for var, val in env_vars.items() if not val]
        if missing_vars:
            logger.critical(f"Missing required Google Cloud environment variables: {missing_vars}")
            raise ValueError(f"Missing env vars: {missing_vars}")
        
        private_key = env_vars['GOOGLE_CLOUD_PRIVATE_KEY'].replace("\\n", "\n")

        # Create credentials
        try:
            credentials = service_account.Credentials.from_service_account_info({
                "type": "service_account",
                "project_id": env_vars['GOOGLE_CLOUD_PROJECT'],
                "private_key_id": env_vars['GOOGLE_CLOUD_PRIVATE_KEY_ID'],
                "private_key": private_key,
                "client_email": env_vars['GOOGLE_CLOUD_CLIENT_EMAIL'],
                "client_id": env_vars['GOOGLE_CLOUD_CLIENT_ID'],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{env_vars['GOOGLE_CLOUD_CLIENT_EMAIL']}"
            })
            logger.debug("Google Cloud credentials created successfully")
        except Exception as e:
            logger.error(f"Failed to create Google Cloud credentials: {str(e)}", exc_info=True)
            raise

        # Initialize TTS client
        try:
            client = texttospeech.TextToSpeechClient(credentials=credentials)
            logger.debug("TTS client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize TTS client: {str(e)}", exc_info=True)
            raise

        # Configure synthesis parameters
        try:
            synthesis_input = texttospeech.SynthesisInput(text=text_block)
            voice = texttospeech.VoiceSelectionParams(language_code=lang_code, name=voice_name)
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                effects_profile_id=["small-bluetooth-speaker-class-device"],
                speaking_rate=voice_speed,
                pitch=0.75
            )
            logger.debug(f"Synthesis configured: lang={lang_code}, voice={voice_name}, speed={voice_speed}")
        except Exception as e:
            logger.error(f"Failed to configure synthesis: {str(e)}", exc_info=True)
            raise

        # Call TTS API
        try:
            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            logger.info(f"TTS synthesis successful for guild {guildId}")
        except Exception as e:
            logger.error(f"Google Cloud TTS API call failed for guild {guildId}: {str(e)}", exc_info=True)
            raise

        # Create output directory and save audio file
        try:
            output_folder = "messageOutput"
            output_file = os.path.join(output_folder, "output.mp3")
            
            # Create the output folder if it doesn't exist
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)
                logger.debug(f"Created output directory: {output_folder}")
            
            # Write audio to file
            with open(output_file, "wb") as out:
                out.write(response.audio_content)
            
            logger.info(f"Audio file saved to {output_file} (size: {len(response.audio_content)} bytes)")
        except IOError as e:
            logger.error(f"Failed to write audio file: {str(e)}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Error saving audio file: {str(e)}", exc_info=True)
            raise
    
    except Exception as e:
        logger.error(f"TTS synthesis failed for guild {guildId}: {str(e)}", exc_info=True)
        raise