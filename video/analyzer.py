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
    # Movement
    MOVE = "move"  # Move in a direction
    SPRINT = "sprint"  # Sprint/run
    JUMP = "jump"  # Jump
    CLIMB = "climb"  # Climb
    GLIDE = "glide"  # Glide
    SWIM = "swim"  # Swim
    PLUNGE = "plunge"  # Plunge attack while gliding
    
    # Interaction
    INTERACT = "interact"  # Press F to interact
    ATTACK = "attack"  # Attack/break something
    CHARGED_ATTACK = "charged_attack"  # Hold attack
    ELEMENTAL_SKILL = "elemental_skill"  # E skill
    ELEMENTAL_BURST = "elemental_burst"  # Q burst
    
    # Navigation
    TELEPORT = "teleport"  # Teleport to waypoint
    OPEN_MAP = "open_map"  # Open map
    USE_GADGET = "use_gadget"  # Press T to use gadget
    
    # Other
    DIALOG = "dialog"  # Handle dialog
    WAIT = "wait"  # Wait for something
    KEY_PRESS = "key_press"  # Press specific key
    MOUSE_CLICK = "mouse_click"  # Click at position
    CUSTOM = "custom"  # Custom action


@dataclass
class GuideStep:
    """A single step in the guide"""
    step_number: int
    action_type: ActionType
    description: str
    
    # Movement details
    direction: Optional[str] = None  # forward, backward, left, right, north, south, etc.
    duration: Optional[float] = None  # How long to perform action (seconds)
    distance: Optional[str] = None  # Description of distance (e.g., "10米", "到树旁边")
    
    # Interaction details
    target: Optional[str] = None  # What to interact with
    landmark: Optional[str] = None  # Nearby landmark for reference
    
    # Key press details
    key_to_press: Optional[str] = None  # Specific key: 'f', 't', 'e', 'q', 'space', etc.
    hold_key: bool = False  # Whether to hold the key
    
    # Teleport details
    teleport_location: Optional[str] = None  # Exact waypoint name
    region: Optional[str] = None  # Region name (e.g., "璃月", "蒙德")
    
    # Timing
    wait_before: Optional[float] = None  # Wait before action (seconds)
    wait_after: Optional[float] = None  # Wait after action (seconds)
    
    # Video reference
    frame_number: Optional[int] = None  # Associated video frame
    timestamp: Optional[float] = None  # Video timestamp
    subtitle_text: Optional[str] = None  # Subtitle/caption at this moment
    
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
    
    SYSTEM_PROMPT = """你是一个原神游戏攻略视频分析专家。你的任务是从攻略视频截图中提取出精确、可执行的操作步骤。

## 分析要求

对于每一张图片，仔细识别：

### 1. 画面内容
- 当前游戏界面状态（大世界/地图/菜单/对话）
- 场景位置和环境特征
- 可见的交互物体（宝箱、神瞳、NPC、采集物等）
- UI提示（左下角按键提示、任务目标等）

### 2. 视频中的文字信息 ⚠️ 非常重要
- **字幕/解说文字**：通常在画面底部，包含操作指引
- **视频制作者的标注**：箭头、圆圈、文字说明
- **弹幕信息**（如果有）
- **按键提示**：如"按F拾取"、"按T使用道具"、"长按E"等

### 3. 需要执行的具体操作
识别以下操作类型及其详细参数：

| 操作类型 | action_type | 需要的参数 |
|---------|-------------|-----------|
| 传送 | teleport | teleport_location(传送点名), region(区域) |
| 移动 | move | direction(方向), duration(时长), landmark(参照物) |
| 冲刺 | sprint | duration(时长) |
| 跳跃 | jump | - |
| 交互 | interact | target(目标), key_to_press(按键，默认F) |
| 攻击 | attack | target(目标) |
| 重击 | charged_attack | duration(蓄力时长) |
| 元素战技 | elemental_skill | hold_key(是否长按) |
| 元素爆发 | elemental_burst | - |
| 使用道具 | use_gadget | target(道具名) |
| 攀爬 | climb | duration(时长) |
| 滑翔 | glide | direction(方向), duration(时长) |
| 下落攻击 | plunge | - |
| 游泳 | swim | direction(方向), duration(时长) |
| 对话 | dialog | - |
| 等待 | wait | duration(时长), target(等什么) |
| 按键 | key_press | key_to_press(具体按键) |

## 输出格式

```json
{
  "frame_info": {
    "scene": "大世界/地图/菜单",
    "location_description": "场景描述",
    "subtitle_text": "字幕内容（如有）"
  },
  "steps": [
    {
      "step_number": 1,
      "action_type": "teleport",
      "description": "传送到璃月港西边的传送锚点",
      "teleport_location": "璃月港-西",
      "region": "璃月",
      "key_to_press": null
    },
    {
      "step_number": 2,
      "action_type": "move",
      "description": "向前走到崖边的大树旁",
      "direction": "forward",
      "duration": 3.0,
      "distance": "约10米",
      "landmark": "崖边大树"
    },
    {
      "step_number": 3,
      "action_type": "interact",
      "description": "按F拾取华丽宝箱",
      "target": "华丽宝箱",
      "key_to_press": "f"
    },
    {
      "step_number": 4,
      "action_type": "use_gadget",
      "description": "按T使用风之翼",
      "target": "风之翼",
      "key_to_press": "t"
    },
    {
      "step_number": 5,
      "action_type": "elemental_skill",
      "description": "长按E使用岩元素战技",
      "hold_key": true,
      "duration": 1.5
    }
  ]
}
```

## 关键提示

1. **字幕最重要**：字幕通常直接告诉你该做什么，如"这里跳下去"、"按T使用道具"
2. **方向要准确**：根据小地图或画面判断，使用 forward/left/right/backward
3. **按键要明确**：F=交互、T=道具、E=元素战技、Q=元素爆发、Space=跳跃
4. **时长估算**：根据画面变化估算操作持续时间
5. **传送点名称**：尽量给出完整的传送点名称，如"望舒客栈"而非"那个传送点"

请仔细分析每张图片，确保步骤准确、详细、可直接执行。"""

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
        context: str = "",
        log_callback = None
    ) -> List[GuideStep]:
        """
        Analyze a batch of frames and extract steps
        
        Args:
            frames: List of video frames to analyze
            context: Additional context about the video
            log_callback: Optional callback(message) for logging
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
            
        # Make API call with retry
        max_retries = 3
        last_error = None
        
        for attempt in range(max_retries):
            try:
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
                
            except Exception as e:
                last_error = e
                error_msg = f"API调用失败 (尝试 {attempt+1}/{max_retries}): {str(e)}"
                print(error_msg)
                if log_callback:
                    log_callback(error_msg)
                
                if attempt < max_retries - 1:
                    import time
                    time.sleep(2)  # Wait before retry
                    
        # If all retries failed
        if log_callback:
            log_callback(f"❌ API分析最终失败: {str(last_error)}")
            
        return []
        
    def _parse_steps(self, text: str, frames: List[VideoFrame]) -> List[GuideStep]:
        """Parse steps from API response"""
        steps = []
        frame_info = {}
        
        # Try to extract JSON from response
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                
                # Extract frame info if present
                frame_info = data.get('frame_info', {})
                
                if 'steps' in data:
                    for step_data in data['steps']:
                        # Get action type safely
                        action_str = step_data.get('action_type', 'custom')
                        try:
                            action_type = ActionType(action_str)
                        except ValueError:
                            action_type = ActionType.CUSTOM
                            
                        step = GuideStep(
                            step_number=step_data.get('step_number', len(steps) + 1),
                            action_type=action_type,
                            description=step_data.get('description', ''),
                            # Movement
                            direction=step_data.get('direction'),
                            duration=step_data.get('duration'),
                            distance=step_data.get('distance'),
                            # Interaction
                            target=step_data.get('target'),
                            landmark=step_data.get('landmark'),
                            # Key press
                            key_to_press=step_data.get('key_to_press'),
                            hold_key=step_data.get('hold_key', False),
                            # Teleport
                            teleport_location=step_data.get('teleport_location'),
                            region=step_data.get('region'),
                            # Timing
                            wait_before=step_data.get('wait_before'),
                            wait_after=step_data.get('wait_after'),
                            # Subtitle from frame_info
                            subtitle_text=frame_info.get('subtitle_text')
                        )
                        steps.append(step)
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"JSON parsing error: {e}")
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
                    
                # Create a simple logger if callback exists
                log_cb = None
                if progress_callback:
                    log_cb = lambda msg: progress_callback(progress, 100, msg)
                    
                batch_steps = self.analyze_frames(batch_frames, context, log_cb)
                
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
