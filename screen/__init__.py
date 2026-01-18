"""
Screen capture and recognition module for Genshin Auto-Guide Helper
"""
from .capture import ScreenCapture
from .detector import GameDetector, GameState, DetectedObject
from .template_matcher import TemplateMatcher, MatchResult
from .ocr import GameOCR, TextRegion
from .ai_vision import AIVisualAnalyzer, VisualAnalysis

__all__ = ['ScreenCapture', 'GameDetector']
