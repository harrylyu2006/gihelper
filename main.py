"""
原神自动攻略助手 - Genshin Auto-Guide Helper
Main entry point for the application
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QSplashScreen, QMessageBox
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QFont


def check_dependencies():
    """Check if required dependencies are installed"""
    missing = []
    
    try:
        import cv2
    except ImportError:
        missing.append("opencv-python")
        
    try:
        import numpy
    except ImportError:
        missing.append("numpy")
        
    try:
        import openai
    except ImportError:
        missing.append("openai")
        
    try:
        import mss
    except ImportError:
        missing.append("mss")
        
    try:
        import pyautogui
    except ImportError:
        missing.append("pyautogui")
        
    return missing


def show_missing_deps_error(missing: list):
    """Show error dialog for missing dependencies"""
    app = QApplication(sys.argv)
    
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Icon.Critical)
    msg.setWindowTitle("缺少依赖 - Missing Dependencies")
    msg.setText("以下依赖包未安装:\n\n" + "\n".join(missing))
    msg.setInformativeText(
        "请运行以下命令安装:\n\n"
        f"pip install {' '.join(missing)}"
    )
    msg.exec()
    
    sys.exit(1)


def create_splash_screen(app: QApplication) -> QSplashScreen:
    """Create a splash screen"""
    # Create a simple splash
    from PyQt6.QtGui import QPainter, QColor, QLinearGradient
    
    pixmap = QPixmap(500, 300)
    pixmap.fill(QColor(26, 26, 46))
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    # Draw gradient background
    gradient = QLinearGradient(0, 0, 500, 300)
    gradient.setColorAt(0, QColor(22, 33, 62))
    gradient.setColorAt(1, QColor(26, 26, 46))
    painter.fillRect(pixmap.rect(), gradient)
    
    # Draw title
    painter.setPen(QColor(233, 69, 96))
    font = QFont("Microsoft YaHei", 24, QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "原神自动攻略助手")
    
    # Draw subtitle
    painter.setPen(QColor(150, 150, 150))
    font = QFont("Microsoft YaHei", 12)
    painter.setFont(font)
    painter.drawText(
        0, 180, 500, 50,
        Qt.AlignmentFlag.AlignCenter,
        "Genshin Auto-Guide Helper"
    )
    
    # Draw loading text
    painter.setPen(QColor(100, 100, 100))
    font = QFont("Microsoft YaHei", 10)
    painter.setFont(font)
    painter.drawText(
        0, 250, 500, 30,
        Qt.AlignmentFlag.AlignCenter,
        "正在加载..."
    )
    
    painter.end()
    
    splash = QSplashScreen(pixmap)
    splash.setWindowFlags(
        Qt.WindowType.WindowStaysOnTopHint | 
        Qt.WindowType.FramelessWindowHint
    )
    
    return splash


def main():
    """Main entry point"""
    # Check dependencies first
    missing = check_dependencies()
    if missing:
        show_missing_deps_error(missing)
        return
        
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("Genshin Auto-Guide Helper")
    app.setApplicationDisplayName("原神自动攻略助手")
    app.setOrganizationName("GenshinAutoGuide")
    
    # Set application style
    app.setStyle("Fusion")
    
    # Show splash screen
    splash = create_splash_screen(app)
    splash.show()
    app.processEvents()
    
    # Import main window (after splash is shown)
    from ui.main_window import MainWindow
    
    # Create main window
    window = MainWindow()
    
    # Hide splash and show main window after a delay
    def show_main():
        splash.finish(window)
        window.show()
        window.append_log("✅ 应用程序已启动")
        window.append_log("📌 请先在设置中配置 OpenAI API Key")
        window.append_log("📹 然后导入攻略视频开始分析")
        
    QTimer.singleShot(1500, show_main)
    
    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
