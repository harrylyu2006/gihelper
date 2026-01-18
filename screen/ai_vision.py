"""
AI-powered visual analyzer for real-time game analysis
Uses GPT-4 Vision for complex visual understanding
"""
import base64
import cv2
import numpy as np
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass
from openai import OpenAI

from config import get_config


@dataclass
class VisualAnalysis:
    """Result of visual analysis"""
    description: str
    game_state: str  # world, map, menu, dialog, loading
    player_position: Optional[str]  # Description of where player is
    visible_targets: List[str]  # List of visible interactable objects
    suggested_action: Optional[str]
    click_target: Optional[Tuple[int, int]]  # Suggested click position
    move_direction: Optional[str]  # Suggested movement direction
    raw_response: str


class AIVisualAnalyzer:
    """
    AI-powered visual analyzer using GPT-4 Vision
    
    Used for:
    - Understanding complex game scenes
    - Finding teleport locations on map
    - Comparing current state to guide video frames
    """
    
    MAP_ANALYSIS_PROMPT = """你是一个原神游戏地图分析专家。分析这张地图截图，找到指定的传送位置。

请回答以下问题：
1. 当前地图显示的是哪个区域？
2. 地图上可见的传送点（包括七天神像、传送锚点）有哪些？请描述它们的位置。
3. 如果需要传送到"{target}"，应该点击哪个位置？请给出大致的屏幕坐标比例（x%, y%）。

请用JSON格式回复：
```json
{
  "region": "区域名称",
  "waypoints": ["传送点1", "传送点2"],
  "target_found": true/false,
  "click_position": {"x_percent": 50, "y_percent": 50},
  "instructions": "具体操作说明"
}
```"""

    SCENE_ANALYSIS_PROMPT = """你是一个原神游戏画面分析专家。分析当前游戏画面，告诉我：

1. 当前场景是什么？（大世界、地图、菜单、对话、加载等）
2. 角色目前在哪个位置？（描述周围环境）
3. 画面中有什么可交互的物体？（宝箱、神瞳、NPC、采集物等）
4. 有什么重要的UI提示？（F键提示、任务提示等）

请用JSON格式回复：
```json
{
  "scene_type": "world/map/menu/dialog/loading",
  "location_description": "位置描述",
  "interactables": ["可交互物体列表"],
  "ui_prompts": ["UI提示列表"],
  "suggested_action": "建议的下一步操作"
}
```"""

    COMPARISON_PROMPT = """对比这两张原神游戏画面。

第一张是攻略视频的截图（参考画面）。
第二张是当前游戏的实际画面。

请分析：
1. 当前画面与参考画面是否在同一位置？
2. 如果不是，应该如何移动才能到达参考画面的位置？
3. 参考画面中的目标物体在当前画面中是否可见？

请用JSON格式回复：
```json
{
  "same_location": true/false,
  "similarity_score": 0-100,
  "move_direction": "forward/backward/left/right/none",
  "target_visible": true/false,
  "instructions": "具体操作说明"
}
```"""

    def __init__(self):
        self.client: Optional[OpenAI] = None
        self._last_api_key = None
        
    def _ensure_client(self) -> Any:
        """Ensure OpenAI client is initialized"""
        config = get_config()
        
        if (self.client is None or 
            self._last_api_key != config.openai_api_key):
            
            if not config.openai_api_key:
                raise RuntimeError("OpenAI API key not set")
                
            self.client = OpenAI(
                api_key=config.openai_api_key,
                base_url=config.openai_base_url or "https://api.openai.com/v1"
            )
            self._last_api_key = config.openai_api_key
            
        return config
        
    def _image_to_base64(self, image: np.ndarray) -> str:
        """Convert numpy image to base64"""
        _, buffer = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return base64.b64encode(buffer).decode('utf-8')
        
    def analyze_map_for_teleport(
        self, 
        map_image: np.ndarray,
        target_location: str
    ) -> Dict[str, Any]:
        """
        Analyze map image to find teleport target
        
        Args:
            map_image: Screenshot of the map
            target_location: Name of the destination (e.g., "望舒客栈")
            
        Returns:
            Dictionary with analysis results including click position
        """
        config = self._ensure_client()
        
        prompt = self.MAP_ANALYSIS_PROMPT.format(target=target_location)
        
        response = self.client.chat.completions.create(
            model=config.openai_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{self._image_to_base64(map_image)}",
                                "detail": "high"
                            }
                        },
                        {"type": "text", "text": prompt}
                    ]
                }
            ],
            max_tokens=1000,
            temperature=0.3
        )
        
        result_text = response.choices[0].message.content
        return self._parse_json_response(result_text)
        
    def analyze_scene(self, screen: np.ndarray) -> VisualAnalysis:
        """
        Analyze current game scene
        """
        config = self._ensure_client()
        
        response = self.client.chat.completions.create(
            model=config.openai_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{self._image_to_base64(screen)}",
                                "detail": "high"
                            }
                        },
                        {"type": "text", "text": self.SCENE_ANALYSIS_PROMPT}
                    ]
                }
            ],
            max_tokens=800,
            temperature=0.3
        )
        
        result_text = response.choices[0].message.content
        data = self._parse_json_response(result_text)
        
        return VisualAnalysis(
            description=data.get('location_description', ''),
            game_state=data.get('scene_type', 'unknown'),
            player_position=data.get('location_description'),
            visible_targets=data.get('interactables', []),
            suggested_action=data.get('suggested_action'),
            click_target=None,
            move_direction=None,
            raw_response=result_text
        )
        
    def compare_with_reference(
        self, 
        reference_frame: np.ndarray,
        current_screen: np.ndarray
    ) -> Dict[str, Any]:
        """
        Compare current screen with a reference frame from guide video
        """
        config = self._ensure_client()
        
        response = self.client.chat.completions.create(
            model=config.openai_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "参考画面（攻略视频截图）："},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{self._image_to_base64(reference_frame)}",
                                "detail": "high"
                            }
                        },
                        {"type": "text", "text": "当前画面（游戏实时截图）："},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{self._image_to_base64(current_screen)}",
                                "detail": "high"
                            }
                        },
                        {"type": "text", "text": self.COMPARISON_PROMPT}
                    ]
                }
            ],
            max_tokens=800,
            temperature=0.3
        )
        
        result_text = response.choices[0].message.content
        return self._parse_json_response(result_text)
        
    def find_click_target(
        self, 
        screen: np.ndarray,
        target_description: str
    ) -> Optional[Tuple[int, int]]:
        """
        Find where to click based on target description
        
        Args:
            screen: Current screenshot
            target_description: What to click (e.g., "传送按钮", "宝箱", "NPC")
            
        Returns:
            (x, y) pixel coordinates to click, or None if not found
        """
        config = self._ensure_client()
        
        h, w = screen.shape[:2]
        
        prompt = f"""在这张原神游戏截图中找到"{target_description}"的位置。

请回答：
1. 是否在画面中找到了目标？
2. 如果找到了，它在画面中的位置是什么？请给出百分比坐标。

用JSON格式回复：
```json
{{
  "found": true/false,
  "x_percent": 50,
  "y_percent": 50,
  "confidence": "high/medium/low"
}}
```"""

        response = self.client.chat.completions.create(
            model=config.openai_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{self._image_to_base64(screen)}",
                                "detail": "high"
                            }
                        },
                        {"type": "text", "text": prompt}
                    ]
                }
            ],
            max_tokens=300,
            temperature=0.2
        )
        
        result_text = response.choices[0].message.content
        data = self._parse_json_response(result_text)
        
        if data.get('found'):
            x_pct = data.get('x_percent', 50)
            y_pct = data.get('y_percent', 50)
            return (int(w * x_pct / 100), int(h * y_pct / 100))
            
        return None
        
    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Parse JSON from AI response"""
        import json
        import re
        
        # Try to extract JSON from markdown code block
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
                
        # Try to parse entire response as JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
            
        # Return empty dict if parsing fails
        return {"raw_text": text}
