from google.cloud import texttospeech
import os

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'ckc-tts-bot-28b03e81ae46.json'

client = texttospeech.TextToSpeechClient()

text_block= "Hi there! I'm a text-to-speech bot. I can help you convert text to speech. Just type your message in this channel and I'll convert it to speech for you."

synthesis_input = texttospeech.SynthesisInput(text=text_block)

voice = texttospeech.VoiceSelectionParams(
    language_code="en-US",
    name="en-US-Studio-O"
)

audio_config = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.MP3,
    effects_profile_id=["small-bluetooth-speaker-class-device"],
    speaking_rate=1.0,
    pitch=1.0
)

response = client.synthesize_speech(
    input=synthesis_input, 
    voice=voice, 
    audio_config=audio_config
)

with open("output.mp3", "wb") as out:
    out.write(response.audio_content)
    print("Audio content written to file 'output.mp3'")