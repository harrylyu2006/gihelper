"""
Settings dialog for application configuration
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTabWidget, QWidget,
    QFormLayout, QSpinBox, QDoubleSpinBox, QGroupBox,
    QComboBox, QCheckBox, QMessageBox
)
from PyQt6.QtCore import Qt

from config import Config


class SettingsDialog(QDialog):
    """Settings configuration dialog"""
    
    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        """Initialize the UI"""
        self.setWindowTitle("设置 - Settings")
        self.setMinimumSize(600, 500)
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a2e;
            }
            QLabel {
                color: #eee;
            }
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
                background-color: #0f3460;
                color: #eee;
                border: 1px solid #16213e;
                border-radius: 5px;
                padding: 8px;
                min-height: 20px;
            }
            QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
                border-color: #e94560;
            }
            QTabWidget::pane {
                border: 1px solid #0f3460;
                border-radius: 5px;
                background-color: #16213e;
            }
            QTabBar::tab {
                background-color: #0f3460;
                color: #aaa;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background-color: #16213e;
                color: #e94560;
            }
            QGroupBox {
                color: #e94560;
                font-weight: bold;
                border: 1px solid #0f3460;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QCheckBox {
                color: #eee;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 3px;
                border: 1px solid #0f3460;
                background-color: #0f3460;
            }
            QCheckBox::indicator:checked {
                background-color: #e94560;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Tab widget
        tabs = QTabWidget()
        
        # API Settings tab
        api_tab = self.create_api_tab()
        tabs.addTab(api_tab, "🔑 API 设置")
        
        # Game Settings tab
        game_tab = self.create_game_tab()
        tabs.addTab(game_tab, "🎮 游戏设置")
        
        # Automation Settings tab
        auto_tab = self.create_automation_tab()
        tabs.addTab(auto_tab, "⚙️ 自动化设置")
        
        # Safety Settings tab
        safety_tab = self.create_safety_tab()
        tabs.addTab(safety_tab, "🛡️ 安全设置")
        
        layout.addWidget(tabs)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        test_btn = QPushButton("🧪 测试 API 连接")
        test_btn.clicked.connect(self.test_api_connection)
        self.style_button(test_btn)
        btn_layout.addWidget(test_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        self.style_button(cancel_btn)
        btn_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("💾 保存")
        save_btn.clicked.connect(self.save_settings)
        self.style_button(save_btn, primary=True)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
        
    def create_api_tab(self) -> QWidget:
        """Create API settings tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        
        # API Provider settings group
        api_group = QGroupBox("API 设置")
        api_layout = QFormLayout(api_group)
        api_layout.setSpacing(10)
        
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["OpenAI", "Gemini"])
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        api_layout.addRow("API 提供商:", self.provider_combo)
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("sk-...")
        api_layout.addRow("API Key:", self.api_key_input)
        
        self.base_url_input = QLineEdit()
        self.base_url_input.setPlaceholderText("https://api.openai.com/v1")
        api_layout.addRow("Base URL:", self.base_url_input)
        
        layout.addWidget(api_group)
        
        # Model settings group
        model_group = QGroupBox("模型设置")
        model_layout = QFormLayout(model_group)
        model_layout.setSpacing(10)
        
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        model_layout.addRow("模型:", self.model_combo)
        
        layout.addWidget(model_group)
        
        # Info label
        info_label = QLabel(
            "提示: 需要支持 Vision 功能的模型来分析视频内容。\n"
            "推荐使用 gpt-4o 或 gpt-4o-mini。"
        )
        info_label.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(info_label)
        
        layout.addStretch()
        return tab
        
    def create_game_tab(self) -> QWidget:
        """Create game settings tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        
        # Window settings group
        window_group = QGroupBox("游戏窗口")
        window_layout = QFormLayout(window_group)
        window_layout.setSpacing(10)
        
        self.window_title_input = QLineEdit()
        self.window_title_input.setPlaceholderText("原神")
        window_layout.addRow("窗口标题:", self.window_title_input)
        
        res_layout = QHBoxLayout()
        self.width_spin = QSpinBox()
        self.width_spin.setRange(800, 3840)
        self.width_spin.setValue(1920)
        res_layout.addWidget(self.width_spin)
        
        res_layout.addWidget(QLabel("×"))
        
        self.height_spin = QSpinBox()
        self.height_spin.setRange(600, 2160)
        self.height_spin.setValue(1080)
        res_layout.addWidget(self.height_spin)
        
        window_layout.addRow("分辨率:", res_layout)
        
        layout.addWidget(window_group)
        
        layout.addStretch()
        return tab
        
    def create_automation_tab(self) -> QWidget:
        """Create automation settings tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        
        # Timing settings group
        timing_group = QGroupBox("时间设置")
        timing_layout = QFormLayout(timing_group)
        timing_layout.setSpacing(10)
        
        self.action_delay_spin = QSpinBox()
        self.action_delay_spin.setRange(50, 2000)
        self.action_delay_spin.setSuffix(" ms")
        timing_layout.addRow("操作延迟:", self.action_delay_spin)
        
        self.screenshot_interval_spin = QSpinBox()
        self.screenshot_interval_spin.setRange(100, 5000)
        self.screenshot_interval_spin.setSuffix(" ms")
        timing_layout.addRow("截图间隔:", self.screenshot_interval_spin)
        
        layout.addWidget(timing_group)
        
        # Video analysis settings
        video_group = QGroupBox("视频分析")
        video_layout = QFormLayout(video_group)
        video_layout.setSpacing(10)
        
        self.frame_interval_spin = QDoubleSpinBox()
        self.frame_interval_spin.setRange(0.1, 10.0)
        self.frame_interval_spin.setSingleStep(0.1)
        self.frame_interval_spin.setSuffix(" 秒")
        video_layout.addRow("帧采样间隔:", self.frame_interval_spin)
        
        self.max_frames_spin = QSpinBox()
        self.max_frames_spin.setRange(1, 50)
        video_layout.addRow("每次分析最大帧数:", self.max_frames_spin)
        
        layout.addWidget(video_group)
        
        # Movement settings
        movement_group = QGroupBox("移动设置")
        movement_layout = QFormLayout(movement_group)
        movement_layout.setSpacing(10)
        
        self.movement_speed_spin = QDoubleSpinBox()
        self.movement_speed_spin.setRange(0.1, 2.0)
        self.movement_speed_spin.setSingleStep(0.1)
        movement_layout.addRow("移动速度倍率:", self.movement_speed_spin)
        
        layout.addWidget(movement_group)
        
        layout.addStretch()
        return tab
        
    def create_safety_tab(self) -> QWidget:
        """Create safety settings tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        
        # Hotkeys group
        hotkeys_group = QGroupBox("快捷键")
        hotkeys_layout = QFormLayout(hotkeys_group)
        hotkeys_layout.setSpacing(10)
        
        self.emergency_stop_combo = QComboBox()
        self.emergency_stop_combo.addItems(["F12", "F11", "F10", "Escape", "Pause"])
        hotkeys_layout.addRow("紧急停止键:", self.emergency_stop_combo)
        
        self.pause_combo = QComboBox()
        self.pause_combo.addItems(["F11", "F10", "F9", "Pause"])
        hotkeys_layout.addRow("暂停键:", self.pause_combo)
        
        layout.addWidget(hotkeys_group)
        
        layout.addStretch()
        return tab
        
    def style_button(self, button: QPushButton, primary=False):
        """Apply button styling"""
        if primary:
            button.setStyleSheet("""
                QPushButton {
                    background-color: #e94560;
                    color: #fff;
                    border: none;
                    padding: 10px 25px;
                    border-radius: 5px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #ff6b6b;
                }
                QPushButton:pressed {
                    background-color: #c73e54;
                }
            """)
        else:
            button.setStyleSheet("""
                QPushButton {
                    background-color: #0f3460;
                    color: #eee;
                    border: none;
                    padding: 10px 25px;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #1a4a7a;
                }
                QPushButton:pressed {
                    background-color: #0a2540;
                }
            """)
            
    def _on_provider_changed(self, index: int):
        """Handle provider change"""
        provider = self.provider_combo.currentText().lower()
        
        # Update models
        self.model_combo.clear()
        if provider == "openai":
            self.model_combo.addItems([
                "gpt-4o",
                "gpt-4o-mini",
                "gpt-4-turbo",
                "gpt-4-vision-preview",
            ])
            default_url = "https://api.openai.com/v1"
        else:  # gemini
            self.model_combo.addItems([
                "gemini-2.0-flash-exp",
                "gemini-1.5-pro",
                "gemini-1.5-flash",
                "gemini-1.5-flash-8b",
            ])
            default_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
            
        # Update Base URL placeholder
        self.base_url_input.setPlaceholderText(default_url)
        
        # Set default URL if current is empty or matches other default
        current_url = self.base_url_input.text().strip()
        openai_default = "https://api.openai.com/v1"
        gemini_default = "https://generativelanguage.googleapis.com/v1beta/openai/"
        
        if not current_url or current_url in [openai_default, gemini_default]:
            self.base_url_input.setText(default_url)
            
    def load_settings(self):
        """Load settings from config"""
        # API settings
        api_provider = getattr(self.config, 'api_provider', 'openai')
        provider_idx = 0 if api_provider == 'openai' else 1
        self.provider_combo.setCurrentIndex(provider_idx)
        
        # Trigger change handler to set models and defaults
        self._on_provider_changed(provider_idx)
        
        self.api_key_input.setText(self.config.openai_api_key)
        
        # Override URL if set and different from default
        if self.config.openai_base_url:
            self.base_url_input.setText(self.config.openai_base_url)
        
        # Select model
        idx = self.model_combo.findText(self.config.openai_model)
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)
        else:
            self.model_combo.setCurrentText(self.config.openai_model)
            
        # Game settings
        self.window_title_input.setText(self.config.game_window_title)
        self.width_spin.setValue(self.config.game_resolution_width)
        self.height_spin.setValue(self.config.game_resolution_height)
        
        # Automation settings
        self.action_delay_spin.setValue(self.config.action_delay_ms)
        self.screenshot_interval_spin.setValue(self.config.screenshot_interval_ms)
        self.frame_interval_spin.setValue(self.config.frame_sample_interval)
        self.max_frames_spin.setValue(self.config.max_frames_per_analysis)
        self.movement_speed_spin.setValue(self.config.movement_speed)
        
        # Safety settings
        idx = self.emergency_stop_combo.findText(self.config.emergency_stop_key)
        if idx >= 0:
            self.emergency_stop_combo.setCurrentIndex(idx)
            
        idx = self.pause_combo.findText(self.config.pause_key)
        if idx >= 0:
            self.pause_combo.setCurrentIndex(idx)
            
    def save_settings(self):
        """Save settings to config"""
        # API settings
        self.config.api_provider = self.provider_combo.currentText().lower()
        self.config.openai_api_key = self.api_key_input.text().strip()
        self.config.openai_base_url = self.base_url_input.text().strip()
        self.config.openai_model = self.model_combo.currentText()
        
        # Game settings
        self.config.game_window_title = self.window_title_input.text().strip() or "原神"
        self.config.game_resolution_width = self.width_spin.value()
        self.config.game_resolution_height = self.height_spin.value()
        
        # Automation settings
        self.config.action_delay_ms = self.action_delay_spin.value()
        self.config.screenshot_interval_ms = self.screenshot_interval_spin.value()
        self.config.frame_sample_interval = self.frame_interval_spin.value()
        self.config.max_frames_per_analysis = self.max_frames_spin.value()
        self.config.movement_speed = self.movement_speed_spin.value()
        
        # Safety settings
        self.config.emergency_stop_key = self.emergency_stop_combo.currentText()
        self.config.pause_key = self.pause_combo.currentText()
        
        self.accept()
        
    def test_api_connection(self):
        """Test the API connection"""
        api_key = self.api_key_input.text().strip()
        base_url = self.base_url_input.text().strip() or "https://api.openai.com/v1"
        
        if not api_key:
            QMessageBox.warning(self, "警告", "请先输入 API Key")
            return
            
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url=base_url)
            
            # Test with a simple request
            response = client.chat.completions.create(
                model=self.model_combo.currentText(),
                messages=[{"role": "user", "content": "Say 'Hello'"}],
                max_tokens=10
            )
            
            QMessageBox.information(
                self,
                "成功",
                f"✅ API 连接成功！\n\n模型响应: {response.choices[0].message.content}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "错误",
                f"❌ API 连接失败:\n\n{str(e)}"
            )
