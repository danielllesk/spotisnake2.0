import os
import time
import requests
import base64
from datetime import timedelta
from flask import Flask, request, jsonify, session
from flask_cors import CORS, cross_origin
# Don't import shared_constants in backend context
# from shared_constants import *
import logging

logging.basicConfig(
    filename='discogs_backend.log',
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(message)s'
)

print("DEBUG: discogs_backend.py - Starting Discogs Flask backend initialization")

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersecretkey")

# CORS configuration - more permissive for development
CORS(app, 
     origins=["*"],  # Allow all origins for now
     allow_headers=["*"],
     expose_headers=["*"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     supports_credentials=False  # Disable credentials for now
     )

# Discogs API configuration
DISCOGS_API_URL = "https://api.discogs.com"
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
    
    try:
        query = request.args.get('q', '')
        if not query:
            return jsonify({"error": "No query provided"}), 400
        
        logging.debug(f"DEBUG: discogs_backend.py - Searching for: {query}")
        
        # Build the Discogs API URL
        search_url = f"{DISCOGS_API_URL}/database/search"
        params = {
            'q': query,
            'type': 'release',
            'format': 'album'
        }
        
        headers = {
            'Accept': 'application/json'
        }
        
        # Add token if available
        if DISCOGS_TOKEN:
            headers['Authorization'] = f'Discogs token={DISCOGS_TOKEN}'
            logging.debug(f"DEBUG: discogs_backend.py - Using token: {DISCOGS_TOKEN[:10]}...")
        else:
            logging.debug("DEBUG: discogs_backend.py - No token available")
        
        logging.debug(f"DEBUG: discogs_backend.py - Making request to: {search_url}")
        response = requests.get(search_url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        logging.debug(f"DEBUG: discogs_backend.py - Discogs API response received")
        
        return jsonify(data)
        
    except requests.exceptions.RequestException as e:
        logging.error(f"DEBUG: discogs_backend.py - Request error: {e}")
        return jsonify({"error": f"Request failed: {str(e)}"}), 500
    except Exception as e:
        logging.error(f"DEBUG: discogs_backend.py - Unexpected error: {e}")
        import traceback
        logging.error(f"DEBUG: discogs_backend.py - Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

@app.route('/download_album_cover', methods=['POST'])
@cross_origin(supports_credentials=True)
def download_album_cover():
    """Download and resize album cover image"""
    logging.debug("DEBUG: discogs_backend.py - Download album cover endpoint called")
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
        image_url = data.get('image_url')
        
        if not image_url:
            return jsonify({"error": "No image URL provided"}), 400
        
        logging.debug(f"DEBUG: discogs_backend.py - Downloading image from: {image_url}")
        
        # Download the image
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.discogs.com/',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        response = requests.get(image_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Get the raw image data first
        image_data = response.content
        
        # Get target dimensions from request
        target_width = data.get('target_width', 600)
        target_height = data.get('target_height', 600)
        
        # Return raw image data (frontend will handle processing)
        base64_data = base64.b64encode(image_data).decode('utf-8')
        
        logging.debug(f"DEBUG: discogs_backend.py - Image downloaded, size: {len(image_data)} bytes")
        
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
        import traceback
        logging.error(f"DEBUG: discogs_backend.py - Traceback: {traceback.format_exc()}")
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
