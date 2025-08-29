# Check if we're running in a backend context (no display)
import os
import sys

# Check if we're in a backend context by looking at the calling module
def is_backend_context():
    """Check if we're running in a backend context"""
    # Check if any frame in the call stack contains 'backend'
    import inspect
    try:
        frame = inspect.currentframe()
        while frame:
            if 'backend' in str(frame.f_globals.get('__file__', '')):
                return True
            frame = frame.f_back
    except:
        pass
    
    # Also check environment variables and command line
    return (os.environ.get('FLASK_APP') or 
            'backend' in sys.argv or 
            any('backend' in arg for arg in sys.argv))

# Only import pygame if we're not in a backend context
if not is_backend_context():
    try:
        import pygame
        import time

        def resource_path(relative_path):
            try:
                base_path = sys._MEIPASS
            except AttributeError:
                base_path = os.path.abspath(".")
            return os.path.join(base_path, relative_path)

        if not pygame.get_init():
            pygame.init()
    except (ImportError, AttributeError):
        pass  # Ignore pygame errors on backend or if not available
else:
    # Backend context - don't import pygame
    pygame = None
    print("DEBUG: shared_constants.py - Running in backend context, skipping pygame import")

# Discogs API configuration
DISCOGS_API_URL = "https://api.discogs.com"
DISCOGS_USER_AGENT = "DiscogSnake/1.0 +https://github.com/yourusername/discogsnake"
DISCOGS_TOKEN = os.environ.get("DISCOGS_TOKEN", "")  # Optional personal access token

# Game dimensions
width = 600
height = 600

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
LIGHT_BLUE = (173, 216, 230)
DARK_BLUE = (0, 0, 139)
LIGHT_GREY = (40,40,40)
DARK_GREY = (30,30,30)

# Game settings
SNAKE_SPEED = 7  # How often the snake moves
GRID_SIZE = 30  # Size for snake movement
ALBUM_GRID_SIZE = 60  # Size for album pieces

# Game states
USER_QUIT_ALBUM_SEARCH = "USER_QUIT_ALBUM_SEARCH"
USER_ABORT_GAME_FROM_SEARCH = "USER_ABORT_GAME_FROM_SEARCH"

# UI settings
OUTLINE_COLOR = BLACK
OUTLINE_THICKNESS = 2 

# Game backgrounds (load by filename only for browser compatibility)
print("DEBUG: shared_constants.py - Starting to load background images")
print("DEBUG: shared_constants.py - Module loaded successfully")

def load_image_simple(filename):
    """Load an image with simple error handling"""
    if pygame is None:
        print(f"DEBUG: shared_constants.py - Skipping {filename} load (backend context)")
        return None
    try:
        print(f"DEBUG: shared_constants.py - Loading {filename}")
        image = pygame.image.load(filename)
        image = pygame.transform.scale(image, (width, height))
        print(f"DEBUG: shared_constants.py - {filename} loaded successfully")
        return image
    except Exception as e:
        print(f"DEBUG: shared_constants.py - Failed to load {filename}: {e}")
        return None

def load_fruit_image():
    """Load the custom fruit image for the game"""
    if pygame is None:
        print("DEBUG: shared_constants.py - Skipping fruit image load (backend context)")
        return None
    try:
        print("DEBUG: shared_constants.py - Loading fruit.png")
        print(f"DEBUG: shared_constants.py - Current working directory: {os.getcwd()}")
        print(f"DEBUG: shared_constants.py - fruit.png exists: {os.path.exists('fruit.png')}")
        fruit_image = pygame.image.load("fruit.png")
        # Scale to GRID_SIZE x GRID_SIZE
        fruit_image = pygame.transform.scale(fruit_image, (GRID_SIZE, GRID_SIZE))
        print(f"DEBUG: shared_constants.py - fruit.png loaded successfully, size: {fruit_image.get_size()}")
        return fruit_image
    except Exception as e:
        print(f"DEBUG: shared_constants.py - Failed to load fruit.png: {e}")
        print("DEBUG: shared_constants.py - Will use white rectangle as fallback")
        return None

# Load images with simple error handling
print("DEBUG: shared_constants.py - Starting to load all images")
game_bg = load_image_simple('background.png')
start_menu_bg = load_image_simple('SpotipyStart.png')
print("DEBUG: shared_constants.py - About to load fruit image")
fruit_image = load_fruit_image()
print(f"DEBUG: shared_constants.py - Fruit image loaded: {fruit_image is not None}")