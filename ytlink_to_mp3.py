import yt_dlp
from pydub import AudioSegment
import os

def download_youtube_video_as_mp3(youtube_url, output_path='output'):
    # Create output directory if it doesn't exist
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    # Download the video and convert it to MP3
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([youtube_url])

    print("Downloaded and converted to MP3")

if __name__ == "__main__":
    youtube_url = input("Enter the YouTube video URL: ")
    download_youtube_video_as_mp3(youtube_url)
