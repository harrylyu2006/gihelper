"""
AI Decision Engine for coordinating automation based on guide steps
"""
import time
from typing import Optional, List, Callable
from dataclasses import dataclass
from enum import Enum
import threading

from video.analyzer import GuideStep, AnalysisResult, ActionType, VideoAnalyzer
from video.extractor import VideoFrame
from screen.capture import ScreenCapture
from screen.detector import GameDetector, GameState
from automation.controller import GameController
from automation.navigator import Navigator
from config import get_config


class ExecutionState(Enum):
    """State of the execution engine"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass  
class ExecutionProgress:
    """Progress information"""
    current_step: int
    total_steps: int
    current_step_description: str
    state: ExecutionState
    error_message: str = ""
    
    @property
    def percentage(self) -> float:
        if self.total_steps == 0:
            return 0
        return (self.current_step / self.total_steps) * 100


class DecisionEngine:
    """
    Core AI decision engine that executes guide steps
    
    Coordinates between:
    - Video analyzer (understanding what to do)
    - Screen detector (understanding current state)
    - Navigator (executing actions)
    - AI vision (real-time decision making)
    """
    
    def __init__(self):
        self.config = get_config()
        
        # Components
        self.analyzer = VideoAnalyzer()
        self.screen = ScreenCapture()
        self.detector = GameDetector(
            resolution=(
                self.config.game_resolution_width,
                self.config.game_resolution_height
            )
        )
        self.controller = GameController(
            action_delay_ms=self.config.action_delay_ms
        )
        self.navigator = Navigator(
            controller=self.controller,
            screen_capture=self.screen,
            detector=self.detector,
            log_callback=self.log
        )
        
        # State
        self.state = ExecutionState.IDLE
        self.current_step = 0
        self.guide_steps: List[GuideStep] = []
        
        # Callbacks
        self.on_progress: Optional[Callable[[ExecutionProgress], None]] = None
        self.on_log: Optional[Callable[[str], None]] = None
        
        # Threading
        self._execution_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # Not paused by default
        
    def log(self, message: str):
        """Log a message"""
        if self.on_log:
            self.on_log(message)
            
    def update_progress(self):
        """Update progress callback"""
        if self.on_progress:
            progress = ExecutionProgress(
                current_step=self.current_step,
                total_steps=len(self.guide_steps),
                current_step_description=self._get_current_step_description(),
                state=self.state
            )
            self.on_progress(progress)
            
    def _get_current_step_description(self) -> str:
        """Get description of current step"""
        if 0 <= self.current_step < len(self.guide_steps):
            return self.guide_steps[self.current_step].description
        return ""
        
    # ================== Guide Analysis ==================
    
    def analyze_video(
        self, 
        video_path: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> AnalysisResult:
        """
        Analyze a guide video and extract steps
        """
        self.log(f"开始分析视频: {video_path}")
        
        result = self.analyzer.analyze_video(
            video_path,
            progress_callback=progress_callback
        )
        
        self.guide_steps = result.steps
        self.current_step = 0
        
        self.log(f"分析完成，共提取 {len(self.guide_steps)} 个步骤")
        
        return result
        
    def load_guide(self, guide_path: str):
        """Load a previously saved guide"""
        result = AnalysisResult.load(guide_path)
        self.guide_steps = result.steps
        self.current_step = 0
        self.log(f"已加载攻略，共 {len(self.guide_steps)} 个步骤")
        
    # ================== Execution Control ==================
    
    def start(self):
        """Start executing the guide"""
        if not self.guide_steps:
            self.log("❌ 没有可执行的步骤")
            return
            
        if self.state == ExecutionState.RUNNING:
            self.log("⚠️ 已经在执行中")
            return
            
        self.state = ExecutionState.RUNNING
        self._stop_event.clear()
        self._pause_event.set()
        
        self._execution_thread = threading.Thread(target=self._execution_loop)
        self._execution_thread.daemon = True
        self._execution_thread.start()
        
        self.log("▶️ 开始执行攻略...")
        
    def pause(self):
        """Pause execution"""
        if self.state == ExecutionState.RUNNING:
            self._pause_event.clear()
            self.state = ExecutionState.PAUSED
            self.controller.pause()
            self.log("⏸️ 已暂停")
            
    def resume(self):
        """Resume execution"""
        if self.state == ExecutionState.PAUSED:
            self._pause_event.set()
            self.state = ExecutionState.RUNNING
            self.controller.resume()
            self.log("▶️ 继续执行...")
            
    def stop(self):
        """Stop execution"""
        self._stop_event.set()
        self._pause_event.set()  # Unblock if paused
        self.controller.emergency_stop()
        self.state = ExecutionState.STOPPED
        self.log("⏹️ 已停止")
        
        if self._execution_thread:
            self._execution_thread.join(timeout=2)
            
    def reset(self):
        """Reset to beginning"""
        self.stop()
        self.current_step = 0
        self.state = ExecutionState.IDLE
        self.controller.reset()
        self.log("🔄 已重置")
        
    # ================== Execution Loop ==================
    
    def _execution_loop(self):
        """Main execution loop (runs in thread)"""
        try:
            # Wait for game to be ready
            if not self._wait_for_game():
                self.state = ExecutionState.ERROR
                self.log("❌ 无法检测到游戏窗口")
                return
                
            # Special handling for initial teleport (Step 1)
            if self.current_step == 0 and self.guide_steps:
                first_step = self.guide_steps[0]
                if first_step.action_type == ActionType.TELEPORT:
                    self.log(f"🚀 准备执行初始传送: {first_step.description}")
                    
                    # Ensure we are in a state to teleport
                    screen = self.screen.capture_full_screen(monitor=1)
                    state = self.detector.detect_game_state(screen)
                    
                    if state == GameState.WORLD:
                        self.log("🗺️ 打开地图准备传送...")
                        self.navigator.open_map_and_wait()
                    
            while self.current_step < len(self.guide_steps):
                # Check stop event
                if self._stop_event.is_set():
                    break
                    
                # Check pause event (blocks if paused)
                self._pause_event.wait()
                
                if self._stop_event.is_set():
                    break
                    
                # Execute current step
                step = self.guide_steps[self.current_step]
                self.log(f"📍 步骤 {self.current_step + 1}: {step.description}")
                self.update_progress()
                
                success = self._execute_step(step)
                
                if success:
                    self.current_step += 1
                else:
                    # Try AI recovery
                    if not self._ai_recovery(step):
                        self.log(f"❌ 步骤执行失败: {step.description}")
                        # Continue anyway
                        self.current_step += 1
                        
                # Small delay between steps
                time.sleep(0.5)
                
            if self.current_step >= len(self.guide_steps):
                self.state = ExecutionState.COMPLETED
                self.log("✅ 攻略执行完成！")
                
        except Exception as e:
            self.state = ExecutionState.ERROR
            self.log(f"❌ 执行出错: {str(e)}")
            
    def _wait_for_game(self, timeout: float = 10) -> bool:
        """Wait for game to be ready"""
        self.log("🔍 检测游戏窗口...")
        
        # Try to find and focus game window first
        game_window = self.screen.find_game_window()
        if game_window:
            self.log(f"📺 找到游戏窗口: {game_window.title}")
            self.screen.bring_window_to_front(game_window)
            import time as t
            t.sleep(0.5)  # Wait for window to come to front
        else:
            self.log("⚠️ 未找到原神窗口，尝试全屏截图...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self._stop_event.is_set():
                return False
                
            try:
                # Capture screen
                if game_window:
                    screen = self.screen.capture_window(game_window)
                else:
                    screen = self.screen.capture_full_screen(monitor=1)
                    
                if screen is None:
                    self.log("⚠️ 截图失败")
                    time.sleep(0.5)
                    continue
                    
                state = self.detector.detect_game_state(screen)
                
                # Accept WORLD or MAP states (map is fine, we can start from there)
                if state == GameState.WORLD:
                    self.log("✅ 检测到游戏大世界画面")
                    return True
                elif state == GameState.MAP:
                    self.log("✅ 检测到地图界面，可以开始")
                    return True
                elif state == GameState.LOADING:
                    self.log("⏳ 游戏加载中...")
                else:
                    self.log(f"🔍 当前状态: {state.value}，继续等待...")
                    
            except Exception as e:
                self.log(f"⚠️ 检测出错: {str(e)[:50]}")
                
            time.sleep(0.5)
            
        self.log("❌ 超时：无法检测到游戏窗口")
        return False
        
    def _execute_step(self, step: GuideStep) -> bool:
        """Execute a single step"""
        # Handle wait_before if specified
        if step.wait_before:
            time.sleep(step.wait_before)
            
        action_handlers = {
            # Movement
            ActionType.MOVE: self._handle_move,
            ActionType.SPRINT: self._handle_sprint,
            ActionType.JUMP: self._handle_jump,
            ActionType.CLIMB: self._handle_climb,
            ActionType.GLIDE: self._handle_glide,
            ActionType.SWIM: self._handle_swim,
            ActionType.PLUNGE: self._handle_plunge,
            # Interaction
            ActionType.INTERACT: self._handle_interact,
            ActionType.ATTACK: self._handle_attack,
            ActionType.CHARGED_ATTACK: self._handle_charged_attack,
            ActionType.ELEMENTAL_SKILL: self._handle_elemental_skill,
            ActionType.ELEMENTAL_BURST: self._handle_elemental_burst,
            # Navigation
            ActionType.TELEPORT: self._handle_teleport,
            ActionType.OPEN_MAP: self._handle_open_map,
            ActionType.USE_GADGET: self._handle_use_gadget,
            # Other
            ActionType.DIALOG: self._handle_dialog,
            ActionType.WAIT: self._handle_wait,
            ActionType.KEY_PRESS: self._handle_key_press,
            ActionType.MOUSE_CLICK: self._handle_mouse_click,
            ActionType.CUSTOM: self._handle_custom,
        }
        
        handler = action_handlers.get(step.action_type, self._handle_custom)
        result = handler(step)
        
        # Handle wait_after if specified
        if step.wait_after:
            time.sleep(step.wait_after)
            
        return result
        
    # ================== Action Handlers ==================
    
    def _handle_move(self, step: GuideStep) -> bool:
        """Handle movement action"""
        direction = step.direction or "forward"
        duration = step.duration or 2.0
        
        result = self.controller.move_direction(direction, duration)
        return result.success
        
    def _handle_interact(self, step: GuideStep) -> bool:
        """Handle interaction action"""
        # Press interact key
        result = self.controller.interact()
        time.sleep(0.5)
        return result.success
        
    def _handle_attack(self, step: GuideStep) -> bool:
        """Handle attack action"""
        result = self.controller.attack()
        return result.success
        
    def _handle_climb(self, step: GuideStep) -> bool:
        """Handle climb action"""
        duration = step.duration or 3.0
        
        # Jump to start climbing, then move forward
        self.controller.jump()
        time.sleep(0.3)
        result = self.controller.move_forward(duration)
        return result.success
        
    def _handle_glide(self, step: GuideStep) -> bool:
        """Handle glide action"""
        duration = step.duration or 5.0
        
        # Jump and hold to glide
        self.controller.jump()
        time.sleep(0.5)
        self.controller.jump()  # Double jump to open glider
        time.sleep(0.2)
        result = self.controller.move_forward(duration)
        return result.success
        
    def _handle_swim(self, step: GuideStep) -> bool:
        """Handle swim action"""
        duration = step.duration or 3.0
        
        # Sprint to swim faster
        self.controller.sprint_start()
        result = self.controller.move_forward(duration)
        self.controller.sprint_stop()
        return result.success
        
    def _handle_teleport(self, step: GuideStep) -> bool:
        """Handle teleport action using AI vision"""
        target = step.target or step.description
        self.log(f"🗺️ 正在传送到: {target}")
        
        # Use AI-powered teleport
        result = self.navigator.teleport_to_location(target)
        
        if result.success:
            self.log(f"✅ 传送成功")
            # Wait a moment after teleport
            time.sleep(2)
            return True
        else:
            self.log(f"⚠️ 自动传送失败，尝试备用方法...")
            
            # Fallback: open map and try template matching
            if not self.navigator.open_map_and_wait():
                return False
                
            # Try clicking nearest waypoint as fallback
            result = self.navigator.click_nearest_waypoint()
            
            if not result.success:
                self.log(f"❌ 无法找到传送点，请手动传送到: {target}")
                time.sleep(5)  # Give user time to teleport manually
                
            self.navigator.close_map()
            return True
        
    def _handle_open_map(self, step: GuideStep) -> bool:
        """Handle open map action"""
        return self.navigator.open_map_and_wait()
        
    def _handle_dialog(self, step: GuideStep) -> bool:
        """Handle dialog action"""
        result = self.navigator.skip_dialog()
        return result.success
        
    def _handle_wait(self, step: GuideStep) -> bool:
        """Handle wait action"""
        duration = step.duration or 2.0
        self.log(f"⏳ 等待 {duration} 秒...")
        time.sleep(duration)
        return True
        
    def _handle_jump(self, step: GuideStep) -> bool:
        """Handle jump action"""
        result = self.controller.jump()
        return result.success
        
    def _handle_sprint(self, step: GuideStep) -> bool:
        """Handle sprint action"""
        duration = step.duration or 2.0
        direction = step.direction or "forward"
        
        self.controller.sprint_start()
        result = self.controller.move_direction(direction, duration)
        self.controller.sprint_stop()
        return result.success
        
    def _handle_plunge(self, step: GuideStep) -> bool:
        """Handle plunge attack (while gliding/falling)"""
        result = self.controller.attack()
        return result.success
        
    def _handle_charged_attack(self, step: GuideStep) -> bool:
        """Handle charged attack (hold click)"""
        duration = step.duration or 1.0
        result = self.controller.charged_attack(duration)
        return result.success
        
    def _handle_elemental_skill(self, step: GuideStep) -> bool:
        """Handle elemental skill (E key)"""
        hold = step.hold_key or False
        duration = step.duration or 1.0
        
        self.log(f"⚡ {'长按' if hold else '按下'} E 元素战技")
        result = self.controller.elemental_skill(hold=hold, hold_time=duration)
        return result.success
        
    def _handle_elemental_burst(self, step: GuideStep) -> bool:
        """Handle elemental burst (Q key)"""
        self.log("💥 按下 Q 元素爆发")
        result = self.controller.elemental_burst()
        return result.success
        
    def _handle_use_gadget(self, step: GuideStep) -> bool:
        """Handle use gadget (T key)"""
        self.log(f"🔧 按下 T 使用道具: {step.target or '小道具'}")
        result = self.controller.press_key('t')
        time.sleep(0.5)
        return result.success
        
    def _handle_key_press(self, step: GuideStep) -> bool:
        """Handle generic key press"""
        key = step.key_to_press or 'f'
        
        if step.hold_key and step.duration:
            self.log(f"⌨️ 长按 {key.upper()} {step.duration}秒")
            self.controller.hold_key(key)
            time.sleep(step.duration)
            self.controller.release_key(key)
            return True
        else:
            self.log(f"⌨️ 按下 {key.upper()}")
            result = self.controller.press_key(key)
            return result.success
            
    def _handle_mouse_click(self, step: GuideStep) -> bool:
        """Handle mouse click at position"""
        # This would need screen coordinates - use AI to find target
        if step.target:
            self.log(f"🖱️ 点击: {step.target}")
            screen = self.screen.capture_full_screen(monitor=1)
            click_pos = self.navigator.ai_vision.find_click_target(screen, step.target)
            if click_pos:
                self.controller.click_at(click_pos[0], click_pos[1])
                return True
        return False
        
    def _handle_custom(self, step: GuideStep) -> bool:
        """Handle custom/unknown action"""
        # If there's a specific key to press, use it
        if step.key_to_press:
            return self._handle_key_press(step)
        # Otherwise use AI to figure out what to do
        return self._ai_decide_action(step)
        
    # ================== AI Decision Making ==================
    
    def _ai_decide_action(self, step: GuideStep) -> bool:
        """Use AI to decide what action to take"""
        try:
            # Capture current screen
            screen = self.screen.capture_full_screen(monitor=1)
            
            # Create a video frame for analysis
            from video.extractor import VideoFrame
            frame = VideoFrame(
                frame_number=0,
                timestamp=0,
                image=screen
            )
            
            # Ask AI what to do
            analysis = self.analyzer.analyze_single_frame(frame)
            self.log(f"🤖 AI 分析: {analysis[:100]}...")
            
            # For now, just try basic interaction
            self.controller.interact()
            time.sleep(0.5)
            
            return True
            
        except Exception as e:
            self.log(f"⚠️ AI 决策失败: {str(e)}")
            return False
            
    def _ai_recovery(self, step: GuideStep) -> bool:
        """Try to recover from a failed step using AI"""
        self.log("🔄 尝试 AI 恢复...")
        
        try:
            # Analyze current state
            screen = self.screen.capture_full_screen(monitor=1)
            state = self.detector.detect_game_state(screen)
            
            if state == GameState.DIALOG:
                # Skip dialog and retry
                self.navigator.skip_dialog()
                time.sleep(0.5)
                return True
                
            elif state == GameState.MAP:
                # Close map and retry
                self.navigator.close_map()
                time.sleep(0.5)
                return True
                
            elif state == GameState.LOADING:
                # Wait for loading
                time.sleep(3)
                return True
                
            # Try to continue with AI
            return self._ai_decide_action(step)
            
        except Exception as e:
            self.log(f"⚠️ AI 恢复失败: {str(e)}")
            return False
