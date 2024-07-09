
## Setup and Installation

This is a self-hosted bot which one can be hosted on any Linux/Windows Machines with their respective methods
## Getting Text-to-Speech API Key
This bot uses the **Google text-to-speech API** for speech generation.
You can choose from one of the basic voice options covered in the free tier.

Link to the API : https://console.cloud.google.com/marketplace/product/google/texttospeech.googleapis.com

You will need to create a google cloud account and make a project for this bot, then go to the linked page and enable api in the selected project

Create a service account for the API and go to *Credentials > KEYS > Create new KEY*  
A .json file would be downloaded on your device which contains the Credentials for you tts API.

## Setting up the .env file
We have to copy the Values of the following attributed in the JSON file and create a .env file in the root directory of the project and paste the values in the following format:
    
    TOKEN=<discord_bot_token>
    GOOGLE_CLOUD_PROJECT=<google_cloud_projectname>
    GOOGLE_CLOUD_PRIVATE_KEY_ID=<google_cloud_private_key_id>
    GOOGLE_CLOUD_CLIENT_EMAIL=<google-cloud_private_key_id>
    GOOGLE_CLOUD_PRIVATE_KEY=<google_cloud_private_key>
    GOOGLE_CLOUD_CLIENT_ID=<google_cloud_client_id>

The TOKEN is the discord bot token which you can get by creating a bot on the discord developer portal.

Discord Developer Portal : https://discord.com/developers/applications
For more information on how to create a bot and get the token, you can refer to the following link:
https://discordpy.readthedocs.io/en/stable/discord.html

## Installing the required dependencies
After setting up the .env file, you need to install the required dependencies by running the following command in the root directory of the project:

    pip install -r requirements.txt

## Installing FFmpeg:

This bot uses FFmpeg for audio manipulation and playback.

### Linux:
You can install FFmpeg on Linux by running the following command:

    sudo apt-get install ffmpeg

### Windows:
You can download FFmpeg from the official website:
https://ffmpeg.org/download.html

After downloading, extract the contents of the zip file and add the bin folder to the system PATH.

## Running the bot

After setting up the .env file and installing the dependencies, you can run the bot by running the following command in the root directory of the project:

### Linux:
    sudo python3 main.py
    
    ## Note for Linux Users

    If you are running the bot on a Linux machine, please make sure to use `sudo` when running the bot. This is necessary to ensure that the bot has the necessary permissions to write onto the `usage.json` and `tts_channels.json` files.


### Windows:
    python main.py

