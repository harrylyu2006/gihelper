"""
Game controller for automating mouse and keyboard input
"""
import time
import platform
from typing import Tuple, Optional, List
from dataclasses import dataclass
from enum import Enum
import threading
from queue import Queue

# Import automation libraries
try:
    import pyautogui
    pyautogui.FAILSAFE = True  # Move mouse to corner to abort
    pyautogui.PAUSE = 0.01  # Minimal pause between actions
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

# Windows-specific for game input
if platform.system() == 'Windows':
    try:
        import pydirectinput
        pydirectinput.FAILSAFE = True
        DIRECTINPUT_AVAILABLE = True
    except ImportError:
        DIRECTINPUT_AVAILABLE = False
else:
    DIRECTINPUT_AVAILABLE = False


class InputMode(Enum):
    """Input mode for the controller"""
    PYAUTOGUI = "pyautogui"  # Works everywhere but may not work in games
    DIRECTINPUT = "directinput"  # Windows only, better for games


@dataclass
class ActionResult:
    """Result of an action"""
    success: bool
    message: str = ""
    

class GameController:
    """
    Controls game through mouse and keyboard input
    
    Uses pydirectinput on Windows for better game compatibility,
    falls back to pyautogui on other platforms.
    """
    
    # Key mappings for Genshin Impact
    KEY_FORWARD = 'w'
    KEY_BACKWARD = 's'
    KEY_LEFT = 'a'
    KEY_RIGHT = 'd'
    KEY_JUMP = 'space'
    KEY_INTERACT = 'f'
    KEY_ATTACK = None  # Mouse click
    KEY_ELEMENTAL_SKILL = 'e'
    KEY_ELEMENTAL_BURST = 'q'
    KEY_SPRINT = 'shift'
    KEY_MAP = 'm'
    KEY_INVENTORY = 'b'
    KEY_ESCAPE = 'escape'
    KEY_CHARACTER_1 = '1'
    KEY_CHARACTER_2 = '2'
    KEY_CHARACTER_3 = '3'
    KEY_CHARACTER_4 = '4'
    
    def __init__(
        self, 
        action_delay_ms: int = 100,
        prefer_directinput: bool = True
    ):
        self.action_delay = action_delay_ms / 1000.0  # Convert to seconds
        
        # Determine input mode
        if prefer_directinput and DIRECTINPUT_AVAILABLE:
            self.mode = InputMode.DIRECTINPUT
            self._input = pydirectinput
        elif PYAUTOGUI_AVAILABLE:
            self.mode = InputMode.PYAUTOGUI
            self._input = pyautogui
        else:
            raise RuntimeError("No input library available")
            
        # State tracking
        self.is_paused = False
        self.is_emergency_stopped = False
        self._pressed_keys = set()
        
        # Action queue for async operations
        self._action_queue = Queue()
        self._worker_thread = None
        
    def _delay(self):
        """Apply action delay"""
        time.sleep(self.action_delay)
        
    def is_available(self) -> bool:
        """Check if controller is available"""
        return self._input is not None
        
    # ================== Mouse Control ==================
    
    def move_mouse(self, x: int, y: int, duration: float = 0.1) -> ActionResult:
        """Move mouse to absolute position"""
        if self.is_paused or self.is_emergency_stopped:
            return ActionResult(False, "Controller is paused or stopped")
            
        try:
            if self.mode == InputMode.DIRECTINPUT:
                # pydirectinput doesn't support duration, move instantly
                self._input.moveTo(x, y)
            else:
                self._input.moveTo(x, y, duration=duration)
            self._delay()
            return ActionResult(True)
        except Exception as e:
            return ActionResult(False, str(e))
            
    def move_mouse_relative(self, dx: int, dy: int) -> ActionResult:
        """Move mouse relative to current position"""
        if self.is_paused or self.is_emergency_stopped:
            return ActionResult(False, "Controller is paused or stopped")
            
        try:
            self._input.move(dx, dy)
            self._delay()
            return ActionResult(True)
        except Exception as e:
            return ActionResult(False, str(e))
            
    def click(self, button: str = 'left') -> ActionResult:
        """Click mouse button"""
        if self.is_paused or self.is_emergency_stopped:
            return ActionResult(False, "Controller is paused or stopped")
            
        try:
            self._input.click(button=button)
            self._delay()
            return ActionResult(True)
        except Exception as e:
            return ActionResult(False, str(e))
            
    def click_at(self, x: int, y: int, button: str = 'left') -> ActionResult:
        """Move to position and click"""
        result = self.move_mouse(x, y)
        if not result.success:
            return result
        return self.click(button)
        
    def drag(
        self, 
        start_x: int, 
        start_y: int, 
        end_x: int, 
        end_y: int,
        duration: float = 0.5
    ) -> ActionResult:
        """Drag from start to end position"""
        if self.is_paused or self.is_emergency_stopped:
            return ActionResult(False, "Controller is paused or stopped")
            
        try:
            self.move_mouse(start_x, start_y)
            if self.mode == InputMode.PYAUTOGUI:
                self._input.drag(
                    end_x - start_x,
                    end_y - start_y,
                    duration=duration
                )
            else:
                # Manual drag for directinput
                self._input.mouseDown()
                time.sleep(0.05)
                self._input.moveTo(end_x, end_y)
                time.sleep(0.05)
                self._input.mouseUp()
            self._delay()
            return ActionResult(True)
        except Exception as e:
            return ActionResult(False, str(e))
            
    def rotate_camera(self, dx: int, dy: int = 0) -> ActionResult:
        """Rotate camera by dragging (for game camera control)"""
        return self.move_mouse_relative(dx, dy)
        
    # ================== Keyboard Control ==================
    
    def press_key(self, key: str) -> ActionResult:
        """Press and release a key"""
        if self.is_paused or self.is_emergency_stopped:
            return ActionResult(False, "Controller is paused or stopped")
            
        try:
            self._input.press(key)
            self._delay()
            return ActionResult(True)
        except Exception as e:
            return ActionResult(False, str(e))
            
    def hold_key(self, key: str) -> ActionResult:
        """Hold down a key (remember to release!)"""
        if self.is_paused or self.is_emergency_stopped:
            return ActionResult(False, "Controller is paused or stopped")
            
        try:
            self._input.keyDown(key)
            self._pressed_keys.add(key)
            return ActionResult(True)
        except Exception as e:
            return ActionResult(False, str(e))
            
    def release_key(self, key: str) -> ActionResult:
        """Release a held key"""
        try:
            self._input.keyUp(key)
            self._pressed_keys.discard(key)
            return ActionResult(True)
        except Exception as e:
            return ActionResult(False, str(e))
            
    def release_all_keys(self):
        """Release all held keys"""
        for key in list(self._pressed_keys):
            self.release_key(key)
        self._pressed_keys.clear()
        
    def type_text(self, text: str, interval: float = 0.05) -> ActionResult:
        """Type text"""
        if self.is_paused or self.is_emergency_stopped:
            return ActionResult(False, "Controller is paused or stopped")
            
        try:
            if self.mode == InputMode.PYAUTOGUI:
                self._input.typewrite(text, interval=interval)
            else:
                for char in text:
                    self._input.press(char)
                    time.sleep(interval)
            self._delay()
            return ActionResult(True)
        except Exception as e:
            return ActionResult(False, str(e))
            
    # ================== Game-Specific Actions ==================
    
    def move_forward(self, duration: float = 1.0) -> ActionResult:
        """Move character forward"""
        return self._hold_and_release(self.KEY_FORWARD, duration)
        
    def move_backward(self, duration: float = 1.0) -> ActionResult:
        """Move character backward"""
        return self._hold_and_release(self.KEY_BACKWARD, duration)
        
    def move_left(self, duration: float = 1.0) -> ActionResult:
        """Move character left"""
        return self._hold_and_release(self.KEY_LEFT, duration)
        
    def move_right(self, duration: float = 1.0) -> ActionResult:
        """Move character right"""
        return self._hold_and_release(self.KEY_RIGHT, duration)
        
    def move_direction(self, direction: str, duration: float = 1.0) -> ActionResult:
        """
        Move in a specified direction
        
        Args:
            direction: 'forward', 'backward', 'left', 'right', 
                      'north', 'south', 'east', 'west',
                      'forward-left', 'forward-right', etc.
            duration: How long to move
        """
        direction = direction.lower()
        
        # Map cardinal directions to relative
        direction_map = {
            'north': 'forward',
            'south': 'backward', 
            'east': 'right',
            'west': 'left'
        }
        direction = direction_map.get(direction, direction)
        
        # Handle compound directions
        keys = []
        if 'forward' in direction:
            keys.append(self.KEY_FORWARD)
        if 'backward' in direction:
            keys.append(self.KEY_BACKWARD)
        if 'left' in direction:
            keys.append(self.KEY_LEFT)
        if 'right' in direction:
            keys.append(self.KEY_RIGHT)
            
        if not keys:
            return ActionResult(False, f"Unknown direction: {direction}")
            
        # Hold all keys
        for key in keys:
            self.hold_key(key)
            
        time.sleep(duration)
        
        # Release all keys
        for key in keys:
            self.release_key(key)
            
        self._delay()
        return ActionResult(True)
        
    def jump(self) -> ActionResult:
        """Jump"""
        return self.press_key(self.KEY_JUMP)
        
    def interact(self) -> ActionResult:
        """Press interact key (F)"""
        return self.press_key(self.KEY_INTERACT)
        
    def attack(self) -> ActionResult:
        """Attack (left click)"""
        return self.click('left')
        
    def charged_attack(self, hold_time: float = 1.0) -> ActionResult:
        """Charged attack (hold left click)"""
        if self.is_paused or self.is_emergency_stopped:
            return ActionResult(False, "Controller is paused or stopped")
            
        try:
            self._input.mouseDown()
            time.sleep(hold_time)
            self._input.mouseUp()
            self._delay()
            return ActionResult(True)
        except Exception as e:
            return ActionResult(False, str(e))
            
    def elemental_skill(self, hold: bool = False, hold_time: float = 1.0) -> ActionResult:
        """Use elemental skill"""
        if hold:
            return self._hold_and_release(self.KEY_ELEMENTAL_SKILL, hold_time)
        return self.press_key(self.KEY_ELEMENTAL_SKILL)
        
    def elemental_burst(self) -> ActionResult:
        """Use elemental burst"""
        return self.press_key(self.KEY_ELEMENTAL_BURST)
        
    def sprint_start(self) -> ActionResult:
        """Start sprinting"""
        return self.hold_key(self.KEY_SPRINT)
        
    def sprint_stop(self) -> ActionResult:
        """Stop sprinting"""
        return self.release_key(self.KEY_SPRINT)
        
    def open_map(self) -> ActionResult:
        """Open/close map"""
        return self.press_key(self.KEY_MAP)
        
    def open_inventory(self) -> ActionResult:
        """Open inventory"""
        return self.press_key(self.KEY_INVENTORY)
        
    def escape(self) -> ActionResult:
        """Press escape"""
        return self.press_key(self.KEY_ESCAPE)
        
    def switch_character(self, slot: int) -> ActionResult:
        """Switch to character in slot (1-4)"""
        if 1 <= slot <= 4:
            return self.press_key(str(slot))
        return ActionResult(False, f"Invalid slot: {slot}")
        
    def _hold_and_release(self, key: str, duration: float) -> ActionResult:
        """Hold a key for duration then release"""
        if self.is_paused or self.is_emergency_stopped:
            return ActionResult(False, "Controller is paused or stopped")
            
        try:
            self._input.keyDown(key)
            time.sleep(duration)
            self._input.keyUp(key)
            self._delay()
            return ActionResult(True)
        except Exception as e:
            self._input.keyUp(key)  # Make sure to release
            return ActionResult(False, str(e))
            
    # ================== Control Methods ==================
    
    def pause(self):
        """Pause all actions"""
        self.is_paused = True
        self.release_all_keys()
        
    def resume(self):
        """Resume actions"""
        self.is_paused = False
        
    def emergency_stop(self):
        """Emergency stop all actions"""
        self.is_emergency_stopped = True
        self.release_all_keys()
        
    def reset(self):
        """Reset controller state"""
        self.is_paused = False
        self.is_emergency_stopped = False
        self.release_all_keys()
        
    def get_mouse_position(self) -> Tuple[int, int]:
        """Get current mouse position"""
        return pyautogui.position() if PYAUTOGUI_AVAILABLE else (0, 0)
