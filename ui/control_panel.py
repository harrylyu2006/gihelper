"""
Control panel for automation controls
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal


class ControlPanel(QWidget):
    """Control panel for automation operations"""
    
    start_clicked = pyqtSignal()
    pause_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    analyze_clicked = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.is_running = False
        self.is_paused = False
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Main container
        container = QFrame()
        container.setObjectName("controlContainer")
        container.setStyleSheet("""
            #controlContainer {
                background-color: #16213e;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(15)
        
        # Header
        header = QLabel("🎮 控制面板 / Control Panel")
        header.setStyleSheet("""
            color: #e94560;
            font-size: 18px;
            font-weight: bold;
        """)
        container_layout.addWidget(header)
        
        # Status indicator
        status_layout = QHBoxLayout()
        
        self.status_indicator = QLabel("●")
        self.status_indicator.setStyleSheet("color: #666; font-size: 24px;")
        status_layout.addWidget(self.status_indicator)
        
        self.status_label = QLabel("待机中")
        self.status_label.setStyleSheet("color: #aaa; font-size: 16px;")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        container_layout.addLayout(status_layout)
        
        # Main controls grid
        controls_grid = QGridLayout()
        controls_grid.setSpacing(10)
        
        # Analyze button
        self.analyze_btn = QPushButton("🔍 分析视频")
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.clicked.connect(self.analyze_clicked.emit)
        self.style_button(self.analyze_btn, primary=False)
        controls_grid.addWidget(self.analyze_btn, 0, 0, 1, 2)
        
        # Start button
        self.start_btn = QPushButton("▶️ 开始执行")
        self.start_btn.setEnabled(False)
        self.start_btn.clicked.connect(self.on_start_clicked)
        self.style_button(self.start_btn, primary=True)
        controls_grid.addWidget(self.start_btn, 1, 0)
        
        # Pause button
        self.pause_btn = QPushButton("⏸️ 暂停")
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self.on_pause_clicked)
        self.style_button(self.pause_btn, primary=False)
        controls_grid.addWidget(self.pause_btn, 1, 1)
        
        # Stop button
        self.stop_btn = QPushButton("⏹️ 停止")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.on_stop_clicked)
        self.style_button(self.stop_btn, danger=True)
        controls_grid.addWidget(self.stop_btn, 2, 0, 1, 2)
        
        container_layout.addLayout(controls_grid)
        
        # Hotkey hints
        hints_frame = QFrame()
        hints_frame.setStyleSheet("""
            background-color: rgba(15, 52, 96, 0.5);
            border-radius: 5px;
            padding: 10px;
        """)
        hints_layout = QVBoxLayout(hints_frame)
        hints_layout.setSpacing(5)
        
        hints_title = QLabel("⌨️ 快捷键")
        hints_title.setStyleSheet("color: #e94560; font-weight: bold;")
        hints_layout.addWidget(hints_title)
        
        hints = [
            ("F11", "暂停/继续"),
            ("F12", "紧急停止"),
        ]
        
        for key, desc in hints:
            hint_layout = QHBoxLayout()
            key_label = QLabel(key)
            key_label.setStyleSheet("""
                background-color: #0f3460;
                color: #fff;
                padding: 2px 8px;
                border-radius: 3px;
                font-family: monospace;
            """)
            hint_layout.addWidget(key_label)
            
            desc_label = QLabel(desc)
            desc_label.setStyleSheet("color: #888;")
            hint_layout.addWidget(desc_label)
            
            hint_layout.addStretch()
            hints_layout.addLayout(hint_layout)
            
        container_layout.addWidget(hints_frame)
        
        container_layout.addStretch()
        
        layout.addWidget(container)
        
    def style_button(self, button: QPushButton, primary=False, danger=False):
        """Apply button styling"""
        if primary:
            button.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #e94560, stop:1 #ff6b6b);
                    color: #fff;
                    border: none;
                    padding: 15px 30px;
                    border-radius: 8px;
                    font-size: 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #ff6b6b, stop:1 #e94560);
                }
                QPushButton:pressed {
                    background-color: #c73e54;
                }
                QPushButton:disabled {
                    background: #1a1a2e;
                    color: #555;
                }
            """)
        elif danger:
            button.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #e94560;
                    border: 2px solid #e94560;
                    padding: 15px 30px;
                    border-radius: 8px;
                    font-size: 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #e94560;
                    color: #fff;
                }
                QPushButton:pressed {
                    background-color: #c73e54;
                }
                QPushButton:disabled {
                    border-color: #555;
                    color: #555;
                }
            """)
        else:
            button.setStyleSheet("""
                QPushButton {
                    background-color: #0f3460;
                    color: #eee;
                    border: none;
                    padding: 15px 30px;
                    border-radius: 8px;
                    font-size: 16px;
                }
                QPushButton:hover {
                    background-color: #1a4a7a;
                }
                QPushButton:pressed {
                    background-color: #0a2540;
                }
                QPushButton:disabled {
                    background-color: #1a1a2e;
                    color: #555;
                }
            """)
            
    def set_analyze_enabled(self, enabled: bool):
        """Enable/disable analyze button"""
        self.analyze_btn.setEnabled(enabled)
        
    def set_ready_to_start(self, ready: bool):
        """Set controls ready to start execution"""
        self.start_btn.setEnabled(ready)
        
    def on_start_clicked(self):
        """Handle start button click"""
        self.is_running = True
        self.is_paused = False
        self.update_status("running")
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.analyze_btn.setEnabled(False)
        self.start_clicked.emit()
        
    def on_pause_clicked(self):
        """Handle pause button click"""
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.update_status("paused")
            self.pause_btn.setText("▶️ 继续")
        else:
            self.update_status("running")
            self.pause_btn.setText("⏸️ 暂停")
        self.pause_clicked.emit()
        
    def on_stop_clicked(self):
        """Handle stop button click"""
        self.is_running = False
        self.is_paused = False
        self.update_status("stopped")
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("⏸️ 暂停")
        self.stop_btn.setEnabled(False)
        self.analyze_btn.setEnabled(True)
        self.stop_clicked.emit()
        
    def update_status(self, status: str):
        """Update status display"""
        status_config = {
            "idle": ("●", "#666", "待机中"),
            "analyzing": ("●", "#ffd700", "分析中..."),
            "ready": ("●", "#00bcd4", "准备就绪"),
            "running": ("●", "#4caf50", "执行中..."),
            "paused": ("●", "#ffc107", "已暂停"),
            "stopped": ("●", "#666", "已停止"),
            "error": ("●", "#f44336", "错误"),
        }
        
        if status in status_config:
            indicator, color, text = status_config[status]
            self.status_indicator.setText(indicator)
            self.status_indicator.setStyleSheet(f"color: {color}; font-size: 24px;")
            self.status_label.setText(text)
