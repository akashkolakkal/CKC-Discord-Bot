import os
from google.oauth2 import service_account
from google.cloud import texttospeech


def tts(text_block):
    # Retrieve the environment variables
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    client_email = os.getenv('GOOGLE_CLOUD_CLIENT_EMAIL')
    client_id = os.getenv('GOOGLE_CLOUD_CLIENT_ID')
    private_key_id = os.getenv('GOOGLE_CLOUD_PRIVATE_KEY_ID')
    private_key = os.getenv('GOOGLE_CLOUD_PRIVATE_KEY').replace(
        "\\n", "\n")  # Replace \n with actual newlines

    # Create a credentials object using the environment variables
    credentials = service_account.Credentials.from_service_account_info({
        "type":
        "service_account",
        "project_id":
        project_id,
        "private_key_id":
        private_key_id,
        "private_key":
        private_key,
        "client_email":
        client_email,
        "client_id":
        client_id,
        "auth_uri":
        "https://accounts.google.com/o/oauth2/auth",
        "token_uri":
        "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url":
        "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url":
        f"https://www.googleapis.com/robot/v1/metadata/x509/{client_email}"
    })

    # Initialize the Text-to-Speech client with the credentials
    client = texttospeech.TextToSpeechClient(credentials=credentials)

    synthesis_input = texttospeech.SynthesisInput(text=text_block)

    voice = texttospeech.VoiceSelectionParams(language_code="mr-IN",
                                              name="mr-IN-Standard-C")

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        effects_profile_id=["small-bluetooth-speaker-class-device"],
        speaking_rate=1,
        pitch=0.75)

    response = client.synthesize_speech(input=synthesis_input,
                                        voice=voice,
                                        audio_config=audio_config)

    with open("output.mp3", "wb") as out:
        out.write(response.audio_content)
        print("Audio content written to file 'output.mp3'")
