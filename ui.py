print("UI MODULE LOADED")
print("DEBUG: ui.py - Starting UI module initialization")

import pygame
print("DEBUG: ui.py - Importing pygame")
pygame.init()
print("DEBUG: ui.py - Pygame initialized in ui module")
pygame.font.init()
print("DEBUG: ui.py - Pygame font initialized in ui module")
import asyncio
import sys
import os
import time
print("DEBUG: ui.py - Importing shared_constants")
from shared_constants import *
print("DEBUG: ui.py - shared_constants imported successfully")
print(f"DEBUG: ui.py - fruit_image available: {fruit_image is not None}")
print("DEBUG: ui.py - Importing discogs_handling functions")
from discogs_handling import (
    get_album_search_input, cleanup, safe_pause_playback, play_uri_with_details
)
print("DEBUG: ui.py - All imports completed successfully")

print("DEBUG: ui.py - Setting up pygame display")
screen = pygame.display.set_mode((width, height))
print(f"DEBUG: ui.py - Display set to {width}x{height}")
pygame.display.set_caption("DiscogSnake - Start Menu")
print("DEBUG: ui.py - Window caption set")
font = pygame.font.SysFont("Press Start 2P", 25)
print("DEBUG: ui.py - Font initialized")

async def quit_game_async(dummy_arg=None):
    """Handles game shutdown: cleans up and exits properly for PyInstaller."""
    print("DEBUG: ui.py - quit_game_async called")
    try:
        print("DEBUG: ui.py - Calling cleanup")
        await cleanup()
        print("DEBUG: ui.py - Cleanup completed")
    except Exception as e:
        print(f"DEBUG: ui.py - Exception during cleanup: {e}")
        pass
    
    # Proper exit for PyInstaller
    try:
        print("DEBUG: ui.py - Quitting pygame")
        pygame.quit()
        print("DEBUG: ui.py - Pygame quit successfully")
    except Exception as e:
        print(f"DEBUG: ui.py - Exception during pygame quit: {e}")
        pass
    
    # Force exit if running as executable
    if getattr(sys, 'frozen', False):
        print("DEBUG: ui.py - Running as frozen executable, using os._exit(0)")
        os._exit(0)
    else:
        print("DEBUG: ui.py - Running as script, using sys.exit(0)")
        sys.exit(0)

async def back_to_menu():
    """Returns to the start menu instead of quitting."""
    print("DEBUG: ui.py - back_to_menu called")
    print("DEBUG: ui.py - back_to_menu completed")
    # Just return to menu - no need to quit pygame

async def start_menu():
    """Displays the main start menu."""
    print("DEBUG: ui.py - start_menu called")
    
    # Wake up backend once at the start
    from snake_logic import wake_up_backend
    await wake_up_backend()
    
    clock = pygame.time.Clock()
    
    # Main menu button - positioned 3/4 down the page
    play_button = pygame.Rect(width//2 - 100, int(height * 0.75) - 25, 200, 50)
    
    # Use a better retro font - try multiple options
    try:
        button_font = pygame.font.SysFont("Courier New", 28, bold=True)
    except:
        try:
            button_font = pygame.font.SysFont("Monaco", 26, bold=True)
        except:
            try:
                button_font = pygame.font.SysFont("Consolas", 26, bold=True)
            except:
                button_font = pygame.font.SysFont("Arial", 26, bold=True)
    
    play_text = button_font.render("PLAY GAME", True, BLACK)
    
    play_text_rect = play_text.get_rect(center=play_button.center)
    
    while True:
        mouse_pos = pygame.mouse.get_pos()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                await quit_game_async()
                return
            if event.type == pygame.MOUSEBUTTONDOWN:
                if play_button.collidepoint(event.pos):
                    print("DEBUG: ui.py - Play button clicked")
                    await start_game(screen)
                    return
        
        # Draw background
        if start_menu_bg:
            screen.blit(start_menu_bg, (0, 0))
        else:
            screen.fill(DARK_GREY)
        
        # Draw button with hover effect
        button_color = DARK_BLUE if play_button.collidepoint(mouse_pos) else LIGHT_BLUE
        pygame.draw.rect(screen, button_color, play_button)
        pygame.draw.rect(screen, BLACK, play_button, 2)
        
        # Draw button text
        screen.blit(play_text, play_text_rect)
        
        pygame.display.flip()
        clock.tick(60)
        await asyncio.sleep(0.01)

async def main_menu():
    """Displays the main menu after game completion."""
    print("DEBUG: ui.py - main_menu called")
    clock = pygame.time.Clock()
    
    # Menu buttons
    play_again_button = pygame.Rect(width//2 - 150, height//2 - 50, 300, 50)
    menu_button = pygame.Rect(width//2 - 150, height//2 + 20, 300, 50)
    quit_button = pygame.Rect(width//2 - 150, height//2 + 90, 300, 50)
    
    title_font = pygame.font.SysFont("Press Start 2P", 40)
    button_font = pygame.font.SysFont("Press Start 2P", 25)
    
    title = title_font.render("GAME OVER", True, WHITE)
    play_again_text = button_font.render("PLAY AGAIN", True, BLACK)
    menu_text = button_font.render("MAIN MENU", True, BLACK)
    quit_text = button_font.render("QUIT", True, BLACK)
    
    title_rect = title.get_rect(center=(width//2, height//2 - 150))
    play_again_text_rect = play_again_text.get_rect(center=play_again_button.center)
    menu_text_rect = menu_text.get_rect(center=menu_button.center)
    quit_text_rect = quit_text.get_rect(center=quit_button.center)
    
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                await quit_game_async()
                return
            if event.type == pygame.MOUSEBUTTONDOWN:
                if play_again_button.collidepoint(event.pos):
                    print("DEBUG: ui.py - Play again button clicked")
                    await start_game(screen)
                    return
                elif menu_button.collidepoint(event.pos):
                    print("DEBUG: ui.py - Main menu button clicked")
                    await start_menu()
                    return
                elif quit_button.collidepoint(event.pos):
                    print("DEBUG: ui.py - Quit button clicked")
                    await quit_game_async()
                    return
        
        # Draw background
        if game_bg:
            screen.blit(game_bg, (0, 0))
        else:
            screen.fill(DARK_GREY)
        
        # Draw title
        screen.blit(title, title_rect)
        
        # Draw buttons
        pygame.draw.rect(screen, LIGHT_BLUE, play_again_button)
        pygame.draw.rect(screen, LIGHT_BLUE, menu_button)
        pygame.draw.rect(screen, LIGHT_BLUE, quit_button)
        pygame.draw.rect(screen, BLACK, play_again_button, 2)
        pygame.draw.rect(screen, BLACK, menu_button, 2)
        pygame.draw.rect(screen, BLACK, quit_button, 2)
        
        # Draw button text
        screen.blit(play_again_text, play_again_text_rect)
        screen.blit(menu_text, menu_text_rect)
        screen.blit(quit_text, quit_text_rect)
        
        pygame.display.flip()
        clock.tick(60)
        await asyncio.sleep(0.01)

# Import the start_game function from snake_logic
from snake_logic import start_game