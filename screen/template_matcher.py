"""
Template Matching for UI element detection
Uses OpenCV to find game UI elements like waypoints, buttons, etc.
"""
import cv2
import numpy as np
from typing import List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import os


@dataclass
class MatchResult:
    """Result of a template match"""
    template_name: str
    confidence: float
    location: Tuple[int, int]  # Top-left corner
    center: Tuple[int, int]
    size: Tuple[int, int]  # width, height
    
    @property
    def bounding_box(self) -> Tuple[int, int, int, int]:
        """Get bounding box (x, y, width, height)"""
        return (self.location[0], self.location[1], self.size[0], self.size[1])


class TemplateMatcher:
    """
    Template matching for detecting game UI elements
    
    Uses multi-scale template matching to handle different resolutions
    """
    
    # Default templates directory
    TEMPLATES_DIR = Path(__file__).parent.parent / "assets" / "templates"
    
    # Common game UI element templates
    TEMPLATE_NAMES = {
        "waypoint": "waypoint.png",          # 传送锚点
        "statue": "statue.png",              # 七天神像
        "domain": "domain.png",              # 秘境
        "chest_common": "chest_common.png",  # 普通宝箱
        "chest_exquisite": "chest_exquisite.png",  # 精致宝箱
        "chest_precious": "chest_precious.png",    # 珍贵宝箱
        "chest_luxurious": "chest_luxurious.png",  # 华丽宝箱
        "oculus_anemo": "oculus_anemo.png",  # 风神瞳
        "oculus_geo": "oculus_geo.png",      # 岩神瞳
        "oculus_electro": "oculus_electro.png",  # 雷神瞳
        "oculus_dendro": "oculus_dendro.png",    # 草神瞳
        "interact_prompt": "interact_prompt.png",  # F 交互提示
        "teleport_button": "teleport_button.png",  # 传送按钮
        "confirm_button": "confirm_button.png",    # 确认按钮
    }
    
    def __init__(self, templates_dir: Optional[str] = None):
        self.templates_dir = Path(templates_dir) if templates_dir else self.TEMPLATES_DIR
        self.templates: dict = {}
        self._load_templates()
        
    def _load_templates(self):
        """Load all template images"""
        if not self.templates_dir.exists():
            # Create templates directory if it doesn't exist
            self.templates_dir.mkdir(parents=True, exist_ok=True)
            return
            
        for name, filename in self.TEMPLATE_NAMES.items():
            template_path = self.templates_dir / filename
            if template_path.exists():
                template = cv2.imread(str(template_path), cv2.IMREAD_COLOR)
                if template is not None:
                    self.templates[name] = template
                    
    def add_template(self, name: str, image: np.ndarray):
        """Add a template dynamically"""
        self.templates[name] = image
        
    def save_template(self, name: str, image: np.ndarray):
        """Save a template to disk"""
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        filepath = self.templates_dir / f"{name}.png"
        cv2.imwrite(str(filepath), image)
        self.templates[name] = image
        
    def find_template(
        self, 
        screen: np.ndarray, 
        template_name: str,
        threshold: float = 0.8,
        max_results: int = 10
    ) -> List[MatchResult]:
        """
        Find all occurrences of a template in the screen
        
        Args:
            screen: Screenshot to search in
            template_name: Name of template to find
            threshold: Minimum confidence threshold (0-1)
            max_results: Maximum number of results to return
        """
        if template_name not in self.templates:
            return []
            
        template = self.templates[template_name]
        return self._match_template(screen, template, template_name, threshold, max_results)
        
    def find_all_waypoints(
        self, 
        screen: np.ndarray,
        threshold: float = 0.75
    ) -> List[MatchResult]:
        """Find all waypoint-type icons on the map"""
        results = []
        
        waypoint_templates = ["waypoint", "statue", "domain"]
        for name in waypoint_templates:
            matches = self.find_template(screen, name, threshold)
            results.extend(matches)
            
        # Sort by confidence
        results.sort(key=lambda x: x.confidence, reverse=True)
        return results
        
    def find_chests(
        self, 
        screen: np.ndarray,
        threshold: float = 0.7
    ) -> List[MatchResult]:
        """Find all chest icons"""
        results = []
        
        chest_templates = ["chest_common", "chest_exquisite", "chest_precious", "chest_luxurious"]
        for name in chest_templates:
            matches = self.find_template(screen, name, threshold)
            results.extend(matches)
            
        return results
        
    def find_oculi(
        self, 
        screen: np.ndarray,
        threshold: float = 0.7
    ) -> List[MatchResult]:
        """Find all oculus icons"""
        results = []
        
        oculus_templates = ["oculus_anemo", "oculus_geo", "oculus_electro", "oculus_dendro"]
        for name in oculus_templates:
            matches = self.find_template(screen, name, threshold)
            results.extend(matches)
            
        return results
        
    def _match_template(
        self,
        screen: np.ndarray,
        template: np.ndarray,
        template_name: str,
        threshold: float,
        max_results: int
    ) -> List[MatchResult]:
        """Perform template matching with multi-scale support"""
        results = []
        
        # Get template size
        h, w = template.shape[:2]
        
        # Try multiple scales
        scales = [0.5, 0.75, 1.0, 1.25, 1.5]
        
        best_matches = []
        
        for scale in scales:
            # Resize template
            new_w = int(w * scale)
            new_h = int(h * scale)
            
            if new_w < 10 or new_h < 10:
                continue
            if new_w > screen.shape[1] or new_h > screen.shape[0]:
                continue
                
            scaled_template = cv2.resize(template, (new_w, new_h))
            
            # Perform matching
            result = cv2.matchTemplate(screen, scaled_template, cv2.TM_CCOEFF_NORMED)
            
            # Find locations above threshold
            locations = np.where(result >= threshold)
            
            for pt in zip(*locations[::-1]):  # Switch x and y
                confidence = result[pt[1], pt[0]]
                center = (pt[0] + new_w // 2, pt[1] + new_h // 2)
                
                best_matches.append(MatchResult(
                    template_name=template_name,
                    confidence=float(confidence),
                    location=pt,
                    center=center,
                    size=(new_w, new_h)
                ))
                
        # Non-maximum suppression to remove overlapping matches
        best_matches = self._non_max_suppression(best_matches, overlap_threshold=0.5)
        
        # Sort by confidence and limit results
        best_matches.sort(key=lambda x: x.confidence, reverse=True)
        return best_matches[:max_results]
        
    def _non_max_suppression(
        self, 
        matches: List[MatchResult],
        overlap_threshold: float = 0.5
    ) -> List[MatchResult]:
        """Remove overlapping matches, keeping the one with highest confidence"""
        if not matches:
            return []
            
        # Sort by confidence
        matches = sorted(matches, key=lambda x: x.confidence, reverse=True)
        
        keep = []
        for match in matches:
            should_keep = True
            for kept in keep:
                # Calculate overlap
                overlap = self._calculate_overlap(match, kept)
                if overlap > overlap_threshold:
                    should_keep = False
                    break
            if should_keep:
                keep.append(match)
                
        return keep
        
    def _calculate_overlap(self, match1: MatchResult, match2: MatchResult) -> float:
        """Calculate IoU (Intersection over Union) between two matches"""
        x1, y1, w1, h1 = match1.bounding_box
        x2, y2, w2, h2 = match2.bounding_box
        
        # Calculate intersection
        xi = max(x1, x2)
        yi = max(y1, y2)
        wi = min(x1 + w1, x2 + w2) - xi
        hi = min(y1 + h1, y2 + h2) - yi
        
        if wi <= 0 or hi <= 0:
            return 0.0
            
        intersection = wi * hi
        union = w1 * h1 + w2 * h2 - intersection
        
        return intersection / union if union > 0 else 0.0
        
    def find_button(
        self,
        screen: np.ndarray,
        button_name: str,
        threshold: float = 0.8
    ) -> Optional[MatchResult]:
        """Find a specific button on screen"""
        results = self.find_template(screen, button_name, threshold, max_results=1)
        return results[0] if results else None
        
    def find_interact_prompt(
        self,
        screen: np.ndarray,
        threshold: float = 0.8
    ) -> Optional[MatchResult]:
        """Find the F key interaction prompt"""
        return self.find_button(screen, "interact_prompt", threshold)
        
    def find_teleport_button(
        self,
        screen: np.ndarray,
        threshold: float = 0.8
    ) -> Optional[MatchResult]:
        """Find the teleport confirmation button"""
        return self.find_button(screen, "teleport_button", threshold)


# Helper function to create templates from screenshots
def create_template_from_region(
    screen: np.ndarray,
    x: int, y: int, 
    width: int, height: int,
    name: str,
    matcher: TemplateMatcher
) -> np.ndarray:
    """
    Extract a region from a screenshot and save as template
    
    Usage:
        screen = capture.capture_full_screen()
        # Select region containing waypoint icon
        create_template_from_region(screen, 100, 200, 50, 50, "waypoint", matcher)
    """
    template = screen[y:y+height, x:x+width].copy()
    matcher.save_template(name, template)
    return template
