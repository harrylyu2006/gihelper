"""
Video panel for displaying and controlling video playback
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSlider, QFileDialog, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QUrl
from PyQt6.QtGui import QPixmap, QImage, QDragEnterEvent, QDropEvent
import cv2
import os


class VideoPanel(QWidget):
    """Panel for video display and control"""
    
    video_loaded = pyqtSignal(str)  # Emitted when video is loaded
    frame_changed = pyqtSignal(int)  # Emitted when frame changes
    
    def __init__(self):
        super().__init__()
        self.current_video = None
        self.video_capture = None
        self.total_frames = 0
        self.current_frame = 0
        self.fps = 30
        self.is_playing = False
        self.timer = QTimer()
        self.timer.timeout.connect(self.next_frame)
        
        self.init_ui()
        self.setAcceptDrops(True)
        
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Video display area
        self.video_frame = QFrame()
        self.video_frame.setObjectName("videoFrame")
        self.video_frame.setMinimumSize(640, 360)
        self.video_frame.setStyleSheet("""
            #videoFrame {
                background-color: #0d1b2a;
                border: 2px dashed #0f3460;
                border-radius: 10px;
            }
        """)
        
        video_layout = QVBoxLayout(self.video_frame)
        
        # Video label (for displaying frames)
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setText("📹 拖放视频文件到此处\n或点击下方按钮选择视频")
        self.video_label.setStyleSheet("""
            color: #666;
            font-size: 16px;
        """)
        video_layout.addWidget(self.video_label)
        
        layout.addWidget(self.video_frame, stretch=1)
        
        # Video info label
        self.info_label = QLabel("未加载视频")
        self.info_label.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(self.info_label)
        
        # Progress slider
        slider_layout = QHBoxLayout()
        
        self.time_label = QLabel("00:00")
        self.time_label.setStyleSheet("color: #888; min-width: 50px;")
        slider_layout.addWidget(self.time_label)
        
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setMinimum(0)
        self.progress_slider.setMaximum(100)
        self.progress_slider.setValue(0)
        self.progress_slider.sliderMoved.connect(self.seek_frame)
        self.progress_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: none;
                height: 6px;
                background: #0f3460;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #e94560;
                border: none;
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #e94560, stop:1 #ff6b6b);
                border-radius: 3px;
            }
        """)
        slider_layout.addWidget(self.progress_slider, stretch=1)
        
        self.duration_label = QLabel("00:00")
        self.duration_label.setStyleSheet("color: #888; min-width: 50px;")
        slider_layout.addWidget(self.duration_label)
        
        layout.addLayout(slider_layout)
        
        # Control buttons
        control_layout = QHBoxLayout()
        control_layout.setSpacing(10)
        
        self.open_btn = QPushButton("📂 打开视频")
        self.open_btn.clicked.connect(self.open_video)
        self.style_button(self.open_btn)
        control_layout.addWidget(self.open_btn)
        
        self.play_btn = QPushButton("▶️ 播放")
        self.play_btn.clicked.connect(self.toggle_play)
        self.play_btn.setEnabled(False)
        self.style_button(self.play_btn)
        control_layout.addWidget(self.play_btn)
        
        self.prev_btn = QPushButton("⏮️ 上一帧")
        self.prev_btn.clicked.connect(self.prev_frame)
        self.prev_btn.setEnabled(False)
        self.style_button(self.prev_btn)
        control_layout.addWidget(self.prev_btn)
        
        self.next_btn = QPushButton("⏭️ 下一帧")
        self.next_btn.clicked.connect(lambda: self.next_frame(manual=True))
        self.next_btn.setEnabled(False)
        self.style_button(self.next_btn)
        control_layout.addWidget(self.next_btn)
        
        control_layout.addStretch()
        
        layout.addLayout(control_layout)
        
    def style_button(self, button: QPushButton):
        """Apply consistent button styling"""
        button.setStyleSheet("""
            QPushButton {
                background-color: #0f3460;
                color: #eee;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #e94560;
            }
            QPushButton:pressed {
                background-color: #c73e54;
            }
            QPushButton:disabled {
                background-color: #1a1a2e;
                color: #555;
            }
        """)
        
    def open_video(self):
        """Open video file dialog"""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "选择攻略视频",
            "",
            "视频文件 (*.mp4 *.avi *.mkv *.mov *.wmv);;所有文件 (*.*)"
        )
        
        if filepath:
            self.load_video(filepath)
            
    def load_video(self, filepath: str):
        """Load video from file path"""
        if self.video_capture:
            self.video_capture.release()
            
        self.video_capture = cv2.VideoCapture(filepath)
        
        if not self.video_capture.isOpened():
            self.video_label.setText("❌ 无法打开视频文件")
            return
            
        self.current_video = filepath
        self.total_frames = int(self.video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.video_capture.get(cv2.CAP_PROP_FPS) or 30
        self.current_frame = 0
        
        # Update UI
        width = int(self.video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = self.total_frames / self.fps
        
        self.info_label.setText(
            f"📹 {os.path.basename(filepath)} | "
            f"{width}x{height} | "
            f"{self.fps:.1f} FPS | "
            f"{self.format_time(duration)}"
        )
        
        self.progress_slider.setMaximum(self.total_frames - 1)
        self.duration_label.setText(self.format_time(duration))
        
        # Enable controls
        self.play_btn.setEnabled(True)
        self.prev_btn.setEnabled(True)
        self.next_btn.setEnabled(True)
        
        # Show first frame
        self.show_frame(0)
        
        # Emit signal
        self.video_loaded.emit(filepath)
        
    def show_frame(self, frame_num: int):
        """Display a specific frame"""
        if not self.video_capture:
            return
            
        self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = self.video_capture.read()
        
        if ret:
            self.current_frame = frame_num
            
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Resize to fit label while maintaining aspect ratio
            label_size = self.video_label.size()
            h, w = frame_rgb.shape[:2]
            
            # Calculate scaling
            scale_w = label_size.width() / w
            scale_h = label_size.height() / h
            scale = min(scale_w, scale_h, 1.0)  # Don't upscale
            
            new_w = int(w * scale)
            new_h = int(h * scale)
            
            if scale < 1.0:
                frame_rgb = cv2.resize(frame_rgb, (new_w, new_h))
                
            # Convert to QImage
            h, w, ch = frame_rgb.shape
            bytes_per_line = ch * w
            q_img = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            
            # Display
            self.video_label.setPixmap(QPixmap.fromImage(q_img))
            
            # Update progress
            self.progress_slider.setValue(frame_num)
            current_time = frame_num / self.fps
            self.time_label.setText(self.format_time(current_time))
            
            self.frame_changed.emit(frame_num)
            
    def toggle_play(self):
        """Toggle video playback"""
        if self.is_playing:
            self.pause()
        else:
            self.play()
            
    def play(self):
        """Start playback"""
        if not self.video_capture:
            return
            
        self.is_playing = True
        self.play_btn.setText("⏸️ 暂停")
        interval = int(1000 / self.fps)
        self.timer.start(interval)
        
    def pause(self):
        """Pause playback"""
        self.is_playing = False
        self.play_btn.setText("▶️ 播放")
        self.timer.stop()
        
    def next_frame(self, manual=False):
        """Show next frame"""
        if not self.video_capture:
            return
            
        if self.current_frame < self.total_frames - 1:
            self.show_frame(self.current_frame + 1)
        elif not manual:
            # End of video, stop playback
            self.pause()
            
    def prev_frame(self):
        """Show previous frame"""
        if not self.video_capture:
            return
            
        if self.current_frame > 0:
            self.show_frame(self.current_frame - 1)
            
    def seek_frame(self, frame_num: int):
        """Seek to specific frame"""
        self.show_frame(frame_num)
        
    def format_time(self, seconds: float) -> str:
        """Format seconds to MM:SS"""
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            
    def dropEvent(self, event: QDropEvent):
        """Handle file drop"""
        urls = event.mimeData().urls()
        if urls:
            filepath = urls[0].toLocalFile()
            if filepath.lower().endswith(('.mp4', '.avi', '.mkv', '.mov', '.wmv')):
                self.load_video(filepath)
                
    def get_current_frame_image(self):
        """Get the current frame as numpy array"""
        if not self.video_capture:
            return None
            
        self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        ret, frame = self.video_capture.read()
        
        if ret:
            return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return None
        
    def closeEvent(self, event):
        """Clean up on close"""
        if self.video_capture:
            self.video_capture.release()
        self.timer.stop()
        event.accept()
