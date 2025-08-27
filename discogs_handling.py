
print("discogs_handling.py loaded")
print("DEBUG: discogs_handling.py - Starting module initialization")

import pygame
from shared_constants import *
from io import BytesIO
import random
import asyncio
import os
import time
import js
import json
import urllib.parse
print("DEBUG: discogs_handling.py - All imports completed")

# Discogs API configuration
DISCOGS_API_URL = "https://api.discogs.com"
DISCOGS_USER_AGENT = "SpotiSnake/1.0 +https://github.com/yourusername/spotisnake"
DISCOGS_TOKEN = os.environ.get("DISCOGS_TOKEN", "")  # Optional personal access token

# Use deployed backend URL for production (if we create a Discogs backend)
BACKEND_URL = os.environ.get("DISCOGSNAKE_BACKEND_URL", "https://spotisnake2-0.onrender.com")

clock = pygame.time.Clock()
pygame.init()

USER_ABORT_GAME_FROM_SEARCH = "USER_ABORT_GAME_FROM_SEARCH"

def is_pyodide():
    """Check if we're running in a browser environment (pygbag/pyodide)"""
    try:
        import js
        # Check for browser-specific attributes
        has_window = hasattr(js, 'window')
        has_fetch = hasattr(js, 'fetch')
        has_eval = hasattr(js, 'eval')
        
        # In pygbag/pyodide, we should have all these
        is_browser = has_window and has_fetch and has_eval
        
        print(f"DEBUG: discogs_handling.py - Environment check: window={has_window}, fetch={has_fetch}, eval={has_eval}, is_browser={is_browser}")
        return is_browser
    except ImportError:
        print("DEBUG: discogs_handling.py - js module not available")
        return False
    except AttributeError:
        print("DEBUG: discogs_handling.py - js module available but missing required attributes")
        return False

async def search_album_via_discogs(query, max_retries=2):
    """Search for albums using Discogs API with retry logic for backend wake-up"""
    print(f"DEBUG: discogs_handling.py - search_album_via_discogs called with query: {query}")
    
    # Check if we're in a browser environment
    if not is_pyodide():
        print("DEBUG: discogs_handling.py - Not in browser environment, using desktop fallback for search")
        # For desktop, return a mock search result
        return {
            'results': [
                {
                    'title': 'Demo Album (Desktop Mode)',
                    'id': 12345,
                    'thumb': 'https://img.discogs.com/example.jpg',
                    'artist': 'Demo Artist',
                    'type': 'release'
                },
                {
                    'title': 'Test Album 2',
                    'id': 67890,
                    'thumb': 'https://img.discogs.com/example2.jpg',
                    'artist': 'Test Artist',
                    'type': 'release'
                }
            ]
        }
    
    # Try multiple times in case backend is slow to wake up
    for attempt in range(max_retries):
        print(f"DEBUG: discogs_handling.py - Search attempt {attempt + 1}/{max_retries}")
        
        result = await _search_album_single_attempt(query)
        if result and 'results' in result:
            print(f"DEBUG: discogs_handling.py - Search successful on attempt {attempt + 1}")
            return result
        
        if attempt < max_retries - 1:
            print(f"DEBUG: discogs_handling.py - Search failed, retrying in 2 seconds...")
            await asyncio.sleep(2)
    
    print(f"DEBUG: discogs_handling.py - All search attempts failed")
    return None

async def _search_album_single_attempt(query):
    """Single attempt to search for albums using Discogs API"""
    try:
        import js
        
        # URL encode the query to handle special characters
        encoded_query = urllib.parse.quote(query)
        
        # Try to use backend first, fallback to direct API
        search_url = f"{BACKEND_URL}/search?q={encoded_query}"
        print(f"DEBUG: discogs_handling.py - Backend URL: {search_url}")
        
        js_code = f'''
        console.log("JS: Starting Discogs search for: {query}");
        console.log("JS: Fetching from backend URL: {search_url}");
        
        fetch("{search_url}", {{
            method: "GET",
            headers: {{
                "Accept": "application/json"
            }},
            mode: "cors"
        }})
        .then(response => {{
            console.log("JS: Backend response status:", response.status);
            console.log("JS: Backend response ok:", response.ok);
            
            if (!response.ok) {{
                console.log("JS: Backend failed, trying direct API");
                throw new Error(`Backend HTTP error! status: ${{response.status}}`);
            }}
            
            return response.json();
        }})
        .then(data => {{
            console.log("JS: Backend search data received:", data);
            console.log("JS: Backend data type:", typeof data);
            console.log("JS: Backend data keys:", Object.keys(data));
            console.log("JS: Backend data results length:", data.results ? data.results.length : "no results");
            console.log("JS: Setting window.discogs_search_result");
            window.discogs_search_result = data;
            console.log("JS: window.discogs_search_result set:", window.discogs_search_result);
            return Promise.resolve(); // Don't continue to fallback
        }})
        .catch(error => {{
            console.log("JS: Backend search error:", error);
            // Fallback to direct Discogs API
            console.log("JS: Falling back to direct Discogs API");
            const directUrl = "{DISCOGS_API_URL}/database/search?q={encoded_query}&type=release&format=album";
            console.log("JS: Direct API URL:", directUrl);
            
            return fetch(directUrl, {{
                method: "GET",
                headers: {{
                    "User-Agent": "{DISCOGS_USER_AGENT}",
                    "Accept": "application/json"
                }},
                mode: "cors"
            }})
            .then(response => {{
                if (response && response.ok) {{
                    console.log("JS: Direct API response ok");
                    return response.json();
                }}
                console.log("JS: Direct API failed, status:", response ? response.status : "no response");
                throw new Error("Both backend and direct API failed");
            }})
            .then(data => {{
                console.log("JS: Direct Discogs API data received:", data);
                window.discogs_search_result = data;
            }});
        }})
        .catch(error => {{
            console.log("JS: All search methods failed:", error);
            window.discogs_search_result = {{ error: error.toString() }};
        }});
        '''
        
        js.eval(js_code)
        await asyncio.sleep(0.5)  # Wait for the fetch to complete
        
        if hasattr(js.window, 'discogs_search_result'):
            result = js.window.discogs_search_result
            print(f"DEBUG: discogs_handling.py - Discogs search result: {result}")
            print(f"DEBUG: discogs_handling.py - Result type: {type(result)}")
            print(f"DEBUG: discogs_handling.py - Result string representation: {str(result)}")
            
            # Handle different result types
            if isinstance(result, dict):
                if 'results' in result:
                    return result
                elif 'error' in result:
                    print(f"DEBUG: discogs_handling.py - Discogs search error: {result['error']}")
                    return None
            else:
                print(f"DEBUG: discogs_handling.py - Unexpected result type: {type(result)}")
                # Try to convert browser Object to Python dict
                try:
                    # Use JavaScript to convert the object to JSON string
                    js_code = '''
                    try {
                        const jsonStr = JSON.stringify(window.discogs_search_result);
                        window.converted_discogs_result = jsonStr;
                    } catch(e) {
                        window.converted_discogs_result = null;
                    }
                    '''
                    js.eval(js_code)
                    await asyncio.sleep(0.1)
                    
                    if hasattr(js.window, 'converted_discogs_result') and js.window.converted_discogs_result:
                        import json
                        converted_result = json.loads(js.window.converted_discogs_result)
                        print(f"DEBUG: discogs_handling.py - Converted result: {converted_result}")
                        if 'results' in converted_result:
                            return converted_result
                        elif 'error' in converted_result:
                            print(f"DEBUG: discogs_handling.py - Converted Discogs search error: {converted_result['error']}")
                            return None
                except Exception as e:
                    print(f"DEBUG: discogs_handling.py - Error converting browser object: {e}")
                return None
        else:
            print("DEBUG: discogs_handling.py - No Discogs search result available")
            return None
    except Exception as e:
        print(f"DEBUG: discogs_handling.py - Error in _search_album_single_attempt: {e}")
        return None

async def download_and_resize_album_cover_async(url, target_width, target_height):
    """Download and resize album cover asynchronously"""

    if not url:
        return create_fallback_album_cover(target_width, target_height)

    # Try to load the actual image using direct fetch
    try:
        import js
        import base64

        # Check if we're in a proper browser environment (pygbag/pyodide)
        if is_pyodide():
            print(f"DEBUG: discogs_handling.py - Running in pygbag/pyodide environment, using browser download")
        else:
            print(f"DEBUG: discogs_handling.py - Desktop environment detected, using Python download")
            raise ImportError("Desktop environment - use Python fallback")
    except ImportError:
        print(f"DEBUG: discogs_handling.py - js module not available, trying Python download")
        # Try to download using Python requests if available
        try:
            import requests
            print(f"DEBUG: discogs_handling.py - Using Python requests to download image")
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                try:
                    image_data = response.content
                    import io
                    image_stream = io.BytesIO(image_data)
                    image = pygame.image.load(image_stream)
                    resized_image = pygame.transform.scale(image, (target_width, target_height))
                    print(f"DEBUG: discogs_handling.py - Successfully downloaded image via Python")
                    return resized_image
                except Exception as e:
                    print(f"DEBUG: discogs_handling.py - Failed to load image from Python download: {e}")
                    return create_visual_album_cover(url, target_width, target_height)
            else:
                print(f"DEBUG: discogs_handling.py - Python download failed with status: {response.status_code}")
                return create_visual_album_cover(url, target_width, target_height)
        except ImportError:
            print(f"DEBUG: discogs_handling.py - requests module not available, using fallback cover")
            return create_visual_album_cover(url, target_width, target_height)
        except Exception as e:
            print(f"DEBUG: discogs_handling.py - Python download failed: {e}")
            return create_visual_album_cover(url, target_width, target_height)

    # Browser-based download - try backend first, fallback to direct download
    js_code = f'''
    console.log("Starting album cover download for: {url}");
    
    (async () => {{
        try {{
            // Try backend first
            console.log("Trying backend download");
            const backendResponse = await fetch("{BACKEND_URL}/download_album_cover", {{
                method: "POST",
                headers: {{
                    "Content-Type": "application/json"
                }},
                mode: "cors",
                body: JSON.stringify({{
                    "image_url": "{url}",
                    "target_width": {target_width},
                    "target_height": {target_height}
                }})
            }});
            
            if (backendResponse.ok) {{
                const backendData = await backendResponse.json();
                if (backendData.status === 200 && backendData.data) {{
                    window.image_download_result = {{ status: 200, data: backendData.data }};
                    window.image_download_complete = true;
                    console.log("Backend image download completed successfully");
                    return;
                }}
            }}
            
            // Fallback to direct download
            console.log("Backend failed, trying direct download");
            const response = await fetch("{url}", {{
                method: "GET"
            }});
            
            console.log("Direct response status:", response.status);
            console.log("Direct response ok:", response.ok);
            
            if (!response.ok) {{
                throw new Error(`HTTP error! status: ${{response.status}}`);
            }}
            
            const blob = await response.blob();
            const reader = new FileReader();
            
            reader.onload = function() {{
                const base64data = reader.result.split(',')[1];
                window.image_download_result = {{ status: 200, data: base64data }};
                window.image_download_complete = true;
                console.log("Direct image download completed successfully");
            }};
            
            reader.onerror = function() {{
                console.log("FileReader error");
                window.image_download_result = {{ status: 500, error: "FileReader error" }};
                window.image_download_complete = true;
            }};
            
            reader.readAsDataURL(blob);
            
        }} catch (error) {{
            console.log("Album cover download error:", error);
            window.image_download_result = {{ status: 500, error: error.toString() }};
            window.image_download_complete = true;
        }}
    }})();
    '''

    try:
        print(f"DEBUG: discogs_handling.py - Executing JavaScript code for {url}")
        js.eval(js_code)
        print(f"DEBUG: discogs_handling.py - JavaScript code executed, waiting for result")

        # Wait for the async JavaScript to complete
        for i in range(10):  # Wait up to 1 second
            await asyncio.sleep(0.1)  # Wait 100ms each time

            # Check if the download is complete
            if hasattr(js.window, 'image_download_complete') and js.window.image_download_complete:
                break

            # Also check if we have a result (in case complete flag isn't set)
            if hasattr(js.window, 'image_download_result') and js.window.image_download_result is not None:
                break

        # Get the result and clean up
        result = None
        if hasattr(js.window, 'image_download_result'):
            js_result = js.window.image_download_result

            # Convert JavaScript object to Python dictionary
            try:
                if hasattr(js_result, 'status'):
                    status = js_result.status
                    data = getattr(js_result, 'data', None)
                    error = getattr(js_result, 'error', None)
                    result = {
                        'status': status,
                        'data': data,
                        'error': error
                    }
                elif isinstance(js_result, dict):
                    result = js_result
                else:
                    result = None

            except Exception as e:
                print(f"DEBUG: discogs_handling.py - Error in conversion process: {e}")
                result = None

            # Clean up the flags for next download
            try:
                js.window.image_download_result = None
                js.window.image_download_complete = False
            except Exception as e:
                print(f"DEBUG: discogs_handling.py - Error cleaning up flags: {e}")
        else:
            print(f"DEBUG: discogs_handling.py - No image_download_result found in window")
            return create_visual_album_cover(url, target_width, target_height)

        # Handle different result types
        if isinstance(result, dict):
            status = result.get('status', 500)
            if status == 200:
                base64_data = result.get('data')
                if base64_data:
                    try:
                        # Convert base64 to pygame surface
                        resized_image = await base64_to_pygame_surface_pygbag(base64_data, target_width, target_height)
                        if resized_image:
                            return resized_image
                        else:
                            return create_visual_album_cover(url, target_width, target_height)
                    except Exception as e:
                        return create_visual_album_cover(url, target_width, target_height)
                else:
                    return create_visual_album_cover(url, target_width, target_height)
            else:
                return create_visual_album_cover(url, target_width, target_height)
        else:
            return create_visual_album_cover(url, target_width, target_height)
    except Exception as e:
        print(f"DEBUG: discogs_handling.py - Error in download_and_resize_album_cover_async: {e}")
        return create_visual_album_cover(url, target_width, target_height)

def download_and_resize_album_cover(url, target_width, target_height):
    print(f"DEBUG: discogs_handling.py - download_and_resize_album_cover called with url: {url}")

    if not url:
        print(f"DEBUG: discogs_handling.py - No URL provided, creating fallback")
        return create_fallback_album_cover(target_width, target_height)

    # Use the async version for browser builds
    try:
        # Create a simple event loop to run the async function
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an async context, we can't use run_until_complete
            # So we'll use the fallback for now
            print(f"DEBUG: discogs_handling.py - Using fallback cover (async context)")
            return create_fallback_album_cover(target_width, target_height)
        else:
            return loop.run_until_complete(download_and_resize_album_cover_async(url, target_width, target_height))
    except Exception as e:
        print(f"DEBUG: discogs_handling.py - Error in sync wrapper: {e}")
        return create_fallback_album_cover(target_width, target_height)

def create_fallback_album_cover(target_width, target_height):
    """Create a fallback album cover when image download fails"""
    try:
        surface = pygame.Surface((target_width, target_height))

        # Create a more vibrant, colorful pattern
        import random
        import time

        # Use time to create different patterns each time
        random.seed(int(time.time() * 1000) % 1000)

        # Create a colorful gradient pattern
        for y in range(target_height):
            for x in range(target_width):
                # Create a more vibrant pattern
                progress_x = x / target_width
                progress_y = y / target_height

                # Generate bright, colorful gradients
                r = int(128 + 127 * (progress_x + random.random() * 0.3))
                g = int(128 + 127 * (progress_y + random.random() * 0.3))
                b = int(128 + 127 * ((progress_x + progress_y) / 2 + random.random() * 0.3))

                # Ensure values are in valid range
                r = max(50, min(255, r))
                g = max(50, min(255, g))
                b = max(50, min(255, b))

                surface.set_at((x, y), (r, g, b))

        # Add a colorful border
        border_color = (random.randint(100, 255), random.randint(100, 255), random.randint(100, 255))
        pygame.draw.rect(surface, border_color, surface.get_rect(), 2)

        # Add some text to indicate it's an album cover
        try:
            font = pygame.font.SysFont("Arial", min(target_width, target_height) // 8)
            text = font.render("ALBUM", True, (255, 255, 255))
            text_rect = text.get_rect(center=(target_width // 2, target_height // 2))
            surface.blit(text, text_rect)
        except Exception as e:
            pass  # If font rendering fails, just use the gradient

        return surface
    except Exception as e:
        print(f"DEBUG: discogs_handling.py - Error creating fallback album cover: {e}")
        return None

def create_visual_album_cover(image_url, target_width, target_height):
    """Create a visual album cover that works in browser environments"""
    try:
        # Generate a unique color pattern based on the image URL
        import hashlib
        hash_value = hashlib.md5(image_url.encode()).hexdigest()
        print(f"DEBUG: discogs_handling.py - Hash value: {hash_value}")
        
        # Create a surface
        surface = pygame.Surface((target_width, target_height))
        
        # Create a cleaner, more appealing pattern
        # Use the hash to generate a consistent color palette
        r_base = int(hash_value[0:2], 16)
        g_base = int(hash_value[2:4], 16)
        b_base = int(hash_value[4:6], 16)
        
        print(f"DEBUG: discogs_handling.py - Creating visual cover with base colors: R={r_base}, G={g_base}, B={b_base}")
        
        # If all colors are 0, use a fallback
        if r_base == 0 and g_base == 0 and b_base == 0:
            print(f"DEBUG: discogs_handling.py - All base colors are 0, using fallback colors")
            r_base = 128
            g_base = 64
            b_base = 192
        
        # Create a gradient pattern
        for y in range(target_height):
            for x in range(target_width):
                # Create a smooth gradient based on position
                x_ratio = x / target_width
                y_ratio = y / target_height
                
                # Mix the base colors with position-based variation
                r = int(r_base * (0.5 + 0.5 * x_ratio))
                g = int(g_base * (0.5 + 0.5 * y_ratio))
                b = int(b_base * (0.5 + 0.5 * (x_ratio + y_ratio) / 2))
                
                # Ensure values are in valid range
                r = max(0, min(255, r))
                g = max(0, min(255, g))
                b = max(0, min(255, b))
                
                # Fill the surface with the color
                surface.set_at((x, y), (r, g, b))
        
        # Add a subtle border
        pygame.draw.rect(surface, (255, 255, 255), surface.get_rect(), 1)
        
        return surface
    except Exception as e:
        print(f"DEBUG: discogs_handling.py - Error creating visual album cover: {e}")
        return create_fallback_album_cover(target_width, target_height)

async def base64_to_pygame_surface_pygbag(base64_data, target_width, target_height):
    """Convert base64 data to pygame surface specifically for pygbag/browser environment"""
    try:
        import base64
        
        # Decode base64 data
        image_data = base64.b64decode(base64_data)
        
        # Since pygame.image.load() doesn't work in browser, we'll create a surface
        # and manually set pixels based on the image data
        surface = pygame.Surface((target_width, target_height))
        
        # Use JavaScript to get pixel data from the image
        js_code = f'''
        try {{
            // Create a canvas element
            const canvas = document.createElement('canvas');
            canvas.width = {target_width};
            canvas.height = {target_height};
            const ctx = canvas.getContext('2d');
            
            // Create an image element
            const img = new Image();
            img.crossOrigin = "anonymous";
            
            img.onload = function() {{
                // Draw the image on the canvas, scaled to fit
                ctx.drawImage(img, 0, 0, {target_width}, {target_height});
                
                // Get the pixel data
                const imageData = ctx.getImageData(0, 0, {target_width}, {target_height});
                window.album_cover_pixels = imageData.data;
                window.album_cover_loaded = true;
                console.log("Album cover pixels extracted successfully");
            }};
            
            img.onerror = function() {{
                console.log("Failed to load album cover image");
                window.album_cover_loaded = false;
            }};
            
            // Set the base64 data as src
            img.src = "data:image/jpeg;base64,{base64_data}";
            
        }} catch(e) {{
            console.log("Error creating canvas:", e);
            window.album_cover_loaded = false;
        }}
        '''
        
        import js
        js.eval(js_code)
        
        # Wait for the image to load and be drawn to canvas
        import asyncio
        await asyncio.sleep(0.3)
        
        # Check if the image was loaded successfully
        if hasattr(js.window, 'album_cover_loaded') and js.window.album_cover_loaded:
            print(f"DEBUG: discogs_handling.py - Real album cover loaded and drawn to canvas")
            
            # Get the pixel data from JavaScript
            if hasattr(js.window, 'album_cover_pixels'):
                pixels = js.window.album_cover_pixels
                
                # Convert JavaScript array to Python and set pixels
                for y in range(target_height):
                    for x in range(target_width):
                        idx = (y * target_width + x) * 4  # RGBA format
                        r = int(pixels[idx])
                        g = int(pixels[idx + 1])
                        b = int(pixels[idx + 2])
                        a = int(pixels[idx + 3])
                        surface.set_at((x, y), (r, g, b, a))
                
                print(f"DEBUG: discogs_handling.py - Real album cover surface created: {surface.get_size()}")
                return surface
            else:
                print(f"DEBUG: discogs_handling.py - No pixel data found, using visual representation")
                return create_visual_album_cover_from_data(image_data, target_width, target_height)
        else:
            print(f"DEBUG: discogs_handling.py - Failed to load real album cover, using visual representation")
            return create_visual_album_cover_from_data(image_data, target_width, target_height)
            
    except Exception as e:
        print(f"DEBUG: discogs_handling.py - Error creating pygame surface from base64: {e}")
        return create_visual_album_cover_from_data(image_data, target_width, target_height)

def create_visual_album_cover_from_data(image_data, target_width, target_height):
    """Create a visual album cover from image data when pygame.image.load fails"""
    try:
        # Generate a unique color pattern based on the image data
        import hashlib
        hash_value = hashlib.md5(image_data).hexdigest()
        
        # Create a surface
        surface = pygame.Surface((target_width, target_height))
        
        # Use the hash to generate a consistent color palette
        r_base = int(hash_value[0:2], 16)
        g_base = int(hash_value[2:4], 16)
        b_base = int(hash_value[4:6], 16)
        
        # Ensure minimum brightness
        r_base = max(r_base, 50)
        g_base = max(g_base, 50)
        b_base = max(b_base, 50)
        
        # Create a more vibrant pattern
        for y in range(target_height):
            for x in range(target_width):
                # Create a gradient pattern
                progress_x = x / target_width
                progress_y = y / target_height
                
                # Generate colors with more variation
                r = int((r_base + progress_x * 100 + progress_y * 50) % 256)
                g = int((g_base + progress_y * 100 + progress_x * 50) % 256)
                b = int((b_base + (progress_x + progress_y) * 75) % 256)
                
                # Ensure minimum brightness
                r = max(r, 30)
                g = max(g, 30)
                b = max(b, 30)
                
                surface.set_at((x, y), (r, g, b))
        
        # Add a colored border based on the hash
        border_color = (
            int(hash_value[6:8], 16),
            int(hash_value[8:10], 16),
            int(hash_value[10:12], 16)
        )
        pygame.draw.rect(surface, border_color, surface.get_rect(), 2)
        
        return surface
    except Exception as e:
        print(f"DEBUG: discogs_handling.py - Error creating visual cover from data: {e}")
        return create_fallback_album_cover(target_width, target_height)

async def get_album_search_input(screen, font):
    print("DEBUG: discogs_handling.py - get_album_search_input called (START)")
    
    input_box = pygame.Rect(width // 2 - 200, 100, 400, 50)
    results_area = pygame.Rect(width // 2 - 200, 160, 400, 300)
    color_inactive = DARK_BLUE
    color_active = LIGHT_BLUE
    color = color_inactive
    active = False
    text = ''
    search_results = []
    album_covers = {}
    quit_button_font = pygame.font.SysFont("Press Start 2P", 20)
    quit_button_rect_local = pygame.Rect(20, height - 70, 250, 50)
    
    # Cursor variables
    cursor_visible = True
    cursor_timer = 0
    cursor_blink_rate = 500  # milliseconds
    
    # Loading state variable
    is_searching = False

    async def draw_search_results_local():
        nonlocal album_covers
        
        # Show loading message if searching
        if is_searching:
            print(f"DEBUG: discogs_handling.py - Displaying loading message")
            loading_font = pygame.font.SysFont("Press Start 2P", 20)
            loading_text = loading_font.render("Searching for album... hang on", True, WHITE)
            loading_rect = loading_text.get_rect(center=(width // 2, 250))
            screen.blit(loading_text, loading_rect)
            return

        if search_results:
            y_offset = results_area.y + 10
            for album in search_results:
                result_rect = pygame.Rect(results_area.x + 5, y_offset, results_area.width - 10, 70)
                if result_rect.collidepoint(pygame.mouse.get_pos()):
                    pygame.draw.rect(screen, LIGHT_BLUE, result_rect)
                else:
                    pygame.draw.rect(screen, WHITE, result_rect)
                pygame.draw.rect(screen, DARK_BLUE, result_rect, 1)

                # Download cover on-demand if needed
                if album['image_url'] and album['id'] not in album_covers:
                    try:
                        print(f"DEBUG: discogs_handling.py - Downloading cover on-demand for {album['title']}")
                        # Download the real cover directly instead of creating visual cover first
                        real_cover = await download_and_resize_album_cover_async(album['image_url'], 50, 50)
                        if real_cover:
                            album_covers[album['id']] = real_cover
                            print(f"DEBUG: discogs_handling.py - Downloaded real cover for {album['title']}")
                        else:
                            print(f"DEBUG: discogs_handling.py - Failed to download real cover for {album['title']}, using fallback")
                            album_covers[album['id']] = create_fallback_album_cover(50, 50)
                    except Exception as e:
                        print(f"DEBUG: discogs_handling.py - Exception in on-demand download: {e}")
                        album_covers[album['id']] = create_fallback_album_cover(50, 50)

                # Draw the cover
                if album['id'] in album_covers and album_covers[album['id']]:
                    cover = album_covers[album['id']]
                    # Add a background rectangle to make the cover more visible
                    cover_rect = pygame.Rect(result_rect.x + 10, result_rect.y + 10, 60, 60)
                    pygame.draw.rect(screen, (100, 100, 100), cover_rect)  # Gray background
                    # Scale the cover to be larger and more visible
                    scaled_cover = pygame.transform.scale(cover, (60, 60))
                    screen.blit(scaled_cover, (result_rect.x + 10, result_rect.y + 10))
                    text_start_x = result_rect.x + 80
                else:
                    # Create a fallback cover for albums without images
                    fallback_cover = create_fallback_album_cover(50, 50)
                    album_covers[album['id']] = fallback_cover
                    # Draw the fallback cover
                    cover_rect = pygame.Rect(result_rect.x + 10, result_rect.y + 10, 60, 60)
                    pygame.draw.rect(screen, (100, 100, 100), cover_rect)  # Gray background
                    scaled_cover = pygame.transform.scale(fallback_cover, (60, 60))
                    screen.blit(scaled_cover, (result_rect.x + 10, result_rect.y + 10))
                    text_start_x = result_rect.x + 80
                
                name_font_local = pygame.font.SysFont('corbel', 18)
                name_surf = name_font_local.render(album['title'], True, BLACK)
                screen.blit(name_surf, (text_start_x, result_rect.y + 10))
                artist_font_local = pygame.font.SysFont('corbel', 16)
                artist_surf = artist_font_local.render(album['artist'], True, DARK_GREY)
                screen.blit(artist_surf, (text_start_x, result_rect.y + 35))
                y_offset += 80
        elif text:
            no_results_surf = font.render("Press Enter to search", True, WHITE)
            screen.blit(no_results_surf, (results_area.x + 10, results_area.y + 10))
        else:
            no_results_surf = font.render("Press Enter to search", True, WHITE)
            screen.blit(no_results_surf, (results_area.x + 10, results_area.y + 10))

    loop_iteration = 0
    while True:
        loop_iteration += 1
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                print("DEBUG: discogs_handling.py - User quit during album search UI")
                print("DEBUG: discogs_handling.py - get_album_search_input returning USER_ABORT_GAME_FROM_SEARCH")
                return USER_ABORT_GAME_FROM_SEARCH
            if event.type == pygame.MOUSEBUTTONDOWN:
                if input_box.collidepoint(event.pos):
                    active = not active
                else:
                    active = False
                color = color_active if active else color_inactive
                if quit_button_rect_local.collidepoint(event.pos):
                    print("DEBUG: discogs_handling.py - User clicked BACK TO MENU during album search UI")
                    print("DEBUG: discogs_handling.py - get_album_search_input returning BACK_TO_MENU")
                    return "BACK_TO_MENU"
                if search_results:
                    y_offset_click = results_area.y + 10
                    for album_click in search_results:
                        result_rect_click = pygame.Rect(results_area.x + 5, y_offset_click, results_area.width - 10, 70)
                        if result_rect_click.collidepoint(event.pos):
                            print(f"DEBUG: discogs_handling.py - User selected album: {album_click}")
                            print("DEBUG: discogs_handling.py - get_album_search_input returning album result")
                            return album_click
                        y_offset_click += 80
            if event.type == pygame.KEYDOWN:
                if active:
                    if event.key == pygame.K_RETURN:
                        if text:
                            print(f"DEBUG: discogs_handling.py - Searching for: {text}")
                            
                            # Set loading state and search
                            is_searching = True
                            print("DEBUG: discogs_handling.py - Loading state set to True")
                            
                            # Force a UI update to show loading message
                            screen.fill((30, 30, 30))
                            if game_bg:
                                screen.blit(game_bg, (0, 0))
                            else:
                                screen.fill(DARK_GREY)
                            label_font = pygame.font.SysFont("Press Start 2P", 25)
                            label = label_font.render("Search for an album:", True, WHITE)
                            screen.blit(label, (input_box.x, input_box.y - 40))
                            txt_surface = font.render(text, True, BLACK)
                            screen.blit(txt_surface, (input_box.x + 5, input_box.y + 5))
                            pygame.draw.rect(screen, color, input_box, 2)
                            await draw_search_results_local()
                            pygame.draw.rect(screen, LIGHT_BLUE, quit_button_rect_local)
                            quit_text_surf = quit_button_font.render("BACK TO MENU", True, BLACK)
                            quit_text_rect = quit_text_surf.get_rect(center=quit_button_rect_local.center)
                            screen.blit(quit_text_surf, quit_text_rect)
                            pygame.display.flip()
                            
                            # Small delay to make loading message visible
                            await asyncio.sleep(0.3)
                            
                            # Use Discogs search
                            search_results = []
                            discogs_results = await search_album_via_discogs(text)
                            
                            if discogs_results and 'results' in discogs_results:
                                albums_found = len(discogs_results['results'])
                                
                                # Filter and deduplicate albums by title and artist
                                unique_albums = []
                                seen_combinations = set()
                                
                                for album in discogs_results['results']:
                                    if album.get('type') == 'release':  # Only include releases
                                        title = album.get('title', 'Unknown Album')
                                        
                                        # Extract artist from title (usually "Artist - Album" format)
                                        if ' - ' in title:
                                            artist, album_name = title.split(' - ', 1)
                                        else:
                                            artist = "Unknown"
                                            album_name = title
                                        
                                        # Create a unique key for artist + album combination
                                        key = f"{artist}|{album_name}"
                                        
                                        if key not in seen_combinations:
                                            seen_combinations.add(key)
                                            album_data = {
                                                'title': title,
                                                'id': album.get('id', 0),
                                                'image_url': album.get('thumb', None),
                                                'artist': artist
                                            }
                                            unique_albums.append(album_data)
                                
                                # Take only the first 5 unique albums
                                search_results = unique_albums[:5]
                                print(f"DEBUG: discogs_handling.py - Found {albums_found} albums, displaying top 5")
                                # Clear any old covers - we'll download them on-demand in the drawing function
                                album_covers.clear()
                                
                                # Clear loading state after search completes - covers will download on-demand
                                is_searching = False
                                print("DEBUG: discogs_handling.py - Loading state set to False (search complete)")
                            else:
                                print(f"DEBUG: discogs_handling.py - No albums found in search results")
                                # Create a fallback result if search fails
                                search_results = [
                                    {
                                        'title': 'Search Failed - Try Again',
                                        'id': 0,
                                        'image_url': None,  # No fallback URL to avoid CORS issues
                                        'artist': 'Unknown Artist'
                                    }
                                ]
                                album_covers.clear()
                                
                                # Clear loading state after everything is complete
                                is_searching = False
                                print("DEBUG: discogs_handling.py - Loading state set to False (no results)")
                    elif event.key == pygame.K_BACKSPACE:
                        text = text[:-1]
                        if not text:
                            search_results = []
                            album_covers.clear()
                    else:
                        text += event.unicode
        screen.fill((30, 30, 30))
        if game_bg:
            screen.blit(game_bg, (0, 0))
        else:
            screen.fill(DARK_GREY)
        label_font = pygame.font.SysFont("Press Start 2P", 25)
        label = label_font.render("Search for an album:", True, WHITE)
        screen.blit(label, (input_box.x, input_box.y - 40))
        txt_surface = font.render(text, True, BLACK)
        screen.blit(txt_surface, (input_box.x + 5, input_box.y + 5))
        
        # Draw blinking cursor when input is active
        if active and cursor_visible:
            # Calculate cursor position based on text width
            text_width = txt_surface.get_width()
            cursor_x = input_box.x + 5 + text_width
            cursor_y = input_box.y + 5
            cursor_height = txt_surface.get_height()
            pygame.draw.line(screen, BLACK, (cursor_x, cursor_y), (cursor_x, cursor_y + cursor_height), 2)
        
        pygame.draw.rect(screen, color, input_box, 2)
        await draw_search_results_local()
        pygame.draw.rect(screen, LIGHT_BLUE, quit_button_rect_local)
        quit_text_surf = quit_button_font.render("BACK TO MENU", True, BLACK)
        quit_text_rect = quit_text_surf.get_rect(center=quit_button_rect_local.center)
        screen.blit(quit_text_surf, quit_text_rect)
        # Update cursor blinking
        cursor_timer += 16  # Approximately 60 FPS
        if cursor_timer >= cursor_blink_rate:
            cursor_visible = not cursor_visible
            cursor_timer = 0
        
        pygame.display.flip()
        await asyncio.sleep(0.01)
    print("DEBUG: discogs_handling.py - get_album_search_input called (END, should never reach here)")

# Placeholder functions for compatibility (no playback in Discogs)
async def play_random_track_from_album(album_id, song_info_updater_callback):
    """Placeholder function - Discogs doesn't have playback"""
    print(f"DEBUG: discogs_handling.py - play_random_track_from_album called (no playback in Discogs)")
    song_info_updater_callback("Discogs Album", "No Playback Available", False)

def play_uri_with_details(track_uri, position_ms=0):
    """Placeholder function - Discogs doesn't have playback"""
    print(f"DEBUG: discogs_handling.py - play_uri_with_details called (no playback in Discogs)")
    return False, "No Playback", "Discogs"

async def safe_pause_playback():
    """Placeholder function - Discogs doesn't have playback"""
    print("DEBUG: discogs_handling.py - safe_pause_playback called (no playback in Discogs)")
    return True

async def cleanup():
    """Placeholder function - Discogs doesn't have playback"""
    print("DEBUG: discogs_handling.py - cleanup called (no playback in Discogs)")
    return True

def setup_page_unload_handler():
    """Placeholder function - Discogs doesn't have playback"""
    print("DEBUG: discogs_handling.py - setup_page_unload_handler called (no playback in Discogs)")
    pass

