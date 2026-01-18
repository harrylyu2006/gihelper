"""
Game navigator for high-level navigation actions
"""
import time
from typing import Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum

from .controller import GameController, ActionResult
from screen.capture import ScreenCapture
from screen.detector import GameDetector, GameState, DetectedObject


class NavigationState(Enum):
    """Navigation state"""
    IDLE = "idle"
    MOVING = "moving"
    TURNING = "turning"
    INTERACTING = "interacting"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class NavigationTarget:
    """Target for navigation"""
    x: int
    y: int
    description: str = ""
    interact: bool = False  # Whether to interact when reached
    
    
class Navigator:
    """
    High-level game navigator
    
    Handles complex navigation like:
    - Moving to a position on screen
    - Following waypoints
    - Interacting with objects
    - Using the map for teleportation
    """
    
    def __init__(
        self,
        controller: Optional[GameController] = None,
        screen_capture: Optional[ScreenCapture] = None,
        detector: Optional[GameDetector] = None
    ):
        self.controller = controller or GameController()
        self.screen = screen_capture or ScreenCapture()
        self.detector = detector or GameDetector()
        
        self.state = NavigationState.IDLE
        self.is_running = False
        
    def get_current_screen(self):
        """Get current game screen"""
        return self.screen.capture_full_screen(monitor=1)
        
    def check_game_state(self) -> GameState:
        """Check current game state"""
        screen = self.get_current_screen()
        return self.detector.detect_game_state(screen)
        
    # ================== Basic Navigation ==================
    
    def turn_to_direction(
        self, 
        target_direction: float,
        current_direction: float = 0
    ) -> ActionResult:
        """
        Turn camera to face a direction
        
        Args:
            target_direction: Target angle in degrees (0 = north)
            current_direction: Current facing (if known)
        """
        # Calculate turn amount
        diff = target_direction - current_direction
        
        # Normalize to -180 to 180
        while diff > 180:
            diff -= 360
        while diff < -180:
            diff += 360
            
        # Convert to mouse movement (rough approximation)
        # Full 360 degree turn is approximately 1500 pixels
        pixels = int(diff * 1500 / 360)
        
        self.state = NavigationState.TURNING
        result = self.controller.rotate_camera(pixels, 0)
        self.state = NavigationState.IDLE
        
        return result
        
    def move_towards_screen_point(
        self,
        target_x: int,
        target_y: int,
        duration: float = 1.0
    ) -> ActionResult:
        """
        Move towards a point visible on screen
        
        The character will turn and move in that direction.
        """
        screen = self.get_current_screen()
        dx, dy = self.detector.calculate_direction_to_target(
            screen, target_x, target_y
        )
        
        # Determine movement direction based on screen position
        # Screen right = turn right, screen left = turn left
        # Screen top = move forward, screen bottom = already there
        
        self.state = NavigationState.MOVING
        
        # Turn camera if target is off center horizontally
        if abs(dx) > 0.1:
            turn_amount = int(dx * 200)  # Scale for mouse movement
            self.controller.rotate_camera(turn_amount, 0)
            time.sleep(0.2)
            
        # Move forward if target is above center
        if dy < -0.1:  # Target is in upper part of screen = further away
            result = self.controller.move_forward(duration)
        else:
            result = ActionResult(True, "Target is close")
            
        self.state = NavigationState.IDLE
        return result
        
    def approach_and_interact(
        self,
        target_x: int,
        target_y: int,
        max_attempts: int = 5
    ) -> ActionResult:
        """
        Move towards a target and interact with it
        """
        for attempt in range(max_attempts):
            # Check if interaction prompt is visible
            screen = self.get_current_screen()
            prompt = self.detector.detect_interaction_prompt(screen)
            
            if prompt:
                # Found interaction prompt, interact
                self.state = NavigationState.INTERACTING
                result = self.controller.interact()
                time.sleep(0.5)
                self.state = NavigationState.IDLE
                return result
                
            # Move closer
            self.move_towards_screen_point(target_x, target_y, duration=0.5)
            time.sleep(0.3)
            
        return ActionResult(False, "Could not reach interaction point")
        
    # ================== Map Navigation ==================
    
    def open_map_and_wait(self, timeout: float = 3.0) -> bool:
        """Open map and wait for it to load"""
        self.controller.open_map()
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            state = self.check_game_state()
            if state == GameState.MAP:
                return True
            time.sleep(0.2)
            
        return False
        
    def close_map(self) -> bool:
        """Close the map"""
        self.controller.escape()
        time.sleep(0.5)
        return self.check_game_state() != GameState.MAP
        
    def teleport_to_waypoint(
        self,
        waypoint_screen_x: int,
        waypoint_screen_y: int
    ) -> ActionResult:
        """
        Teleport to a waypoint at the given map coordinates
        
        Assumes map is already open and waypoint is visible.
        """
        # Click on waypoint
        self.controller.click_at(waypoint_screen_x, waypoint_screen_y)
        time.sleep(0.5)
        
        # Look for teleport button (usually appears near bottom right)
        # This is a simplified version - real implementation would detect the button
        screen = self.get_current_screen()
        h, w = screen.shape[:2]
        
        # Teleport button is usually in the bottom right panel
        teleport_x = int(w * 0.85)
        teleport_y = int(h * 0.75)
        
        self.controller.click_at(teleport_x, teleport_y)
        time.sleep(0.5)
        
        # Wait for teleport (loading screen)
        start_time = time.time()
        while time.time() - start_time < 10:
            state = self.check_game_state()
            if state == GameState.LOADING:
                # Wait for loading to complete
                time.sleep(1)
            elif state == GameState.WORLD:
                return ActionResult(True, "Teleported successfully")
            time.sleep(0.5)
            
        return ActionResult(False, "Teleport timeout")
        
    # ================== Object Collection ==================
    
    def collect_nearby_item(
        self,
        item_type: str = "any"
    ) -> ActionResult:
        """
        Look for and collect a nearby item
        """
        screen = self.get_current_screen()
        
        objects = []
        if item_type in ("any", "chest"):
            objects.extend(self.detector.detect_chests(screen))
        if item_type in ("any", "oculus"):
            objects.extend(self.detector.detect_oculi(screen))
            
        if not objects:
            return ActionResult(False, "No collectible objects found")
            
        # Get closest object (to screen center)
        center = self.detector.get_screen_center(screen)
        closest = min(
            objects,
            key=lambda o: (o.x - center[0])**2 + (o.y - center[1])**2
        )
        
        return self.approach_and_interact(closest.x, closest.y)
        
    # ================== Dialog Handling ==================
    
    def skip_dialog(self, timeout: float = 10.0) -> ActionResult:
        """
        Skip through dialog by clicking
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            state = self.check_game_state()
            
            if state != GameState.DIALOG:
                return ActionResult(True, "Dialog ended")
                
            # Click to advance
            self.controller.click()
            time.sleep(0.3)
            
        return ActionResult(False, "Dialog timeout")
        
    def wait_for_dialog_end(self, timeout: float = 30.0) -> bool:
        """Wait for dialog to end naturally"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            state = self.check_game_state()
            if state != GameState.DIALOG:
                return True
            time.sleep(0.5)
            
        return False
        
    # ================== Utility Methods ==================
    
    def wait_for_game_ready(self, timeout: float = 30.0) -> bool:
        """Wait for game to be in playable state"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            state = self.check_game_state()
            if state == GameState.WORLD:
                return True
            time.sleep(0.5)
            
        return False
        
    def stop(self):
        """Stop navigation"""
        self.is_running = False
        self.controller.release_all_keys()
        self.state = NavigationState.IDLE
        
    def emergency_stop(self):
        """Emergency stop"""
        self.is_running = False
        self.controller.emergency_stop()
        self.state = NavigationState.FAILED
