"""
Build script for creating Windows executable
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path


def build():
    """Build the application using PyInstaller"""
    # Get the project root directory
    project_root = Path(__file__).parent
    
    # PyInstaller options
    options = [
        'main.py',
        '--name=GenshinAutoGuide',
        '--windowed',  # No console window
        '--onefile',   # Single executable
        '--icon=icon.ico' if (project_root / 'icon.ico').exists() else '',
        f'--distpath={project_root / "dist"}',
        f'--workpath={project_root / "build"}',
        f'--specpath={project_root}',
        '--clean',
        
        # Add hidden imports
        '--hidden-import=PyQt6',
        '--hidden-import=PyQt6.QtCore',
        '--hidden-import=PyQt6.QtWidgets', 
        '--hidden-import=PyQt6.QtGui',
        '--hidden-import=cv2',
        '--hidden-import=numpy',
        '--hidden-import=openai',
        '--hidden-import=mss',
        '--hidden-import=pyautogui',
        '--hidden-import=pydirectinput',
        '--hidden-import=PIL',
        
        # Add data files
        '--add-data=config.py:.',
        '--add-data=README.md:.',
    ]
    
    # Filter empty options
    options = [opt for opt in options if opt]
    
    print("=" * 50)
    print("Building Genshin Auto-Guide Helper")
    print("=" * 50)
    print()
    
    # Check PyInstaller
    try:
        import PyInstaller
        print(f"✅ PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print("❌ PyInstaller not found. Installing...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])
        
    # Clean previous builds
    dist_dir = project_root / 'dist'
    build_dir = project_root / 'build'
    
    if dist_dir.exists():
        print("🧹 Cleaning dist directory...")
        shutil.rmtree(dist_dir)
        
    if build_dir.exists():
        print("🧹 Cleaning build directory...")
        shutil.rmtree(build_dir)
        
    # Run PyInstaller
    print("\n🔨 Running PyInstaller...")
    print(f"   Command: pyinstaller {' '.join(options)}")
    print()
    
    result = subprocess.run(
        [sys.executable, '-m', 'PyInstaller'] + options,
        cwd=project_root,
        capture_output=False
    )
    
    if result.returncode == 0:
        exe_path = dist_dir / 'GenshinAutoGuide.exe'
        print()
        print("=" * 50)
        print("✅ Build successful!")
        print(f"📦 Executable: {exe_path}")
        print("=" * 50)
        
        # Get file size
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"📊 Size: {size_mb:.1f} MB")
    else:
        print()
        print("=" * 50)
        print("❌ Build failed!")
        print("=" * 50)
        sys.exit(1)
        
        
def create_installer():
    """Create an installer using Inno Setup (optional)"""
    # This would create a proper Windows installer
    # Requires Inno Setup to be installed
    pass


if __name__ == '__main__':
    build()
