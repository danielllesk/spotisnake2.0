import pygame
import time
import random
import asyncio
import traceback
import math
from discogs_handling import (
    get_album_search_input, download_and_resize_album_cover, download_and_resize_album_cover_async,
    play_random_track_from_album, play_uri_with_details, safe_pause_playback
)
from shared_constants import * 
from ui import start_menu, main_menu, quit_game_async

def render_text_with_outline(text_str, font, main_color, outline_color, thickness):
    """Renders text with a specified outline color and thickness."""
    outline_surfaces = []
    positions = [
        (-thickness, -thickness), ( thickness, -thickness), (-thickness,  thickness), ( thickness,  thickness),
        (-thickness, 0), (thickness, 0), (0, -thickness), (0, thickness)
    ]
    for dx, dy in positions:
        text_surface_outline = font.render(text_str, True, outline_color)
        outline_surfaces.append((text_surface_outline, (dx, dy)))

    # Render the main text
    text_surface_main = font.render(text_str, True, main_color)
    
    final_width = text_surface_main.get_width() + 2 * thickness
    final_height = text_surface_main.get_height() + 2 * thickness

    # Create a new surface with transparency for the combined text and outline
    final_surface = pygame.Surface((final_width, final_height), pygame.SRCALPHA)

    for surf, (dx, dy) in outline_surfaces:
        final_surface.blit(surf, (thickness + dx, thickness + dy))
    
    final_surface.blit(text_surface_main, (thickness, thickness))
    
    return final_surface

def cut_image_into_pieces(image_surface, piece_width, piece_height):
    """Divides a Pygame surface into a grid of smaller pieces (subsurfaces)."""
    pieces = {}
    for row in range(0, image_surface.get_height(), piece_height):
        for col in range(0, image_surface.get_width(), piece_width):
            rect = pygame.Rect(col, row, piece_width, piece_height)
            piece = image_surface.subsurface(rect).copy()
            grid_pos = (col // piece_width, row // piece_height)
            pieces[grid_pos] = piece
    return pieces  # {(x, y): surface, ...}

def create_high_quality_pieces_improved(image_surface, piece_width, piece_height):
    """Creates high-quality pieces with better scaling and anti-aliasing."""
    pieces = {}
    grid_cols = image_surface.get_width() // piece_width
    grid_rows = image_surface.get_height() // piece_height
    
    for row in range(grid_rows):
        for col in range(grid_cols):
            # Extract the piece from the original image
            x = col * piece_width
            y = row * piece_height
            rect = pygame.Rect(x, y, piece_width, piece_height)
            piece = image_surface.subsurface(rect).copy()
            
            # Create a higher resolution temporary surface for better scaling
            temp_size = piece_width * 2  # 2x resolution for better quality
            temp_surface = pygame.Surface((temp_size, temp_size))
            
            # Scale up first for better quality
            scaled_up = pygame.transform.scale(piece, (temp_size, temp_size))
            temp_surface.blit(scaled_up, (0, 0))
            
            # Then scale down to final size with better anti-aliasing
            final_piece = pygame.transform.scale(temp_surface, (piece_width, piece_height))
            
            grid_pos = (col, row)
            pieces[grid_pos] = final_piece
    
    return pieces  # {(x, y): surface, ...}

def create_high_quality_pieces(image_surface, piece_width, piece_height):
    """Creates high-quality pieces by resizing each piece individually for better quality."""
    pieces = {}
    grid_cols = image_surface.get_width() // piece_width
    grid_rows = image_surface.get_height() // piece_height
    
    for row in range(grid_rows):
        for col in range(grid_cols):
            # Extract the piece from the original image
            x = col * piece_width
            y = row * piece_height
            rect = pygame.Rect(x, y, piece_width, piece_height)
            piece = image_surface.subsurface(rect).copy()
            
            # Resize the piece to the target size for better quality
            resized_piece = pygame.transform.scale(piece, (piece_width, piece_height))
            
            grid_pos = (col, row)
            pieces[grid_pos] = resized_piece
    
    return pieces  # {(x, y): surface, ...}

async def wake_up_backend():
    """Wake up the backend by making a simple ping request and wait for confirmation"""
    try:
        print("DEBUG: snake_logic.py - Waking up backend...")
        # Import BACKEND_URL from discogs_handling
        from discogs_handling import BACKEND_URL
        
        # Make a request to wake up the backend and wait for response
        js_code = f'''
        window.backend_wake_up_status = "pending";
        fetch("{BACKEND_URL}/ping", {{
            method: "GET",
            mode: "cors"
        }})
        .then(response => {{
            console.log("Backend wake-up response:", response.status);
            window.backend_wake_up_status = response.status;
        }})
        .catch(error => {{
            console.log("Backend wake-up failed:", error);
            window.backend_wake_up_status = "error";
        }});
        '''
        import js
        js.eval(js_code)
        
        # Wait for backend to respond (up to 10 seconds)
        max_attempts = 20  # 20 attempts * 0.5 seconds = 10 seconds
        for attempt in range(max_attempts):
            await asyncio.sleep(0.5)
            
            # Check if backend responded
            try:
                status = js.window.backend_wake_up_status
                if status == 200:
                    print("DEBUG: snake_logic.py - Backend is ready!")
                    return True
                elif status == "error":
                    print("DEBUG: snake_logic.py - Backend wake-up failed")
                    return False
                # If still pending, continue waiting
            except:
                # If status not set yet, continue waiting
                pass
        
        print("DEBUG: snake_logic.py - Backend wake-up timeout")
        return False
    except Exception as e:
        print(f"DEBUG: snake_logic.py - Backend wake-up failed: {e}")
        return False

async def show_backend_loading_screen(screen):
    """Show a loading screen while backend starts up"""
    print("DEBUG: snake_logic.py - Showing backend loading screen")
    
    # Use better retro fonts
    try:
        font = pygame.font.SysFont("Courier New", 32, bold=True)
        small_font = pygame.font.SysFont("Courier New", 20, bold=True)
    except:
        try:
            font = pygame.font.SysFont("Monaco", 30, bold=True)
            small_font = pygame.font.SysFont("Monaco", 18, bold=True)
        except:
            font = pygame.font.SysFont("Arial", 30, bold=True)
            small_font = pygame.font.SysFont("Arial", 18, bold=True)
    
    loading_text = font.render("WAKING UP BACKEND...", True, WHITE)
    info_text = small_font.render("Please wait while we connect to Discogs", True, LIGHT_GREY)
    
    loading_rect = loading_text.get_rect(center=(width//2, height//2))
    info_rect = info_text.get_rect(center=(width//2, height//2 + 50))
    
    # Show loading screen for a short time
    for i in range(20):  # Show for 1 second (20 * 0.05)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                await quit_game_async()
                return
        
        # Draw background
        if game_bg:
            screen.blit(game_bg, (0, 0))
        else:
            screen.fill(DARK_GREY)
        
        # Draw loading text
        screen.blit(loading_text, loading_rect)
        screen.blit(info_text, info_rect)
        
        pygame.display.flip()
        await asyncio.sleep(0.05)
    
    print("DEBUG: snake_logic.py - Backend loading screen completed")

async def show_click_to_start_screen(screen):
    """Show click to start screen before game begins"""
    print("DEBUG: snake_logic.py - Showing click to start screen")
    
    # Use better retro font
    try:
        font = pygame.font.SysFont("Courier New", 32, bold=True)
    except:
        try:
            font = pygame.font.SysFont("Monaco", 30, bold=True)
        except:
            font = pygame.font.SysFont("Arial", 30, bold=True)
    
    click_text = font.render("CLICK TO START", True, WHITE)
    click_rect = click_text.get_rect(center=(width//2, height//2))
    
    waiting_for_click = True
    while waiting_for_click:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                await quit_game_async()
                return
            elif event.type == pygame.MOUSEBUTTONDOWN:
                waiting_for_click = False
                break
            elif event.type == pygame.KEYDOWN:
                if event.key in [pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE]:
                    waiting_for_click = False
                    break
        
        # Draw background
        if game_bg:
            screen.blit(game_bg, (0, 0))
        else:
            screen.fill(BLACK)
        
        # Draw click text
        screen.blit(click_text, click_rect)
        
        pygame.display.flip()
        await asyncio.sleep(0.01)
    
    print("DEBUG: snake_logic.py - Click to start completed")

async def show_click_to_continue_screen(screen, score):
    """Show click to continue screen after death"""
    print("DEBUG: snake_logic.py - Showing click to continue screen")
    
    # Use better retro font
    try:
        font = pygame.font.SysFont("Courier New", 32, bold=True)
    except:
        try:
            font = pygame.font.SysFont("Monaco", 30, bold=True)
        except:
            font = pygame.font.SysFont("Arial", 30, bold=True)
    
    continue_text = font.render("CLICK TO CONTINUE", True, WHITE)
    score_text = font.render(f"SCORE: {score}", True, WHITE)
    
    continue_rect = continue_text.get_rect(center=(width//2, height//2))
    score_rect = score_text.get_rect(center=(width//2, height//2 + 50))
    
    waiting_for_click = True
    while waiting_for_click:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                await quit_game_async()
                return
            elif event.type == pygame.MOUSEBUTTONDOWN:
                waiting_for_click = False
                break
            elif event.type == pygame.KEYDOWN:
                if event.key in [pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE]:
                    waiting_for_click = False
                    break
        
        # Draw background
        if game_bg:
            screen.blit(game_bg, (0, 0))
        else:
            screen.fill(BLACK)
        
        # Draw text
        screen.blit(continue_text, continue_rect)
        screen.blit(score_text, score_rect)
        
        pygame.display.flip()
        await asyncio.sleep(0.01)
    
    print("DEBUG: snake_logic.py - Click to continue completed")

async def show_game_over_screen(screen, score, album_result, album_pieces, revealed_pieces, won_game=False):
    """Show game over or win screen with two buttons"""
    if won_game:
        print("DEBUG: snake_logic.py - Showing WIN screen")
    else:
        print("DEBUG: snake_logic.py - Showing game over screen")
    
    # Use better retro fonts
    try:
        title_font = pygame.font.SysFont("Courier New", 40, bold=True)
        score_font = pygame.font.SysFont("Courier New", 30, bold=True)
        button_font = pygame.font.SysFont("Courier New", 24, bold=True)
    except:
        try:
            title_font = pygame.font.SysFont("Monaco", 38, bold=True)
            score_font = pygame.font.SysFont("Monaco", 28, bold=True)
            button_font = pygame.font.SysFont("Monaco", 22, bold=True)
        except:
            title_font = pygame.font.SysFont("Arial", 38, bold=True)
            score_font = pygame.font.SysFont("Arial", 28, bold=True)
            button_font = pygame.font.SysFont("Arial", 22, bold=True)
    
    if won_game:
        game_over_text = title_font.render("YOU DA GOAT!", True, GREEN)
        final_score_text = score_font.render(f"FINAL SCORE: {score}", True, WHITE)
    else:
        game_over_text = title_font.render("GAME OVER", True, RED)
        final_score_text = score_font.render(f"FINAL SCORE: {score}", True, WHITE)
    
    # Create two buttons
    retry_button = pygame.Rect(width//2 - 220, height//2 + 20, 200, 50)
    new_game_button = pygame.Rect(width//2 + 20, height//2 + 20, 200, 50)
    
    retry_text = button_font.render("RETRY ALBUM", True, BLACK)
    new_game_text = button_font.render("NEW GAME", True, BLACK)
    
    retry_text_rect = retry_text.get_rect(center=retry_button.center)
    new_game_text_rect = new_game_text.get_rect(center=new_game_button.center)
    
    game_over_rect = game_over_text.get_rect(center=(width//2, height//2 - 50))
    score_rect = final_score_text.get_rect(center=(width//2, height//2))
    
    # Game over screen loop
    waiting_for_input = True
    while waiting_for_input:
        mouse_pos = pygame.mouse.get_pos()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                await quit_game_async()
                return
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if retry_button.collidepoint(event.pos):
                    print("DEBUG: snake_logic.py - Retry button clicked, restarting game with same album")
                    waiting_for_input = False
                    # Restart the game with the same album
                    await start_game(screen, album_result)
                    return
                elif new_game_button.collidepoint(event.pos):
                    print("DEBUG: snake_logic.py - New game button clicked, going to search")
                    waiting_for_input = False
                    # Go back to album search
                    await start_game(screen)
                    return
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    print("DEBUG: snake_logic.py - R key pressed, restarting game")
                    waiting_for_input = False
                    await start_game(screen, album_result)
                    return
                elif event.key == pygame.K_n:
                    print("DEBUG: snake_logic.py - N key pressed, going to search")
                    waiting_for_input = False
                    await start_game(screen)
                    return
        
        # Draw game over screen
        if game_bg:
            screen.blit(game_bg, (0, 0))
        else:
            screen.fill(BLACK)
        
        # Draw revealed album pieces
        for pos in revealed_pieces:
            # Draw the piece at its proper grid position
            px, py = pos[0] * ALBUM_GRID_SIZE, pos[1] * ALBUM_GRID_SIZE
            if pos in album_pieces:
                screen.blit(album_pieces[pos], (px, py))
        
        screen.blit(game_over_text, game_over_rect)
        screen.blit(final_score_text, score_rect)
        
        # Draw buttons with hover effects
        retry_color = DARK_BLUE if retry_button.collidepoint(mouse_pos) else LIGHT_BLUE
        new_game_color = DARK_BLUE if new_game_button.collidepoint(mouse_pos) else LIGHT_BLUE
        
        pygame.draw.rect(screen, retry_color, retry_button)
        pygame.draw.rect(screen, new_game_color, new_game_button)
        pygame.draw.rect(screen, BLACK, retry_button, 2)
        pygame.draw.rect(screen, BLACK, new_game_button, 2)
        screen.blit(retry_text, retry_text_rect)
        screen.blit(new_game_text, new_game_text_rect)
        
        pygame.display.flip()
        await asyncio.sleep(0.01)
    
    print("DEBUG: snake_logic.py - Game over screen completed")

async def start_game(screen, album_result=None):
    """Initializes and runs the main DiscogSnake game loop, including setup and event handling."""
    print("DEBUG: snake_logic.py - start_game called")
    print(f"DEBUG: snake_logic.py - fruit_image available: {fruit_image is not None}")
    pygame.display.set_caption('DiscogSnake')

    # Show loading screen (backend wake-up moved to start menu)
    await show_backend_loading_screen(screen)

    test_font_object = None

    # If album_result is provided (retry), skip album search
    if album_result is None:
        try:
            test_font_object = pygame.font.SysFont('corbel', 20)
            print("DEBUG: snake_logic.py - Font loaded successfully")
        except Exception as e:
            print(f"DEBUG: snake_logic.py - Font loading failed: {e}")
            traceback.print_exc()
            await asyncio.sleep(1)
            try:
                fallback_font = pygame.font.SysFont('sans', 20) 
                print("DEBUG: snake_logic.py - Using fallback font")
                album_result = await get_album_search_input(screen, fallback_font)
            except Exception as e:
                print(f"DEBUG: snake_logic.py - Fallback font also failed: {e}")
                traceback.print_exc()
                await start_menu()
                return
        else:
            try:
                print("DEBUG: snake_logic.py - Getting album search input")
                album_result = await get_album_search_input(screen, test_font_object)
                print(f"DEBUG: snake_logic.py - Album search result: {album_result}")
            except Exception as e:
                print(f"DEBUG: snake_logic.py - Album search failed: {e}")
                traceback.print_exc()
                await start_menu()
                return
    else:
        print("DEBUG: snake_logic.py - Using provided album_result for retry")

    # Extra debug: ensure album_result is valid
    if album_result == USER_ABORT_GAME_FROM_SEARCH:
        print("DEBUG: snake_logic.py - User aborted from search (album_result == USER_ABORT_GAME_FROM_SEARCH)")
        await quit_game_async()
        return
    
    if album_result == "BACK_TO_MENU":
        print("DEBUG: snake_logic.py - User chose back to menu (album_result == BACK_TO_MENU)")
        await start_menu()
        return
    
    if not album_result:
        print("DEBUG: snake_logic.py - No album selected, returning to menu")
        await start_menu()
        return

    print(f"DEBUG: snake_logic.py - Album selected: {album_result}")
    
    # Extract album information
    album_title = album_result.get('title', 'Unknown Album')
    album_artist = album_result.get('artist', 'Unknown Artist')
    album_image_url = album_result.get('image_url', None)
    album_id = album_result.get('id', 0)
    
    print(f"DEBUG: snake_logic.py - Album title: {album_title}")
    print(f"DEBUG: snake_logic.py - Album artist: {album_artist}")
    print(f"DEBUG: snake_logic.py - Album image URL: {album_image_url}")
    print(f"DEBUG: snake_logic.py - Album ID: {album_id}")

    # Download and process the album cover
    print("DEBUG: snake_logic.py - Downloading album cover")
    try:
        # Download the original image and upscale it for better quality pieces
        print(f"DEBUG: snake_logic.py - Original URL: {album_image_url}")
        
        # Try a more conservative approach - download at original size and scale less aggressively
        print(f"DEBUG: snake_logic.py - Using conservative scaling approach")
        
        # Download at higher quality 300x300 size first
        original_cover = await download_and_resize_album_cover_async(album_image_url, 300, 300)
        if original_cover:
            print(f"DEBUG: snake_logic.py - Downloaded original 300x300 image")
            
            # Scale directly to final size for better quality
            album_cover = pygame.transform.scale(original_cover, (width, height))
            print(f"DEBUG: snake_logic.py - Final scale to {width}x{height}")
        else:
            print(f"DEBUG: snake_logic.py - Failed to download original image, using fallback")
            album_cover = create_fallback_album_cover(width, height)
        if album_cover:
            print(f"DEBUG: snake_logic.py - Downloaded {width}x{height} image directly")
            print("DEBUG: snake_logic.py - Album cover downloaded successfully")
        else:
            print(f"DEBUG: snake_logic.py - Failed to download image, using fallback")
            album_cover = create_fallback_album_cover(width, height)
    except Exception as e:
        print(f"DEBUG: snake_logic.py - Error downloading album cover: {e}")
        album_cover = create_fallback_album_cover(width, height)

    # Cut the album cover into pieces with different approach
    print("DEBUG: snake_logic.py - Cutting album cover into pieces")
    # Try using the original cut method but with better source image
    album_pieces = cut_image_into_pieces(album_cover, ALBUM_GRID_SIZE, ALBUM_GRID_SIZE)
    print(f"DEBUG: snake_logic.py - Created {len(album_pieces)} album pieces")

    # Initialize game state
    # Snake should be fixed size (5 blocks) and not grow
    snake_pos = [width//2, height//2]
    snake_body = [[snake_pos[0] - i * GRID_SIZE, snake_pos[1]] for i in range(5)]
    snake_direction = [GRID_SIZE, 0]
    food = None
    score = 0
    game_over = False
    clock = pygame.time.Clock()
    
    # Track revealed album pieces
    revealed_pieces = set()
    
    # Game state
    won_game = False
    
    # Song info display
    current_song = "Discogs Album"
    current_artist = album_artist
    is_easter_egg = False

    def update_song_info(song_name, artist_name, easter_egg=False):
        nonlocal current_song, current_artist, is_easter_egg
        current_song = song_name
        current_artist = artist_name
        is_easter_egg = easter_egg
        print(f"DEBUG: snake_logic.py - Song info updated: {song_name} by {artist_name}")

    # Start playing music (placeholder for Discogs)
    print("DEBUG: snake_logic.py - Starting album playback (placeholder)")
    try:
        await play_random_track_from_album(album_id, update_song_info)
        print("DEBUG: snake_logic.py - Album playback started")
    except Exception as e:
        print(f"DEBUG: snake_logic.py - Failed to start album playback: {e}")
        update_song_info("Discogs Album", album_artist, False)

    def generate_food():
        nonlocal food
        attempts = 0
        while attempts < 100:  # Prevent infinite loop
            x = random.randrange(0, width, GRID_SIZE)
            y = random.randrange(0, height, GRID_SIZE)
            food = (x, y)
            # Don't place food on snake or on revealed album grid positions
            fruit_album_grid = (food[0] // ALBUM_GRID_SIZE, food[1] // ALBUM_GRID_SIZE)
            if food not in snake_body and fruit_album_grid not in revealed_pieces:
                print(f"DEBUG: snake_logic.py - Generated food at {food}, revealed pieces: {len(revealed_pieces)}")
                break
            attempts += 1
        
        if attempts >= 100:
            print("DEBUG: snake_logic.py - Warning: Could not find valid food position after 100 attempts")
            # Fallback: find any available position
            for x in range(0, width, GRID_SIZE):
                for y in range(0, height, GRID_SIZE):
                    pos = (x, y)
                    pos_album_grid = (pos[0] // ALBUM_GRID_SIZE, pos[1] // ALBUM_GRID_SIZE)
                    if pos not in snake_body and pos_album_grid not in revealed_pieces:
                        food = pos
                        print(f"DEBUG: snake_logic.py - Fallback food at {food}")
                return


    def draw_food():
        if food:
            # Add bouncing animation to fruit
            bounce_offset = int(5 * abs(math.sin(time.time() * 3)))  # Bounce up and down
            
            if fruit_image:
                screen.blit(fruit_image, (food[0], food[1] - bounce_offset))
        else:
                pygame.draw.rect(screen, RED, (food[0], food[1] - bounce_offset, GRID_SIZE, GRID_SIZE))
                pygame.draw.rect(screen, BLACK, (food[0], food[1] - bounce_offset, GRID_SIZE, GRID_SIZE), 1)

    def draw_album_pieces():
        # Only draw album pieces that have been revealed
        for pos in revealed_pieces:
            # Draw the piece at its proper grid position like the original
            px, py = pos[0] * ALBUM_GRID_SIZE, pos[1] * ALBUM_GRID_SIZE
            if pos in album_pieces:
                screen.blit(album_pieces[pos], (px, py))
        
    def draw_ui():
        # Use better retro fonts
        try:
            score_font = pygame.font.SysFont("Courier New", 20, bold=True)
            info_font = pygame.font.SysFont("Courier New", 16, bold=True)
        except:
            try:
                score_font = pygame.font.SysFont("Monaco", 18, bold=True)
                info_font = pygame.font.SysFont("Monaco", 14, bold=True)
            except:
                score_font = pygame.font.SysFont("Arial", 18, bold=True)
                info_font = pygame.font.SysFont("Arial", 14, bold=True)
        
        # Draw score
        score_text = score_font.render(f"SCORE: {score}", True, WHITE)
        screen.blit(score_text, (10, 10))
        
        # Draw album and speed info
        album_text = info_font.render(f"ALBUM: {album_title}", True, WHITE)
        speed_text = info_font.render(f"SPEED: {current_speed:.1f}", True, WHITE)
        screen.blit(album_text, (10, 40))
        screen.blit(speed_text, (10, 60))
        
        # Draw easter egg indicator
        if is_easter_egg:
            easter_text = info_font.render("EASTER EGG!", True, RED)
            screen.blit(easter_text, (10, 80))

    # Initialize random seed for this game session
    import random
    import time
    random.seed(time.time())  # Use current time for true randomness
    
    # Generate initial food
    generate_food()

    print("DEBUG: snake_logic.py - Starting main game loop")
    
    # Click to start screen
    await show_click_to_start_screen(screen)
    
    # Speed progression variables
    current_speed = 7  # Start at 7
    speed_increase_interval = 5  # Increase every 5 pieces
    pieces_eaten = 0
    
    # Input buffering to prevent rapid direction changes
    direction_changed_this_frame = False
    
    # Main game loop
    while not game_over:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                print("DEBUG: snake_logic.py - QUIT event received")
                await quit_game_async()
                return
            elif event.type == pygame.KEYDOWN and not direction_changed_this_frame:
                if event.key == pygame.K_UP and snake_direction[1] != GRID_SIZE:
                    snake_direction = [0, -GRID_SIZE]
                    direction_changed_this_frame = True
                elif event.key == pygame.K_DOWN and snake_direction[1] != -GRID_SIZE:
                    snake_direction = [0, GRID_SIZE]
                    direction_changed_this_frame = True
                elif event.key == pygame.K_LEFT and snake_direction[0] != GRID_SIZE:
                    snake_direction = [-GRID_SIZE, 0]
                    direction_changed_this_frame = True
                elif event.key == pygame.K_RIGHT and snake_direction[0] != -GRID_SIZE:
                    snake_direction = [GRID_SIZE, 0]
                    direction_changed_this_frame = True
                elif event.key == pygame.K_ESCAPE:
                    print("DEBUG: snake_logic.py - ESC key pressed, returning to menu")
                    await main_menu()
                    return

        # Move snake
        new_head = (snake_body[0][0] + snake_direction[0], snake_body[0][1] + snake_direction[1])
        
        # Check for collisions
        if (new_head[0] < 0 or new_head[0] >= width or 
            new_head[1] < 0 or new_head[1] >= height or 
            new_head in snake_body):
            print(f"DEBUG: snake_logic.py - Game over due to collision at {new_head}")
            game_over = True
            break
        
        # Check for win condition (all album pieces revealed)
        if len(revealed_pieces) >= 100:  # 10x10 grid = 100 pieces
            print(f"DEBUG: snake_logic.py - WIN! All album pieces revealed!")
            game_over = True
            won_game = True
            break

        # Move snake (fixed size, so we remove tail and add new head)
        snake_body.pop()  # Remove tail
        snake_body.insert(0, new_head)  # Add new head
        
        # Check if food is eaten
        if snake_body[0] == food:
            score += 10
            pieces_eaten += 1
            # Reveal the album piece at the grid position like the original
            fruit_album_grid = (food[0] // ALBUM_GRID_SIZE, food[1] // ALBUM_GRID_SIZE)
            if fruit_album_grid not in revealed_pieces:
                revealed_pieces.add(fruit_album_grid)
                print(f"DEBUG: snake_logic.py - Food eaten, score: {score}, revealed piece at grid {fruit_album_grid}")
            else:
                print(f"DEBUG: snake_logic.py - Warning: Grid position {fruit_album_grid} already revealed!")
            
            # Increase speed every 5 pieces
            if pieces_eaten % speed_increase_interval == 0:
                current_speed += 1
                print(f"DEBUG: snake_logic.py - Speed increased to {current_speed}")
            
            # Generate new food after revealing the piece
            generate_food()
        # Note: snake doesn't grow, so no else clause needed

        # Draw everything
        # Use background image instead of black
        if game_bg:
            screen.blit(game_bg, (0, 0))
        else:
            screen.fill(BLACK)
        
        # Draw revealed album pieces first (background)
        draw_album_pieces()
        
        # Draw snake as individual blocks
        for block in snake_body:
            pygame.draw.rect(screen, GREEN, pygame.Rect(block[0], block[1], GRID_SIZE, GRID_SIZE))
        
        # Draw food on top
        draw_food()
        
        # Draw UI
        draw_ui()
        
        pygame.display.flip()
        # Use async sleep for better performance like the original
        await asyncio.sleep(1/current_speed)
        
        # Reset direction change flag for next frame
        direction_changed_this_frame = False

    print("DEBUG: snake_logic.py - Game over, showing click to continue")
    
    # First show click to continue screen
    await show_click_to_continue_screen(screen, score)
    
    # Then show game over/win screen with two buttons
    await show_game_over_screen(screen, score, album_result, album_pieces, revealed_pieces, won_game)

def create_fallback_album_cover(target_width, target_height):
    """Create a fallback album cover when image download fails"""
    try:
        surface = pygame.Surface((target_width, target_height))
        
        # Create a colorful gradient pattern
        import random
        import time
        
        # Don't set random seed - let it be truly random
        
        for y in range(target_height):
            for x in range(target_width):
                progress_x = x / target_width
                progress_y = y / target_height
                
                r = int(128 + 127 * (progress_x + random.random() * 0.3))
                g = int(128 + 127 * (progress_y + random.random() * 0.3))
                b = int(128 + 127 * ((progress_x + progress_y) / 2 + random.random() * 0.3))
                
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
        print(f"DEBUG: snake_logic.py - Error creating fallback album cover: {e}")
        return None