"""
OCR (Optical Character Recognition) for reading game text
Supports Chinese and English text recognition
"""
import cv2
import numpy as np
from typing import List, Optional, Tuple
from dataclasses import dataclass
import re


@dataclass
class TextRegion:
    """A detected text region"""
    text: str
    confidence: float
    bounding_box: Tuple[int, int, int, int]  # x, y, width, height
    center: Tuple[int, int]
    
    
class GameOCR:
    """
    OCR for reading game text
    
    Uses either:
    - Tesseract OCR (if installed)
    - PaddleOCR (if installed)
    - Simple template-based digit recognition as fallback
    """
    
    def __init__(self):
        self.engine = None
        self._init_ocr_engine()
        
    def _init_ocr_engine(self):
        """Initialize the best available OCR engine"""
        # Try PaddleOCR first (better for Chinese)
        try:
            from paddleocr import PaddleOCR
            self.engine = PaddleOCR(use_angle_cls=True, lang='ch', show_log=False)
            self.engine_type = 'paddle'
            return
        except ImportError:
            pass
            
        # Try Tesseract
        try:
            import pytesseract
            # Test if tesseract is available
            pytesseract.get_tesseract_version()
            self.engine = pytesseract
            self.engine_type = 'tesseract'
            return
        except Exception:
            pass
            
        # No OCR engine available, use fallback
        self.engine = None
        self.engine_type = 'none'
        
    def read_text(
        self, 
        image: np.ndarray,
        lang: str = 'chi_sim+eng'
    ) -> List[TextRegion]:
        """
        Read all text from image
        
        Args:
            image: Image to read text from
            lang: Language code (for Tesseract)
        """
        if self.engine_type == 'paddle':
            return self._read_paddle(image)
        elif self.engine_type == 'tesseract':
            return self._read_tesseract(image, lang)
        else:
            return []
            
    def _read_paddle(self, image: np.ndarray) -> List[TextRegion]:
        """Read text using PaddleOCR"""
        results = []
        
        try:
            ocr_result = self.engine.ocr(image, cls=True)
            
            if ocr_result and ocr_result[0]:
                for line in ocr_result[0]:
                    box = line[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                    text_info = line[1]  # (text, confidence)
                    
                    # Get bounding box
                    x_coords = [p[0] for p in box]
                    y_coords = [p[1] for p in box]
                    x = int(min(x_coords))
                    y = int(min(y_coords))
                    w = int(max(x_coords) - x)
                    h = int(max(y_coords) - y)
                    
                    results.append(TextRegion(
                        text=text_info[0],
                        confidence=text_info[1],
                        bounding_box=(x, y, w, h),
                        center=(x + w // 2, y + h // 2)
                    ))
        except Exception:
            pass
            
        return results
        
    def _read_tesseract(self, image: np.ndarray, lang: str) -> List[TextRegion]:
        """Read text using Tesseract"""
        results = []
        
        try:
            # Get detailed data
            data = self.engine.image_to_data(
                image, 
                lang=lang,
                output_type=self.engine.Output.DICT
            )
            
            n_boxes = len(data['text'])
            for i in range(n_boxes):
                text = data['text'][i].strip()
                conf = int(data['conf'][i])
                
                if text and conf > 0:
                    x = data['left'][i]
                    y = data['top'][i]
                    w = data['width'][i]
                    h = data['height'][i]
                    
                    results.append(TextRegion(
                        text=text,
                        confidence=conf / 100.0,
                        bounding_box=(x, y, w, h),
                        center=(x + w // 2, y + h // 2)
                    ))
        except Exception:
            pass
            
        return results
        
    def find_text(
        self, 
        image: np.ndarray, 
        target_text: str,
        fuzzy: bool = True
    ) -> Optional[TextRegion]:
        """
        Find specific text in image
        
        Args:
            image: Image to search
            target_text: Text to find
            fuzzy: Allow partial matches
        """
        regions = self.read_text(image)
        
        target_lower = target_text.lower()
        
        for region in regions:
            text_lower = region.text.lower()
            if fuzzy:
                if target_lower in text_lower or text_lower in target_lower:
                    return region
            else:
                if text_lower == target_lower:
                    return region
                    
        return None
        
    def find_waypoint_name(
        self, 
        image: np.ndarray, 
        waypoint_name: str
    ) -> Optional[TextRegion]:
        """Find a waypoint name on the map"""
        return self.find_text(image, waypoint_name, fuzzy=True)
        
    def read_coordinates(
        self, 
        image: np.ndarray
    ) -> Optional[Tuple[float, float]]:
        """
        Read coordinate numbers from image
        Returns (x, y) coordinates if found
        """
        regions = self.read_text(image)
        
        # Look for coordinate pattern like "123.4, 567.8" or "X: 123 Y: 456"
        for region in regions:
            # Try to extract numbers
            numbers = re.findall(r'-?\d+\.?\d*', region.text)
            if len(numbers) >= 2:
                try:
                    x = float(numbers[0])
                    y = float(numbers[1])
                    return (x, y)
                except ValueError:
                    continue
                    
        return None
        
    def preprocess_for_ocr(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess image for better OCR results
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
            
        # Enhance contrast
        gray = cv2.equalizeHist(gray)
        
        # Threshold to get black text on white background
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return thresh


class MapTextFinder:
    """
    Specialized text finder for map interface
    """
    
    def __init__(self):
        self.ocr = GameOCR()
        
    def find_region_name(
        self, 
        map_image: np.ndarray
    ) -> Optional[str]:
        """Find the current region name on the map"""
        # Region name is usually in the top-left area
        h, w = map_image.shape[:2]
        region_area = map_image[0:int(h*0.15), 0:int(w*0.4)]
        
        regions = self.ocr.read_text(region_area)
        
        # Find the largest/most prominent text
        if regions:
            regions.sort(key=lambda r: r.bounding_box[2] * r.bounding_box[3], reverse=True)
            return regions[0].text
            
        return None
        
    def find_waypoint_labels(
        self, 
        map_image: np.ndarray
    ) -> List[TextRegion]:
        """Find all waypoint/location labels on the map"""
        regions = self.ocr.read_text(map_image)
        
        # Filter for likely location names (Chinese characters, reasonable length)
        location_regions = []
        for region in regions:
            text = region.text.strip()
            # Check if it looks like a location name
            if len(text) >= 2 and len(text) <= 20:
                # Contains Chinese characters
                if any('\u4e00' <= char <= '\u9fff' for char in text):
                    location_regions.append(region)
                    
        return location_regions
