import yt_dlp
from pydub import AudioSegment
import os
import logging

logger = logging.getLogger('CKCBot')


def download_youtube_video_as_mp3(youtube_url, output_path='output'):
    """Download YouTube video and convert to MP3 format."""
    try:
        logger.info(f"Starting YouTube download: {youtube_url}")
        
        # Create output directory if it doesn't exist
        try:
            if not os.path.exists(output_path):
                os.makedirs(output_path)
                logger.debug(f"Created output directory: {output_path}")
        except OSError as e:
            logger.error(f"Failed to create output directory {output_path}: {str(e)}", exc_info=True)
            raise

        # Configure yt-dlp options
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': False,
            'no_warnings': False,
        }

        # Download and convert video
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.debug(f"Starting yt-dlp download for: {youtube_url}")
                info = ydl.extract_info(youtube_url, download=True)
                title = info.get('title', 'Unknown')
                logger.info(f"Successfully downloaded and converted to MP3: {title}")
                return title
        except yt_dlp.utils.DownloadError as e:
            logger.error(f"yt-dlp download error for {youtube_url}: {str(e)}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Failed to download/convert video {youtube_url}: {str(e)}", exc_info=True)
            raise
    
    except Exception as e:
        logger.error(f"YouTube MP3 conversion failed for {youtube_url}: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    try:
        youtube_url = input("Enter the YouTube video URL: ")
        if not youtube_url.strip():
            logger.error("No YouTube URL provided")
            raise ValueError("YouTube URL cannot be empty")
        
        logger.info(f"User initiated YouTube download: {youtube_url}")
        title = download_youtube_video_as_mp3(youtube_url)
        logger.info(f"Download completed successfully: {title}")
    except KeyboardInterrupt:
        logger.info("YouTube download cancelled by user")
    except Exception as e:
        logger.critical(f"YouTube download failed: {str(e)}", exc_info=True)
        raise
