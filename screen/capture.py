"""
Screen capture module for capturing game screenshots
"""
import numpy as np
from typing import Optional, Tuple, List
import platform
from dataclasses import dataclass
from PIL import Image

# Import mss for cross-platform screen capture
try:
    import mss
    import mss.tools
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False

# Platform-specific imports
if platform.system() == 'Windows':
    try:
        import win32gui
        import win32ui
        import win32con
        import win32api
        WIN32_AVAILABLE = True
    except ImportError:
        WIN32_AVAILABLE = False
else:
    WIN32_AVAILABLE = False


@dataclass
class WindowInfo:
    """Information about a window"""
    hwnd: int  # Window handle
    title: str
    x: int
    y: int
    width: int
    height: int
    
    @property
    def rect(self) -> Tuple[int, int, int, int]:
        """Get (left, top, right, bottom) rectangle"""
        return (self.x, self.y, self.x + self.width, self.y + self.height)
        
    @property
    def center(self) -> Tuple[int, int]:
        """Get center point"""
        return (self.x + self.width // 2, self.y + self.height // 2)


class ScreenCapture:
    """Handles screen and window capture"""
    
    def __init__(self):
        # We don't initialize persistent mss here anymore to avoid threading issues
        # on macOS. Instead we create a new instance for each capture.
        pass
            
    def capture_full_screen(self, monitor: int = 1) -> np.ndarray:
        """
        Capture full screen
        
        Args:
            monitor: Monitor index (1 = first monitor)
            
        Returns:
            RGB numpy array
        """
        if not MSS_AVAILABLE:
            raise RuntimeError("MSS not available for screen capture")
            
        with mss.mss() as sct:
            # Get monitor info (handle case where monitor index out of range)
            if monitor >= len(sct.monitors):
                monitor = 1  # Fallback to primary
            
            mon = sct.monitors[monitor]
            
            # Capture
            screenshot = sct.grab(mon)
            
            # Convert to numpy array (BGRA format)
            img = np.array(screenshot)
            
            # Convert BGRA to RGB
            return img[:, :, :3][:, :, ::-1]
        
    def capture_region(
        self, 
        left: int, 
        top: int, 
        width: int, 
        height: int
    ) -> np.ndarray:
        """
        Capture a specific region of the screen
        
        Returns:
            RGB numpy array
        """
        if not MSS_AVAILABLE:
            raise RuntimeError("MSS not available for screen capture")
            
        with mss.mss() as sct:
            region = {
                'left': int(left),
                'top': int(top),
                'width': int(width),
                'height': int(height)
            }
            
            screenshot = sct.grab(region)
            img = np.array(screenshot)
            return img[:, :, :3][:, :, ::-1]
        
    def capture_window(self, window_info: WindowInfo) -> Optional[np.ndarray]:
        """
        Capture a specific window
        
        Returns:
            RGB numpy array or None if failed
        """
        return self.capture_region(
            window_info.x,
            window_info.y,
            window_info.width,
            window_info.height
        )
        
    @staticmethod
    def find_windows(title_contains: str = "") -> List[WindowInfo]:
        """
        Find windows by title
        
        Args:
            title_contains: Substring to search for in window title
            
        Returns:
            List of matching windows
        """
        windows = []
        
        if platform.system() == 'Windows' and WIN32_AVAILABLE:
            def enum_callback(hwnd, results):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if title_contains.lower() in title.lower():
                        try:
                            rect = win32gui.GetWindowRect(hwnd)
                            x, y, right, bottom = rect
                            width = right - x
                            height = bottom - y
                            
                            if width > 0 and height > 0:
                                results.append(WindowInfo(
                                    hwnd=hwnd,
                                    title=title,
                                    x=x,
                                    y=y,
                                    width=width,
                                    height=height
                                ))
                        except:
                            pass
                return True
                
            win32gui.EnumWindows(enum_callback, windows)
        else:
            # For non-Windows platforms, we can use wmctrl or xdotool on Linux
            # For macOS, we would need Quartz
            # For now, return empty list
            pass
            
        return windows
        
    @staticmethod
    def find_game_window(game_title: str = "原神") -> Optional[WindowInfo]:
        """
        Find the game window
        
        Args:
            game_title: Window title to search for
            
        Returns:
            WindowInfo if found, None otherwise
        """
        windows = ScreenCapture.find_windows(game_title)
        
        # Return the first match, prioritizing exact matches
        for window in windows:
            if window.title == game_title:
                return window
                
        return windows[0] if windows else None
        
    @staticmethod
    def bring_window_to_front(window_info: WindowInfo) -> bool:
        """
        Bring window to foreground
        
        Returns:
            True if successful
        """
        if platform.system() == 'Windows' and WIN32_AVAILABLE:
            try:
                win32gui.SetForegroundWindow(window_info.hwnd)
                return True
            except:
                pass
        return False
        
    @staticmethod
    def get_screen_size() -> Tuple[int, int]:
        """Get primary screen size"""
        if MSS_AVAILABLE:
            with mss.mss() as sct:
                mon = sct.monitors[1]  # Primary monitor
                return mon['width'], mon['height']
        return (1920, 1080)  # Default fallback
        
    def to_pil_image(self, img_array: np.ndarray) -> Image.Image:
        """Convert numpy array to PIL Image"""
        return Image.fromarray(img_array)
        
    def save_screenshot(self, img_array: np.ndarray, filepath: str):
        """Save screenshot to file"""
        img = Image.fromarray(img_array)
        img.save(filepath)
        
    def close(self):
        """Clean up resources"""
        if self.sct:
            self.sct.close()
            self.sct = None
            
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
