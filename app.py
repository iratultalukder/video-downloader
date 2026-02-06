import os
import threading
import time
from flask import Flask, render_template, request, send_file, jsonify
from flask_cors import CORS
import yt_dlp
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration
DOWNLOAD_FOLDER = 'downloads'
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB limit
ALLOWED_EXTENSIONS = {'mp4', 'mp3'}
FILE_CLEANUP_DELAY = 300  # 5 minutes in seconds

# Create downloads folder if it doesn't exist
Path(DOWNLOAD_FOLDER).mkdir(exist_ok=True)

# ==================== SECURITY & VALIDATION ====================

def validate_url(url):
    """Validate if URL is a valid video platform URL"""
    valid_domains = [
        'youtube.com', 'youtu.be',
        'vimeo.com',
        'dailymotion.com',
        'instagram.com',
        'tiktok.com',
        'twitter.com',
        'x.com'
    ]
    
    url_lower = url.lower()
    return any(domain in url_lower for domain in valid_domains)

def cleanup_file(filepath, delay=FILE_CLEANUP_DELAY):
    """Delete file after specified delay (async)"""
    def delete():
        try:
            time.sleep(delay)
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Cleaned up: {filepath}")
        except Exception as e:
            logger.error(f"Error cleaning up {filepath}: {e}")
    
    thread = threading.Thread(target=delete, daemon=True)
    thread.start()

def cleanup_old_files():
    """Clean up files older than FILE_CLEANUP_DELAY"""
    try:
        current_time = time.time()
        for filename in os.listdir(DOWNLOAD_FOLDER):
            filepath = os.path.join(DOWNLOAD_FOLDER, filename)
            if os.path.isfile(filepath):
                file_age = current_time - os.path.getmtime(filepath)
                if file_age > FILE_CLEANUP_DELAY:
                    os.remove(filepath)
                    logger.info(f"Auto-cleaned old file: {filepath}")
    except Exception as e:
        logger.error(f"Error in cleanup_old_files: {e}")

# ==================== YT-DLP CONFIGURATION ====================

def get_yt_dlp_options(format_type, output_path):
    """Configure yt-dlp options based on format"""
    common_options = {
        'quiet': False,
        'no_warnings': False,
        'socket_timeout': 30,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    }
    
    if format_type == 'mp4':
        options = {
            **common_options,
            'format': 'best[ext=mp4]/best',
            'outtmpl': output_path,
            'quiet': False,
            'no_warnings': False,
            'postprocessors': []
        }
    else:  # mp3
        options = {
            **common_options,
            'format': 'bestaudio/best',
            'outtmpl': output_path,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': False,
            'no_warnings': False,
        }
    
    return options

# ==================== ROUTES ====================

@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')

@app.route('/api/download', methods=['POST'])
def download():
    """Handle download requests"""
    try:
        # Clean up old files periodically
        cleanup_old_files()
        
        data = request.get_json()
        url = data.get('url', '').strip()
        format_type = data.get('format', 'mp4')
        
        # Validation
        if not url:
            return jsonify({'error': 'Please provide a URL'}), 400
        
        if not validate_url(url):
            return jsonify({'error': 'Invalid URL. Please provide a valid video platform link (YouTube, Vimeo, etc.)'}), 400
        
        if format_type not in ALLOWED_EXTENSIONS:
            return jsonify({'error': 'Invalid format. Choose mp4 or mp3'}), 400
        
        # Prepare output path
        timestamp = int(time.time())
        filename = f"video_{timestamp}.%(ext)s"
        output_path = os.path.join(DOWNLOAD_FOLDER, filename.replace('.%(ext)s', ''))
        
        logger.info(f"Starting download: {url} as {format_type}")
        
        # Download
        ydl_opts = get_yt_dlp_options(format_type, output_path)
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_title = info.get('title', 'video')
        
        # Find the downloaded file
        downloaded_file = None
        for file in os.listdir(DOWNLOAD_FOLDER):
            if file.startswith(f"video_{timestamp}"):
                downloaded_file = os.path.join(DOWNLOAD_FOLDER, file)
                break
        
        if not downloaded_file or not os.path.exists(downloaded_file):
            return jsonify({'error': 'Download completed but file not found'}), 500
        
        # Check file size
        file_size = os.path.getsize(downloaded_file)
        if file_size > MAX_FILE_SIZE:
            os.remove(downloaded_file)
            return jsonify({'error': 'File size exceeds limit (500MB max)'}), 400
        
        logger.info(f"Download successful: {downloaded_file} ({file_size} bytes)")
        
        # Send file and schedule cleanup
        cleanup_file(downloaded_file)
        
        return send_file(
            downloaded_file,
            as_attachment=True,
            download_name=f"{video_title}.{format_type}"
        )
    
    except yt_dlp.utils.DownloadError as e:
        logger.error(f"yt-dlp error: {e}")
        return jsonify({'error': f'Download error: {str(e)[:100]}'}), 400
    
    except yt_dlp.utils.ExtractorError as e:
        logger.error(f"Extractor error: {e}")
        return jsonify({'error': 'Could not extract video information. The link may be invalid or the video may be unavailable.'}), 400
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify({'error': 'An unexpected error occurred. Please try again.'}), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'Video Downloader API is running'}), 200

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# ==================== MAIN ====================

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)