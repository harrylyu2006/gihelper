"""
AI-powered video analyzer using GPT-4 Vision
"""
import json
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum
import re

from openai import OpenAI

from .extractor import VideoFrame, VideoExtractor
from config import get_config


class ActionType(Enum):
    """Types of actions in the game"""
    MOVE = "move"  # Move in a direction
    INTERACT = "interact"  # Press F to interact
    ATTACK = "attack"  # Attack/break something
    CLIMB = "climb"  # Climb
    GLIDE = "glide"  # Glide
    SWIM = "swim"  # Swim
    TELEPORT = "teleport"  # Teleport to waypoint
    OPEN_MAP = "open_map"  # Open map
    DIALOG = "dialog"  # Handle dialog
    WAIT = "wait"  # Wait for something
    CUSTOM = "custom"  # Custom action


@dataclass
class GuideStep:
    """A single step in the guide"""
    step_number: int
    action_type: ActionType
    description: str
    direction: Optional[str] = None  # For move actions: north, south, east, west, etc.
    duration: Optional[float] = None  # How long to perform action
    target: Optional[str] = None  # What to interact with
    landmark: Optional[str] = None  # Nearby landmark for reference
    frame_number: Optional[int] = None  # Associated video frame
    timestamp: Optional[float] = None  # Video timestamp
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        d = asdict(self)
        d['action_type'] = self.action_type.value
        return d
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GuideStep':
        """Create from dictionary"""
        data['action_type'] = ActionType(data['action_type'])
        return cls(**data)


@dataclass
class AnalysisResult:
    """Result of video analysis"""
    video_path: str
    total_steps: int
    steps: List[GuideStep]
    summary: str
    estimated_duration: float  # Estimated time to complete in minutes
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        data = {
            'video_path': self.video_path,
            'total_steps': self.total_steps,
            'steps': [step.to_dict() for step in self.steps],
            'summary': self.summary,
            'estimated_duration': self.estimated_duration
        }
        return json.dumps(data, ensure_ascii=False, indent=2)
        
    @classmethod
    def from_json(cls, json_str: str) -> 'AnalysisResult':
        """Create from JSON string"""
        data = json.loads(json_str)
        data['steps'] = [GuideStep.from_dict(s) for s in data['steps']]
        return cls(**data)
        
    def save(self, filepath: str):
        """Save to file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.to_json())
            
    @classmethod
    def load(cls, filepath: str) -> 'AnalysisResult':
        """Load from file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return cls.from_json(f.read())


class VideoAnalyzer:
    """Analyzes guide videos using GPT-4 Vision"""
    
    SYSTEM_PROMPT = """你是一个原神游戏攻略分析专家。你的任务是分析攻略视频的截图，提取出详细的操作步骤指引。

对于每一张图片，你需要识别：
1. 当前的游戏场景/位置
2. 视频中显示的指引文字或提示
3. 需要执行的具体操作

请用结构化的JSON格式输出每个步骤，包含以下字段：
- step_number: 步骤编号
- action_type: 操作类型 (move/interact/attack/climb/glide/swim/teleport/open_map/dialog/wait/custom)
- description: 详细描述
- direction: 移动方向 (如果是移动操作)
- target: 交互目标 (如果有)
- landmark: 参考地标

输出格式示例：
```json
{
  "steps": [
    {
      "step_number": 1,
      "action_type": "teleport",
      "description": "传送到望舒客栈",
      "target": "望舒客栈传送点"
    },
    {
      "step_number": 2,
      "action_type": "move",
      "description": "向东走到悬崖边",
      "direction": "east",
      "landmark": "大树旁边"
    }
  ]
}
```

请仔细分析每张图片，确保步骤准确、详细、可执行。"""

    def __init__(self):
        self.client: Optional[OpenAI] = None
        self._last_api_key = None
        self._last_base_url = None
        
    def _ensure_client(self):
        """Ensure OpenAI client is initialized with current settings"""
        config = get_config()
        
        # Check if we need to reinitialize
        if (self.client is None or 
            self._last_api_key != config.openai_api_key or
            self._last_base_url != config.openai_base_url):
            
            if not config.openai_api_key:
                raise RuntimeError("OpenAI client not initialized. Please set API key in settings.")
                
            self.client = OpenAI(
                api_key=config.openai_api_key,
                base_url=config.openai_base_url or "https://api.openai.com/v1"
            )
            self._last_api_key = config.openai_api_key
            self._last_base_url = config.openai_base_url
            
        return config
            
    def analyze_frames(
        self, 
        frames: List[VideoFrame],
        context: str = ""
    ) -> List[GuideStep]:
        """
        Analyze a batch of frames and extract steps
        
        Args:
            frames: List of video frames to analyze
            context: Additional context about the video
        """
        config = self._ensure_client()
            
        # Prepare messages with images
        content = []
        
        # Add context
        if context:
            content.append({
                "type": "text",
                "text": f"视频上下文：{context}\n\n请分析以下视频截图并提取操作步骤："
            })
        else:
            content.append({
                "type": "text", 
                "text": "请分析以下原神攻略视频截图，提取出详细的操作步骤："
            })
            
        # Add images
        for i, frame in enumerate(frames):
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{frame.to_base64()}",
                    "detail": "high"
                }
            })
            content.append({
                "type": "text",
                "text": f"[图片 {i+1}，时间戳: {frame.timestamp:.1f}秒]"
            })
            
        # Make API call
        response = self.client.chat.completions.create(
            model=config.openai_model,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": content}
            ],
            max_tokens=4096,
            temperature=0.3
        )
        
        # Parse response
        result_text = response.choices[0].message.content
        steps = self._parse_steps(result_text, frames)
        
        return steps
        
    def _parse_steps(self, text: str, frames: List[VideoFrame]) -> List[GuideStep]:
        """Parse steps from API response"""
        steps = []
        
        # Try to extract JSON from response
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                if 'steps' in data:
                    for step_data in data['steps']:
                        step = GuideStep(
                            step_number=step_data.get('step_number', len(steps) + 1),
                            action_type=ActionType(step_data.get('action_type', 'custom')),
                            description=step_data.get('description', ''),
                            direction=step_data.get('direction'),
                            duration=step_data.get('duration'),
                            target=step_data.get('target'),
                            landmark=step_data.get('landmark')
                        )
                        steps.append(step)
            except (json.JSONDecodeError, KeyError, ValueError):
                pass
                
        # If JSON parsing failed, try to parse text
        if not steps:
            steps = self._parse_text_steps(text)
            
        # Associate frames with steps
        if frames and steps:
            frames_per_step = len(frames) / len(steps)
            for i, step in enumerate(steps):
                frame_idx = min(int(i * frames_per_step), len(frames) - 1)
                step.frame_number = frames[frame_idx].frame_number
                step.timestamp = frames[frame_idx].timestamp
                
        return steps
        
    def _parse_text_steps(self, text: str) -> List[GuideStep]:
        """Parse steps from plain text response"""
        steps = []
        lines = text.strip().split('\n')
        
        step_pattern = re.compile(r'^[\d]+[.、\)]?\s*(.+)$')
        
        for line in lines:
            line = line.strip()
            match = step_pattern.match(line)
            if match:
                description = match.group(1)
                
                # Try to detect action type
                action_type = ActionType.CUSTOM
                if any(kw in description for kw in ['传送', '传送点']):
                    action_type = ActionType.TELEPORT
                elif any(kw in description for kw in ['走', '跑', '向', '前进', '移动']):
                    action_type = ActionType.MOVE
                elif any(kw in description for kw in ['拾取', '开启', '互动', '对话']):
                    action_type = ActionType.INTERACT
                elif any(kw in description for kw in ['攻击', '打', '破坏']):
                    action_type = ActionType.ATTACK
                elif any(kw in description for kw in ['爬', '攀爬']):
                    action_type = ActionType.CLIMB
                elif any(kw in description for kw in ['飞', '滑翔']):
                    action_type = ActionType.GLIDE
                elif any(kw in description for kw in ['游', '潜水']):
                    action_type = ActionType.SWIM
                elif any(kw in description for kw in ['等待', '等']):
                    action_type = ActionType.WAIT
                    
                steps.append(GuideStep(
                    step_number=len(steps) + 1,
                    action_type=action_type,
                    description=description
                ))
                
        return steps
        
    def analyze_video(
        self,
        video_path: str,
        frame_interval: Optional[float] = None,
        progress_callback=None
    ) -> AnalysisResult:
        """
        Analyze entire video and generate guide
        
        Args:
            video_path: Path to video file
            frame_interval: Interval between frame samples (seconds)
            progress_callback: Callback function(current, total, message)
        """
        config = get_config()
        
        if frame_interval is None:
            frame_interval = config.frame_sample_interval
            
        max_frames = config.max_frames_per_analysis
        
        with VideoExtractor(video_path) as extractor:
            # Extract frames
            if progress_callback:
                progress_callback(0, 100, "提取视频帧...")
                
            all_frames = list(extractor.extract_frames_at_interval(frame_interval))
            
            if progress_callback:
                progress_callback(20, 100, f"已提取 {len(all_frames)} 帧")
                
            # Analyze in batches
            all_steps = []
            batch_count = (len(all_frames) + max_frames - 1) // max_frames
            
            for batch_idx in range(batch_count):
                start_idx = batch_idx * max_frames
                end_idx = min(start_idx + max_frames, len(all_frames))
                batch_frames = all_frames[start_idx:end_idx]
                
                if progress_callback:
                    progress = 20 + int(70 * (batch_idx + 1) / batch_count)
                    progress_callback(
                        progress, 100, 
                        f"分析中... (批次 {batch_idx + 1}/{batch_count})"
                    )
                    
                context = ""
                if all_steps:
                    # Provide context from previous steps
                    last_steps = all_steps[-3:]
                    context = "前面的步骤：" + "; ".join(s.description for s in last_steps)
                    
                batch_steps = self.analyze_frames(batch_frames, context)
                
                # Renumber steps
                for step in batch_steps:
                    step.step_number = len(all_steps) + 1
                    all_steps.append(step)
                    
            # Generate summary
            if progress_callback:
                progress_callback(90, 100, "生成摘要...")
                
            summary = self._generate_summary(all_steps)
            
            # Estimate duration
            estimated_duration = len(all_steps) * 0.5  # Rough estimate: 30 seconds per step
            
            if progress_callback:
                progress_callback(100, 100, "分析完成！")
                
            return AnalysisResult(
                video_path=video_path,
                total_steps=len(all_steps),
                steps=all_steps,
                summary=summary,
                estimated_duration=estimated_duration
            )
            
    def _generate_summary(self, steps: List[GuideStep]) -> str:
        """Generate a summary of all steps"""
        if not steps:
            return "无步骤"
            
        # Count action types
        action_counts = {}
        for step in steps:
            action_type = step.action_type.value
            action_counts[action_type] = action_counts.get(action_type, 0) + 1
            
        # Generate summary
        parts = [f"共 {len(steps)} 个步骤"]
        
        action_names = {
            'move': '移动',
            'interact': '交互',
            'attack': '攻击',
            'climb': '攀爬',
            'glide': '滑翔',
            'swim': '游泳',
            'teleport': '传送',
            'dialog': '对话',
            'wait': '等待',
            'custom': '其他'
        }
        
        for action, count in sorted(action_counts.items(), key=lambda x: -x[1]):
            if count > 0:
                name = action_names.get(action, action)
                parts.append(f"{name}×{count}")
                
        return "，".join(parts)
        
    def analyze_single_frame(self, frame: VideoFrame) -> str:
        """
        Analyze a single frame for real-time decision making
        Returns description of what's in the frame
        """
        config = self._ensure_client()
        
        response = self.client.chat.completions.create(
            model=config.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": "你是原神游戏画面分析专家。请简洁描述当前画面中的场景、角色位置、以及任何可交互的物体（宝箱、神瞳、NPC等）。"
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{frame.to_base64()}",
                                "detail": "high"
                            }
                        },
                        {
                            "type": "text",
                            "text": "请描述这个原神游戏画面。"
                        }
                    ]
                }
            ],
            max_tokens=500,
            temperature=0.3
        )
        
        return response.choices[0].message.content
