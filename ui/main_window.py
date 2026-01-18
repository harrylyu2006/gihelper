"""
Main window for Genshin Auto-Guide Helper
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QStatusBar, QMenuBar, QMenu, QToolBar,
    QTextEdit, QLabel, QProgressBar, QMessageBox,
    QFileDialog
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QAction, QIcon, QKeySequence

from .video_panel import VideoPanel
from .control_panel import ControlPanel
from .settings_dialog import SettingsDialog
from config import get_config, save_config
from engine.decision import DecisionEngine, ExecutionProgress, ExecutionState


class AnalysisWorkerThread(QThread):
    """Worker thread for video analysis"""
    progress = pyqtSignal(int, str)  # current percentage, message
    finished_signal = pyqtSignal(object)  # analysis result
    error = pyqtSignal(str)  # error message
    
    def __init__(self, engine, video_path):
        super().__init__()
        self.engine = engine
        self.video_path = video_path
        
    def run(self):
        try:
            def progress_callback(current, total, message):
                self.progress.emit(current, message)
                
            result = self.engine.analyze_video(
                self.video_path,
                progress_callback=progress_callback
            )
            self.finished_signal.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    """Main application window"""
    
    # Signals
    status_changed = pyqtSignal(str)
    log_message = pyqtSignal(str)
    
    # Thread-safe signals for engine callbacks
    engine_progress_signal = pyqtSignal(object)  # ExecutionProgress
    engine_log_signal = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.config = get_config()
        self.is_running = False
        self.is_paused = False
        
        # Initialize decision engine
        self.engine = DecisionEngine()
        # Use lambda to emit signals (thread-safe)
        self.engine.on_progress = lambda p: self.engine_progress_signal.emit(p)
        self.engine.on_log = lambda m: self.engine_log_signal.emit(m)
        self.guide_loaded = False
        
        # Connect signals to slots
        self.engine_progress_signal.connect(self._on_engine_progress)
        self.engine_log_signal.connect(self._on_engine_log)
        
        self.init_ui()
        self.setup_signals()
        self.apply_styles()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("原神自动攻略助手 - Genshin Auto-Guide Helper")
        self.setMinimumSize(1200, 800)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Create splitter for main content
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Video and status
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Video panel
        self.video_panel = VideoPanel()
        left_layout.addWidget(self.video_panel, stretch=2)
        
        # Current step display
        step_container = QWidget()
        step_container.setObjectName("stepContainer")
        step_layout = QVBoxLayout(step_container)
        step_layout.setContentsMargins(15, 15, 15, 15)
        
        step_header = QLabel("📍 当前步骤 / Current Step")
        step_header.setObjectName("stepHeader")
        step_layout.addWidget(step_header)
        
        self.current_step_label = QLabel("等待开始...")
        self.current_step_label.setObjectName("currentStep")
        self.current_step_label.setWordWrap(True)
        step_layout.addWidget(self.current_step_label)
        
        left_layout.addWidget(step_container)
        
        splitter.addWidget(left_panel)
        
        # Right panel - Control and logs
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Control panel
        self.control_panel = ControlPanel()
        right_layout.addWidget(self.control_panel)
        
        # Progress section
        progress_container = QWidget()
        progress_container.setObjectName("progressContainer")
        progress_layout = QVBoxLayout(progress_container)
        progress_layout.setContentsMargins(15, 15, 15, 15)
        
        progress_header = QLabel("📊 执行进度 / Progress")
        progress_header.setObjectName("progressHeader")
        progress_layout.addWidget(progress_header)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("0 / 0 步骤完成")
        progress_layout.addWidget(self.progress_label)
        
        right_layout.addWidget(progress_container)
        
        # Log output
        log_container = QWidget()
        log_container.setObjectName("logContainer")
        log_layout = QVBoxLayout(log_container)
        log_layout.setContentsMargins(15, 15, 15, 15)
        
        log_header = QLabel("📝 运行日志 / Log")
        log_header.setObjectName("logHeader")
        log_layout.addWidget(log_header)
        
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setObjectName("logOutput")
        log_layout.addWidget(self.log_output)
        
        right_layout.addWidget(log_container, stretch=1)
        
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setSizes([700, 500])
        
        main_layout.addWidget(splitter)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create toolbar
        self.create_toolbar()
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪 - Ready")
        
    def create_menu_bar(self):
        """Create the menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("文件(&F)")
        
        open_action = QAction("打开视频(&O)...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.video_panel.open_video)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Settings menu
        settings_menu = menubar.addMenu("设置(&S)")
        
        preferences_action = QAction("首选项(&P)...", self)
        preferences_action.setShortcut("Ctrl+,")
        preferences_action.triggered.connect(self.show_settings)
        settings_menu.addAction(preferences_action)
        
        # Help menu
        help_menu = menubar.addMenu("帮助(&H)")
        
        about_action = QAction("关于(&A)...", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def create_toolbar(self):
        """Create the toolbar"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # Open video button
        open_btn = QAction("📂 打开视频", self)
        open_btn.triggered.connect(self.video_panel.open_video)
        toolbar.addAction(open_btn)
        
        toolbar.addSeparator()
        
        # Analyze button
        analyze_btn = QAction("🔍 分析视频", self)
        analyze_btn.triggered.connect(self.analyze_video)
        toolbar.addAction(analyze_btn)
        
        toolbar.addSeparator()
        
        # Settings button
        settings_btn = QAction("⚙️ 设置", self)
        settings_btn.triggered.connect(self.show_settings)
        toolbar.addAction(settings_btn)
        
    def setup_signals(self):
        """Setup signal connections"""
        # Control panel signals
        self.control_panel.start_clicked.connect(self.start_execution)
        self.control_panel.pause_clicked.connect(self.pause_execution)
        self.control_panel.stop_clicked.connect(self.stop_execution)
        
        # Video panel signals
        self.video_panel.video_loaded.connect(self.on_video_loaded)
        
        # Internal signals
        self.log_message.connect(self.append_log)
        self.status_changed.connect(self.status_bar.showMessage)
        
    def apply_styles(self):
        """Apply application styles"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a2e;
            }
            
            QWidget {
                color: #eee;
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
                font-size: 14px;
            }
            
            QMenuBar {
                background-color: #16213e;
                color: #eee;
                padding: 5px;
            }
            
            QMenuBar::item:selected {
                background-color: #0f3460;
            }
            
            QMenu {
                background-color: #16213e;
                color: #eee;
                border: 1px solid #0f3460;
            }
            
            QMenu::item:selected {
                background-color: #e94560;
            }
            
            QToolBar {
                background-color: #16213e;
                border: none;
                spacing: 10px;
                padding: 5px;
            }
            
            QToolBar QToolButton {
                background-color: transparent;
                color: #eee;
                padding: 8px 15px;
                border-radius: 5px;
            }
            
            QToolBar QToolButton:hover {
                background-color: #0f3460;
            }
            
            QStatusBar {
                background-color: #16213e;
                color: #888;
            }
            
            #stepContainer, #progressContainer, #logContainer {
                background-color: #16213e;
                border-radius: 10px;
                margin: 5px;
            }
            
            #stepHeader, #progressHeader, #logHeader {
                color: #e94560;
                font-size: 16px;
                font-weight: bold;
                margin-bottom: 10px;
            }
            
            #currentStep {
                color: #fff;
                font-size: 18px;
                padding: 10px;
                background-color: rgba(15, 52, 96, 0.5);
                border-radius: 5px;
            }
            
            QProgressBar {
                border: none;
                border-radius: 5px;
                background-color: #0f3460;
                height: 20px;
                text-align: center;
            }
            
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #e94560, stop:1 #ff6b6b);
                border-radius: 5px;
            }
            
            #logOutput {
                background-color: #0d1b2a;
                border: 1px solid #0f3460;
                border-radius: 5px;
                color: #aaa;
                font-family: "Consolas", "Courier New", monospace;
                font-size: 12px;
                padding: 10px;
            }
            
            QSplitter::handle {
                background-color: #0f3460;
                width: 3px;
            }
        """)
        
    def show_settings(self):
        """Show settings dialog"""
        dialog = SettingsDialog(self.config, self)
        if dialog.exec():
            save_config()
            self.append_log("✅ 设置已保存")
            
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "关于 - About",
            """<h2>原神自动攻略助手</h2>
            <p>Genshin Auto-Guide Helper</p>
            <p>版本: 1.0.0</p>
            <hr>
            <p>通过 AI 分析攻略视频，自动执行游戏操作。</p>
            """
        )
        
    def on_video_loaded(self, filepath: str):
        """Handle video loaded event"""
        self.append_log(f"📹 视频已加载: {filepath}")
        self.config.last_video_path = filepath
        save_config()
        self.control_panel.set_analyze_enabled(True)
        
    def analyze_video(self):
        """Start video analysis"""
        if not self.video_panel.current_video:
            QMessageBox.warning(self, "警告", "请先加载视频文件")
            return
            
        if not self.config.openai_api_key:
            QMessageBox.warning(self, "警告", "请先在设置中配置 OpenAI API Key")
            self.show_settings()
            return
            
        self.append_log("🔍 开始分析视频...")
        self.status_changed.emit("正在分析视频...")
        self.control_panel.update_status("analyzing")
        
        # Disable buttons during analysis
        self.control_panel.set_analyze_enabled(False)
        
        # Create worker thread
        self._analysis_thread = AnalysisWorkerThread(
            self.engine,
            self.video_panel.current_video
        )
        self._analysis_thread.progress.connect(self._on_analysis_progress)
        self._analysis_thread.finished_signal.connect(self._on_analysis_finished)
        self._analysis_thread.error.connect(self._on_analysis_error)
        self._analysis_thread.start()
        
    def _on_analysis_progress(self, current: int, message: str):
        """Handle analysis progress update"""
        self.append_log(f"📊 {message} ({current}%)")
        self.progress_bar.setValue(current)
        
    def _on_analysis_finished(self, result):
        """Handle analysis completion"""
        from video.analyzer import AnalysisResult
        
        self.append_log(f"✅ 分析完成: {result.summary}")
        self.append_log(f"📋 共提取 {result.total_steps} 个步骤")
        
        # Enable execution
        self.guide_loaded = True
        self.control_panel.set_ready_to_start(True)
        self.control_panel.set_analyze_enabled(True)
        self.control_panel.update_status("ready")
        self.status_changed.emit("分析完成 - 准备执行")
        
        # Save the guide
        save_path = self.video_panel.current_video + ".guide.json"
        result.save(save_path)
        self.append_log(f"💾 攻略已保存到: {save_path}")
        
    def _on_analysis_error(self, error_msg: str):
        """Handle analysis error"""
        self.append_log(f"❌ 分析失败: {error_msg}")
        self.control_panel.update_status("error")
        self.control_panel.set_analyze_enabled(True)
        QMessageBox.critical(self, "错误", f"视频分析失败:\n{error_msg}")
        
    def start_execution(self):
        """Start automation execution"""
        if not self.config.openai_api_key:
            QMessageBox.warning(self, "警告", "请先在设置中配置 OpenAI API Key")
            self.show_settings()
            return
            
        if not self.guide_loaded:
            QMessageBox.warning(self, "警告", "请先分析视频或加载已有攻略")
            return
            
        # Confirmation dialog
        reply = QMessageBox.question(
            self,
            "确认开始",
            "确定要开始自动执行吗？\n\n"
            "请确保:\n"
            "1. 原神游戏窗口已打开\n"
            "2. 角色在正确的起始位置\n"
            "3. 紧急停止键(F12)可用",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
            
        self.is_running = True
        self.is_paused = False
        self.engine.start()
        self.status_changed.emit("执行中...")
        
    def pause_execution(self):
        """Pause/resume automation execution"""
        if self.is_running:
            self.is_paused = not self.is_paused
            if self.is_paused:
                self.engine.pause()
                self.status_changed.emit("已暂停")
            else:
                self.engine.resume()
                self.status_changed.emit("执行中...")
                
    def stop_execution(self):
        """Stop automation execution"""
        self.engine.stop()
        self.is_running = False
        self.is_paused = False
        self.status_changed.emit("已停止")
    
    def _on_engine_progress(self, progress: ExecutionProgress):
        """Handle progress updates from engine"""
        self.update_progress(progress.current_step, progress.total_steps)
        self.update_current_step(progress.current_step_description)
        
        if progress.state == ExecutionState.COMPLETED:
            self.is_running = False
            self.control_panel.on_stop_clicked()
            QMessageBox.information(self, "完成", "攻略执行完成！")
        elif progress.state == ExecutionState.ERROR:
            self.is_running = False
            self.control_panel.on_stop_clicked()
            QMessageBox.critical(self, "错误", f"执行出错: {progress.error_message}")
            
    def _on_engine_log(self, message: str):
        """Handle log messages from engine"""
        self.append_log(message)
        
    def append_log(self, message: str):
        """Append message to log output"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_output.append(f"[{timestamp}] {message}")
        # Auto scroll to bottom
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def update_progress(self, current: int, total: int):
        """Update progress display"""
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)
            self.progress_label.setText(f"{current} / {total} 步骤完成")
            
    def update_current_step(self, step_text: str):
        """Update current step display"""
        self.current_step_label.setText(step_text)
        
    def closeEvent(self, event):
        """Handle window close event"""
        if self.is_running:
            reply = QMessageBox.question(
                self,
                "确认退出",
                "自动化任务正在运行中，确定要退出吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
                
        save_config()
        event.accept()
