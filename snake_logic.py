import pygame
import time
import random
import asyncio
import traceback
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

async def start_game(screen):
    """Initializes and runs the main DiscogSnake game loop, including setup and event handling."""
    print("DEBUG: snake_logic.py - start_game called")
    print(f"DEBUG: snake_logic.py - fruit_image available: {fruit_image is not None}")
    pygame.display.set_caption('DiscogSnake')

    album_result = None
    test_font_object = None

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
        album_cover = await download_and_resize_album_cover_async(album_image_url, width, height)
        if album_cover:
            print("DEBUG: snake_logic.py - Album cover downloaded successfully")
        else:
            print("DEBUG: snake_logic.py - Failed to download album cover, using fallback")
            album_cover = create_fallback_album_cover(width, height)
    except Exception as e:
        print(f"DEBUG: snake_logic.py - Error downloading album cover: {e}")
        album_cover = create_fallback_album_cover(width, height)

    # Cut the album cover into pieces
    print("DEBUG: snake_logic.py - Cutting album cover into pieces")
    album_pieces = cut_image_into_pieces(album_cover, ALBUM_GRID_SIZE, ALBUM_GRID_SIZE)
    print(f"DEBUG: snake_logic.py - Created {len(album_pieces)} album pieces")

    # Initialize game state
    # Snake should be fixed size (5 blocks) and not grow
    snake = [(width//2, height//2), (width//2-GRID_SIZE, height//2), (width//2-GRID_SIZE*2, height//2), 
             (width//2-GRID_SIZE*3, height//2), (width//2-GRID_SIZE*4, height//2)]
    snake_direction = [GRID_SIZE, 0]
    food = None
    score = 0
    game_over = False
    clock = pygame.time.Clock()
    
    # Track revealed album pieces
    revealed_pieces = set()
    
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
        while True:
            x = random.randrange(0, width, GRID_SIZE)
            y = random.randrange(0, height, GRID_SIZE)
            food = (x, y)
            # Don't place food on snake or on revealed album pieces
            if food not in snake and food not in revealed_pieces:
                break

    def draw_snake():
        for segment in snake:
            pygame.draw.rect(screen, GREEN, (segment[0], segment[1], GRID_SIZE, GRID_SIZE))
            pygame.draw.rect(screen, BLACK, (segment[0], segment[1], GRID_SIZE, GRID_SIZE), 1)

    def draw_food():
        if food:
            if fruit_image:
                screen.blit(fruit_image, (food[0], food[1]))
            else:
                pygame.draw.rect(screen, RED, (food[0], food[1], GRID_SIZE, GRID_SIZE))
                pygame.draw.rect(screen, BLACK, (food[0], food[1], GRID_SIZE, GRID_SIZE), 1)

    def draw_album_pieces():
        # Only draw album pieces that have been revealed
        for food_pos in revealed_pieces:
            # Convert food position to album grid position
            grid_x = food_pos[0] // ALBUM_GRID_SIZE
            grid_y = food_pos[1] // ALBUM_GRID_SIZE
            grid_pos = (grid_x, grid_y)
            
            if grid_pos in album_pieces:
                piece = album_pieces[grid_pos]
                # Draw the piece at the food location (not the grid location)
                screen.blit(piece, (food_pos[0], food_pos[1]))

    def draw_ui():
        # Draw score
        score_font = pygame.font.SysFont("Press Start 2P", 20)
        score_text = score_font.render(f"Score: {score}", True, WHITE)
        screen.blit(score_text, (10, 10))
        
        # Draw song info
        song_font = pygame.font.SysFont("Press Start 2P", 16)
        song_text = song_font.render(f"Album: {current_song}", True, WHITE)
        artist_text = song_font.render(f"Artist: {current_artist}", True, WHITE)
        screen.blit(song_text, (10, 40))
        screen.blit(artist_text, (10, 60))
        
        # Draw easter egg indicator
        if is_easter_egg:
            easter_text = song_font.render("EASTER EGG!", True, RED)
            screen.blit(easter_text, (10, 80))

    # Generate initial food
    generate_food()

    print("DEBUG: snake_logic.py - Starting main game loop")
    
    # Main game loop
    while not game_over:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                print("DEBUG: snake_logic.py - QUIT event received")
                await quit_game_async()
                return
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP and snake_direction[1] != GRID_SIZE:
                    snake_direction = [0, -GRID_SIZE]
                elif event.key == pygame.K_DOWN and snake_direction[1] != -GRID_SIZE:
                    snake_direction = [0, GRID_SIZE]
                elif event.key == pygame.K_LEFT and snake_direction[0] != GRID_SIZE:
                    snake_direction = [-GRID_SIZE, 0]
                elif event.key == pygame.K_RIGHT and snake_direction[0] != -GRID_SIZE:
                    snake_direction = [GRID_SIZE, 0]
                elif event.key == pygame.K_ESCAPE:
                    print("DEBUG: snake_logic.py - ESC key pressed, returning to menu")
                    await main_menu()
                    return

        # Move snake
        new_head = (snake[0][0] + snake_direction[0], snake[0][1] + snake_direction[1])
        
        # Check for collisions
        if (new_head[0] < 0 or new_head[0] >= width or 
            new_head[1] < 0 or new_head[1] >= height or 
            new_head in snake):
            print("DEBUG: snake_logic.py - Game over due to collision")
            game_over = True
            break

        # Move snake (fixed size, so we remove tail and add new head)
        snake.pop()  # Remove tail
        snake.insert(0, new_head)  # Add new head
        
        # Check if food is eaten
        if snake[0] == food:
            score += 10
            # Reveal the album piece at the food location
            revealed_pieces.add(food)
            print(f"DEBUG: snake_logic.py - Food eaten, score: {score}, revealed piece at {food}")
            generate_food()
        # Note: snake doesn't grow, so no else clause needed

        # Draw everything
        screen.fill(BLACK)
        
        # Draw snake and food first
        draw_snake()
        draw_food()
        
        # Draw revealed album pieces on top
        draw_album_pieces()
        
        # Draw UI
        draw_ui()
        
        pygame.display.flip()
        clock.tick(SNAKE_SPEED)
        await asyncio.sleep(0.01)

    print("DEBUG: snake_logic.py - Game over, showing final score")
    
    # Game over screen
    game_over_font = pygame.font.SysFont("Press Start 2P", 40)
    score_font = pygame.font.SysFont("Press Start 2P", 30)
    instruction_font = pygame.font.SysFont("Press Start 2P", 20)
    
    game_over_text = game_over_font.render("GAME OVER", True, RED)
    final_score_text = score_font.render(f"Final Score: {score}", True, WHITE)
    instruction_text = instruction_font.render("Press any key to continue", True, WHITE)
    
    game_over_rect = game_over_text.get_rect(center=(width//2, height//2 - 50))
    score_rect = final_score_text.get_rect(center=(width//2, height//2))
    instruction_rect = instruction_text.get_rect(center=(width//2, height//2 + 50))
    
    # Draw game over screen
    screen.fill(BLACK)
    draw_album_pieces()
    screen.blit(game_over_text, game_over_rect)
    screen.blit(final_score_text, score_rect)
    screen.blit(instruction_text, instruction_rect)
    pygame.display.flip()
    
    # Wait for key press
    waiting_for_key = True
    while waiting_for_key:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                await quit_game_async()
                return
            elif event.type == pygame.KEYDOWN:
                waiting_for_key = False
                break
        await asyncio.sleep(0.01)
    
    print("DEBUG: snake_logic.py - Returning to main menu")
    await main_menu()

def create_fallback_album_cover(target_width, target_height):
    """Create a fallback album cover when image download fails"""
    try:
        surface = pygame.Surface((target_width, target_height))
        
        # Create a colorful gradient pattern
        import random
        import time
        
        # Use time to create different patterns each time
        random.seed(int(time.time() * 1000) % 1000)
        
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