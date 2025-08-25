import os
import time
import requests
import base64
from datetime import timedelta
from flask import Flask, request, jsonify, session
from flask_cors import CORS, cross_origin
from shared_constants import *
import logging

logging.basicConfig(
    filename='discogs_backend.log',
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(message)s'
)

print("DEBUG: discogs_backend.py - Starting Discogs Flask backend initialization")

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersecretkey")

# CORS configuration
CORS(app, supports_credentials=True, 
     origins=[
         # Allow all localhost variants
         "http://localhost:8000",
         "http://127.0.0.1:8000", 
         "http://[::1]:8000",
         "http://[::]:8000",
         "http://localhost:3000",
         "http://localhost:8080",
         "http://localhost:9000",
         "https://localhost:8000",
         "https://127.0.0.1:8000", 
         "https://[::1]:8000",
         "https://[::]:8000",
         "https://localhost:3000",
         "https://localhost:8080",
         "https://localhost:9000",
         # Production domains
         "https://discogsnake.onrender.com",
         "https://danielllesk.itch.io",
         "https://danielllesk.itch.io/discogsnake",
         "https://html-classic.itch.zone",
         # Allow any itch.io subdomain
         "https://*.itch.io",
         "https://*.itch.zone"
     ],
     allow_headers=["Content-Type", "Authorization", "Origin", "Accept", "X-Requested-With"],
     expose_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     credentials=True
     )

# Discogs API configuration
DISCOGS_API_URL = "https://api.discogs.com"
DISCOGS_USER_AGENT = "DiscogSnake/1.0 +https://github.com/yourusername/discogsnake"
DISCOGS_TOKEN = os.environ.get("DISCOGS_TOKEN", "")

@app.route('/ping', methods=['GET'])
@cross_origin(supports_credentials=True)
def ping():
    """Simple ping endpoint to test connectivity"""
    logging.debug("DEBUG: discogs_backend.py - Ping endpoint called")
    return jsonify({"status": "ok", "message": "Discogs backend is running"})

@app.route('/search', methods=['GET'])
@cross_origin(supports_credentials=True)
def search_albums():
    """Search for albums using Discogs API"""
    logging.debug("DEBUG: discogs_backend.py - Search endpoint called")
    
    query = request.args.get('q', '')
    if not query:
        return jsonify({"error": "No query provided"}), 400
    
    logging.debug(f"DEBUG: discogs_backend.py - Searching for: {query}")
    
    try:
        # Build the Discogs API URL
        search_url = f"{DISCOGS_API_URL}/database/search"
        params = {
            'q': query,
            'type': 'release',
            'format': 'album'
        }
        
        headers = {
            'User-Agent': DISCOGS_USER_AGENT,
            'Accept': 'application/json'
        }
        
        # Add token if available
        if DISCOGS_TOKEN:
            headers['Authorization'] = f'Discogs token={DISCOGS_TOKEN}'
        
        response = requests.get(search_url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        logging.debug(f"DEBUG: discogs_backend.py - Discogs API response: {data}")
        
        return jsonify(data)
        
    except requests.exceptions.RequestException as e:
        logging.error(f"DEBUG: discogs_backend.py - Request error: {e}")
        return jsonify({"error": f"Request failed: {str(e)}"}), 500
    except Exception as e:
        logging.error(f"DEBUG: discogs_backend.py - Unexpected error: {e}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

@app.route('/download_album_cover', methods=['POST'])
@cross_origin(supports_credentials=True)
def download_album_cover():
    """Download and resize album cover image"""
    logging.debug("DEBUG: discogs_backend.py - Download album cover endpoint called")
    
    try:
        data = request.get_json()
        image_url = data.get('image_url')
        
        if not image_url:
            return jsonify({"error": "No image URL provided"}), 400
        
        logging.debug(f"DEBUG: discogs_backend.py - Downloading image from: {image_url}")
        
        # Download the image
        headers = {
            'User-Agent': DISCOGS_USER_AGENT
        }
        
        response = requests.get(image_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Convert to base64
        image_data = response.content
        base64_data = base64.b64encode(image_data).decode('utf-8')
        
        logging.debug(f"DEBUG: discogs_backend.py - Image downloaded successfully, size: {len(image_data)} bytes")
        
        return jsonify({
            "status": 200,
            "data": base64_data,
            "size": len(image_data)
        })
        
    except requests.exceptions.RequestException as e:
        logging.error(f"DEBUG: discogs_backend.py - Image download error: {e}")
        return jsonify({"error": f"Image download failed: {str(e)}"}), 500
    except Exception as e:
        logging.error(f"DEBUG: discogs_backend.py - Unexpected error in image download: {e}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

@app.route('/album/<int:album_id>', methods=['GET'])
@cross_origin(supports_credentials=True)
def get_album_details(album_id):
    """Get detailed information about a specific album"""
    logging.debug(f"DEBUG: discogs_backend.py - Get album details endpoint called for ID: {album_id}")
    
    try:
        # Build the Discogs API URL
        album_url = f"{DISCOGS_API_URL}/releases/{album_id}"
        
        headers = {
            'User-Agent': DISCOGS_USER_AGENT,
            'Accept': 'application/json'
        }
        
        # Add token if available
        if DISCOGS_TOKEN:
            headers['Authorization'] = f'Discogs token={DISCOGS_TOKEN}'
        
        response = requests.get(album_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        logging.debug(f"DEBUG: discogs_backend.py - Album details retrieved successfully")
        
        return jsonify(data)
        
    except requests.exceptions.RequestException as e:
        logging.error(f"DEBUG: discogs_backend.py - Request error: {e}")
        return jsonify({"error": f"Request failed: {str(e)}"}), 500
    except Exception as e:
        logging.error(f"DEBUG: discogs_backend.py - Unexpected error: {e}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

@app.route('/health', methods=['GET'])
@cross_origin(supports_credentials=True)
def health_check():
    """Health check endpoint"""
    logging.debug("DEBUG: discogs_backend.py - Health check endpoint called")
    return jsonify({
        "status": "healthy",
        "timestamp": time.time(),
        "discogs_token_configured": bool(DISCOGS_TOKEN)
    })

if __name__ == '__main__':
    print("DEBUG: discogs_backend.py - Starting Discogs backend server")
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
