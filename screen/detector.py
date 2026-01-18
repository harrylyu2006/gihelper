"""
Game state detector using screen recognition
"""
import cv2
import numpy as np
from enum import Enum
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass


class GameState(Enum):
    """Possible game states"""
    UNKNOWN = "unknown"
    MAIN_MENU = "main_menu"
    LOADING = "loading"
    WORLD = "world"  # In the open world
    MAP = "map"  # Map is open
    INVENTORY = "inventory"
    DIALOG = "dialog"  # In conversation
    COMBAT = "combat"
    DOMAIN = "domain"  # In a domain/dungeon
    CUTSCENE = "cutscene"
    PAUSE_MENU = "pause_menu"


@dataclass
class DetectedObject:
    """Represents a detected object in the game"""
    object_type: str  # chest, oculus, enemy, npc, etc.
    x: int  # Center x position
    y: int  # Center y position
    width: int
    height: int
    confidence: float
    
    @property
    def center(self) -> Tuple[int, int]:
        return (self.x, self.y)
        
    @property
    def bbox(self) -> Tuple[int, int, int, int]:
        """Return (x1, y1, x2, y2) bounding box"""
        half_w = self.width // 2
        half_h = self.height // 2
        return (
            self.x - half_w,
            self.y - half_h,
            self.x + half_w,
            self.y + half_h
        )


@dataclass
class MinimapInfo:
    """Information extracted from the minimap"""
    player_direction: float  # Angle in degrees (0 = north)
    has_waypoint: bool
    waypoint_direction: Optional[float] = None  # Direction to waypoint
    
    
class GameDetector:
    """Detects game state and objects from screenshots"""
    
    # UI element positions (relative to 1920x1080 resolution)
    # These need calibration for different resolutions
    MINIMAP_REGION = (55, 45, 210, 200)  # (x, y, w, h) for minimap
    HEALTH_BAR_REGION = (85, 200, 150, 20)  # HP bar
    INTERACTION_PROMPT_REGION = (900, 500, 120, 50)  # "F" prompt area
    DIALOG_REGION = (300, 650, 1320, 150)  # Dialog text area
    
    def __init__(self, resolution: Tuple[int, int] = (1920, 1080)):
        self.resolution = resolution
        self.scale_x = resolution[0] / 1920
        self.scale_y = resolution[1] / 1080
        
    def _scale_region(self, region: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
        """Scale a region to current resolution"""
        x, y, w, h = region
        return (
            int(x * self.scale_x),
            int(y * self.scale_y),
            int(w * self.scale_x),
            int(h * self.scale_y)
        )
        
    def detect_game_state(self, screen: np.ndarray) -> GameState:
        """
        Detect the current game state from screenshot
        
        Args:
            screen: RGB numpy array of the game screen
        """
        # Check if loading (mostly black with loading indicator)
        if self._is_loading_screen(screen):
            return GameState.LOADING
            
        # Check if in dialog (dialog UI at bottom)
        if self._has_dialog_ui(screen):
            return GameState.DIALOG
            
        # Check if map is open (large map UI)
        if self._is_map_open(screen):
            return GameState.MAP
            
        # Check if in pause menu
        if self._is_pause_menu(screen):
            return GameState.PAUSE_MENU
            
        # Check if in main menu
        if self._is_main_menu(screen):
            return GameState.MAIN_MENU
            
        # Default to world if we have minimap
        if self._has_minimap(screen):
            return GameState.WORLD
            
        return GameState.UNKNOWN
        
    def _is_loading_screen(self, screen: np.ndarray) -> bool:
        """Check if screen is a loading screen"""
        # Loading screens are mostly dark
        gray = cv2.cvtColor(screen, cv2.COLOR_RGB2GRAY)
        mean_brightness = np.mean(gray)
        
        # Very dark screen is likely loading
        return mean_brightness < 30
        
    def _has_dialog_ui(self, screen: np.ndarray) -> bool:
        """Check if dialog UI is visible"""
        region = self._scale_region(self.DIALOG_REGION)
        x, y, w, h = region
        
        # Crop dialog region
        dialog_area = screen[y:y+h, x:x+w]
        
        # Dialog boxes typically have a dark semi-transparent background
        gray = cv2.cvtColor(dialog_area, cv2.COLOR_RGB2GRAY)
        
        # Look for the characteristic dialog gradient
        mean_val = np.mean(gray)
        return 20 < mean_val < 80  # Dialog boxes are moderately dark
        
    def _is_map_open(self, screen: np.ndarray) -> bool:
        """Check if the map is open"""
        # When map is open, the center of screen has the map
        h, w = screen.shape[:2]
        center = screen[h//3:2*h//3, w//3:2*w//3]
        
        # Map has lots of light blues and greens
        hsv = cv2.cvtColor(center, cv2.COLOR_RGB2HSV)
        
        # Check for map-like colors (blues, greens)
        lower_blue = np.array([90, 50, 50])
        upper_blue = np.array([130, 255, 255])
        mask = cv2.inRange(hsv, lower_blue, upper_blue)
        
        blue_ratio = np.sum(mask > 0) / mask.size
        return blue_ratio > 0.15  # More than 15% blue = likely map
        
    def _is_pause_menu(self, screen: np.ndarray) -> bool:
        """Check if pause menu is open"""
        # Pause menu darkens the background and shows buttons
        gray = cv2.cvtColor(screen, cv2.COLOR_RGB2GRAY)
        
        # The pause menu has characteristic dark overlay
        mean_brightness = np.mean(gray)
        return 40 < mean_brightness < 70
        
    def _is_main_menu(self, screen: np.ndarray) -> bool:
        """Check if at main menu"""
        # Main menu has the door/login screen
        # This is a simple heuristic
        return False  # Implement if needed
        
    def _has_minimap(self, screen: np.ndarray) -> bool:
        """Check if minimap is visible (indicates in-game)"""
        region = self._scale_region(self.MINIMAP_REGION)
        x, y, w, h = region
        
        # Crop minimap region
        if y + h > screen.shape[0] or x + w > screen.shape[1]:
            return False
            
        minimap = screen[y:y+h, x:x+w]
        
        # Minimap should have varied colors (terrain)
        std_dev = np.std(minimap)
        return std_dev > 30  # Has enough variation to be a minimap
        
    def detect_interaction_prompt(self, screen: np.ndarray) -> Optional[Tuple[int, int]]:
        """
        Detect the 'F' interaction prompt position
        
        Returns:
            (x, y) position of prompt, or None if not found
        """
        # The interaction prompt is usually white/yellow text
        # We'll look for it in the center-right area of screen
        h, w = screen.shape[:2]
        
        # Search region (right side of center)
        search_x = int(w * 0.45)
        search_y = int(h * 0.35)
        search_w = int(w * 0.2)
        search_h = int(h * 0.3)
        
        region = screen[search_y:search_y+search_h, search_x:search_x+search_w]
        
        # Convert to HSV for color detection
        hsv = cv2.cvtColor(region, cv2.COLOR_RGB2HSV)
        
        # Look for bright yellow/white (interaction prompt color)
        lower = np.array([20, 100, 200])
        upper = np.array([40, 255, 255])
        mask = cv2.inRange(hsv, lower, upper)
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            # Get the largest contour
            largest = max(contours, key=cv2.contourArea)
            M = cv2.moments(largest)
            if M['m00'] > 0:
                cx = int(M['m10'] / M['m00']) + search_x
                cy = int(M['m01'] / M['m00']) + search_y
                return (cx, cy)
                
        return None
        
    def detect_minimap_info(self, screen: np.ndarray) -> Optional[MinimapInfo]:
        """
        Extract information from the minimap
        
        Returns:
            MinimapInfo with player direction and waypoint info
        """
        region = self._scale_region(self.MINIMAP_REGION)
        x, y, w, h = region
        
        if y + h > screen.shape[0] or x + w > screen.shape[1]:
            return None
            
        minimap = screen[y:y+h, x:x+w]
        
        # Find player indicator (usually a white/light triangle at center)
        center_x, center_y = w // 2, h // 2
        
        # For now, return a basic info
        # Full implementation would detect the arrow direction
        return MinimapInfo(
            player_direction=0,  # Would need more complex detection
            has_waypoint=False
        )
        
    def detect_chests(self, screen: np.ndarray) -> List[DetectedObject]:
        """
        Detect chest locations on screen
        
        Note: This is a basic color-based detection.
        For better results, use a trained object detection model.
        """
        chests = []
        
        # Chests have golden/brown color
        hsv = cv2.cvtColor(screen, cv2.COLOR_RGB2HSV)
        
        # Golden chest color range
        lower_gold = np.array([15, 100, 100])
        upper_gold = np.array([30, 255, 255])
        mask = cv2.inRange(hsv, lower_gold, upper_gold)
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 500:  # Minimum size threshold
                x, y, w, h = cv2.boundingRect(contour)
                
                # Filter by aspect ratio (chests are roughly square-ish)
                aspect = w / h if h > 0 else 0
                if 0.5 < aspect < 2.0:
                    chests.append(DetectedObject(
                        object_type="chest",
                        x=x + w // 2,
                        y=y + h // 2,
                        width=w,
                        height=h,
                        confidence=0.5  # Basic detection has low confidence
                    ))
                    
        return chests
        
    def detect_oculi(self, screen: np.ndarray) -> List[DetectedObject]:
        """
        Detect oculi (Anemoculus, Geoculus, etc.) on screen
        
        Note: This is a basic color-based detection.
        """
        oculi = []
        
        # Oculi glow with specific colors
        hsv = cv2.cvtColor(screen, cv2.COLOR_RGB2HSV)
        
        # Cyan glow (Anemo) - common in early game
        lower_cyan = np.array([85, 150, 150])
        upper_cyan = np.array([100, 255, 255])
        mask = cv2.inRange(hsv, lower_cyan, upper_cyan)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 200:
                x, y, w, h = cv2.boundingRect(contour)
                oculi.append(DetectedObject(
                    object_type="oculus",
                    x=x + w // 2,
                    y=y + h // 2,
                    width=w,
                    height=h,
                    confidence=0.4
                ))
                
        return oculi
        
    def get_screen_center(self, screen: np.ndarray) -> Tuple[int, int]:
        """Get screen center point (where player/crosshair is)"""
        h, w = screen.shape[:2]
        return (w // 2, h // 2)
        
    def calculate_direction_to_target(
        self, 
        screen: np.ndarray,
        target_x: int,
        target_y: int
    ) -> Tuple[float, float]:
        """
        Calculate direction from screen center to target
        
        Returns:
            (dx, dy) normalized direction vector
        """
        center_x, center_y = self.get_screen_center(screen)
        
        dx = target_x - center_x
        dy = target_y - center_y
        
        # Normalize
        magnitude = (dx**2 + dy**2) ** 0.5
        if magnitude > 0:
            dx /= magnitude
            dy /= magnitude
            
        return (dx, dy)
