"""
Video frame extractor for analyzing guide videos
"""
import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional, Generator
from dataclasses import dataclass
import base64
from io import BytesIO
from PIL import Image


@dataclass
class VideoFrame:
    """Represents a single video frame"""
    frame_number: int
    timestamp: float  # in seconds
    image: np.ndarray  # RGB numpy array
    
    def to_base64(self, max_size: int = 1024) -> str:
        """Convert frame to base64 string for API calls"""
        # Resize if needed
        h, w = self.image.shape[:2]
        if max(h, w) > max_size:
            scale = max_size / max(h, w)
            new_w = int(w * scale)
            new_h = int(h * scale)
            resized = cv2.resize(self.image, (new_w, new_h))
        else:
            resized = self.image
            
        # Convert to PIL Image
        pil_image = Image.fromarray(resized)
        
        # Save to bytes
        buffer = BytesIO()
        pil_image.save(buffer, format="JPEG", quality=85)
        buffer.seek(0)
        
        # Encode to base64
        return base64.b64encode(buffer.read()).decode('utf-8')
        
    def to_pil(self) -> Image.Image:
        """Convert to PIL Image"""
        return Image.fromarray(self.image)


@dataclass
class VideoInfo:
    """Video metadata"""
    filepath: str
    width: int
    height: int
    fps: float
    total_frames: int
    duration: float  # in seconds
    
    @property
    def formatted_duration(self) -> str:
        """Get duration as MM:SS"""
        mins = int(self.duration // 60)
        secs = int(self.duration % 60)
        return f"{mins:02d}:{secs:02d}"


class VideoExtractor:
    """Extracts and processes frames from video files"""
    
    def __init__(self, video_path: str):
        self.video_path = video_path
        self.capture: Optional[cv2.VideoCapture] = None
        self.info: Optional[VideoInfo] = None
        self._load_video()
        
    def _load_video(self):
        """Load video and extract metadata"""
        self.capture = cv2.VideoCapture(self.video_path)
        
        if not self.capture.isOpened():
            raise ValueError(f"Cannot open video file: {self.video_path}")
            
        width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = self.capture.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps
        
        self.info = VideoInfo(
            filepath=self.video_path,
            width=width,
            height=height,
            fps=fps,
            total_frames=total_frames,
            duration=duration
        )
        
    def get_frame(self, frame_number: int) -> Optional[VideoFrame]:
        """Get a specific frame by number"""
        if not self.capture or frame_number >= self.info.total_frames:
            return None
            
        self.capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = self.capture.read()
        
        if ret:
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            timestamp = frame_number / self.info.fps
            return VideoFrame(
                frame_number=frame_number,
                timestamp=timestamp,
                image=frame_rgb
            )
        return None
        
    def get_frame_at_time(self, timestamp: float) -> Optional[VideoFrame]:
        """Get frame at specific timestamp (in seconds)"""
        frame_number = int(timestamp * self.info.fps)
        return self.get_frame(frame_number)
        
    def extract_frames_at_interval(
        self, 
        interval: float = 1.0,
        start_time: float = 0,
        end_time: Optional[float] = None
    ) -> Generator[VideoFrame, None, None]:
        """
        Extract frames at regular intervals
        
        Args:
            interval: Time between frames in seconds
            start_time: Start time in seconds
            end_time: End time in seconds (None for end of video)
        """
        if end_time is None:
            end_time = self.info.duration
            
        current_time = start_time
        while current_time < end_time:
            frame = self.get_frame_at_time(current_time)
            if frame:
                yield frame
            current_time += interval
            
    def extract_key_frames(
        self,
        threshold: float = 30.0,
        max_frames: int = 100
    ) -> List[VideoFrame]:
        """
        Extract key frames based on scene changes
        
        Uses histogram comparison to detect significant changes
        """
        frames = []
        prev_hist = None
        
        for i in range(0, self.info.total_frames, int(self.info.fps / 2)):  # Check every 0.5 seconds
            frame = self.get_frame(i)
            if not frame:
                continue
                
            # Calculate histogram
            hist = cv2.calcHist(
                [frame.image], 
                [0, 1, 2], 
                None, 
                [8, 8, 8], 
                [0, 256, 0, 256, 0, 256]
            )
            hist = cv2.normalize(hist, hist).flatten()
            
            # Compare with previous frame
            if prev_hist is None:
                frames.append(frame)
            else:
                # Calculate histogram difference
                diff = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CHISQR)
                if diff > threshold:
                    frames.append(frame)
                    
            prev_hist = hist
            
            if len(frames) >= max_frames:
                break
                
        return frames
        
    def extract_uniform_samples(self, num_samples: int) -> List[VideoFrame]:
        """Extract uniformly distributed frames from the video"""
        frames = []
        interval = self.info.total_frames / num_samples
        
        for i in range(num_samples):
            frame_num = int(i * interval)
            frame = self.get_frame(frame_num)
            if frame:
                frames.append(frame)
                
        return frames
        
    def detect_text_regions(self, frame: VideoFrame) -> List[Tuple[int, int, int, int]]:
        """
        Detect regions that might contain text (for subtitle/instruction areas)
        Returns list of (x, y, w, h) bounding boxes
        """
        # Convert to grayscale
        gray = cv2.cvtColor(frame.image, cv2.COLOR_RGB2GRAY)
        
        # Apply edge detection
        edges = cv2.Canny(gray, 50, 150)
        
        # Dilate to connect text regions
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 3))
        dilated = cv2.dilate(edges, kernel, iterations=2)
        
        # Find contours
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        regions = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            # Filter by aspect ratio (text regions are usually wide)
            if w > h * 2 and w > 100:
                regions.append((x, y, w, h))
                
        return regions
        
    def close(self):
        """Release video capture"""
        if self.capture:
            self.capture.release()
            self.capture = None
            
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
