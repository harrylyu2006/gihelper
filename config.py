"""
Configuration management for Genshin Auto-Guide Helper
"""
import os
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class Config:
    """Application configuration"""
    # OpenAI API settings
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_base_url: str = "https://api.openai.com/v1"
    
    # Game settings
    game_window_title: str = "原神"
    game_resolution_width: int = 1920
    game_resolution_height: int = 1080
    
    # Automation settings
    action_delay_ms: int = 100  # Delay between actions in milliseconds
    screenshot_interval_ms: int = 500  # Screen capture interval
    movement_speed: float = 1.0  # Movement speed multiplier
    
    # Video analysis settings
    frame_sample_interval: float = 1.0  # Extract frame every N seconds
    max_frames_per_analysis: int = 10  # Max frames to send per API call
    
    # Safety settings
    emergency_stop_key: str = "F12"  # Key to emergency stop
    pause_key: str = "F11"  # Key to pause
    
    # Paths
    last_video_path: str = ""
    log_path: str = ""
    
    @classmethod
    def get_config_path(cls) -> Path:
        """Get the configuration file path"""
        # Use AppData on Windows, otherwise use home directory
        if os.name == 'nt':
            app_data = os.environ.get('APPDATA', '')
            config_dir = Path(app_data) / 'GenshinAutoGuide'
        else:
            config_dir = Path.home() / '.genshin_auto_guide'
        
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / 'config.json'
    
    @classmethod
    def load(cls) -> 'Config':
        """Load configuration from file"""
        config_path = cls.get_config_path()
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return cls(**data)
            except (json.JSONDecodeError, TypeError):
                pass
        
        return cls()
    
    def save(self) -> None:
        """Save configuration to file"""
        config_path = self.get_config_path()
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)
    
    def validate(self) -> tuple[bool, list[str]]:
        """Validate configuration, returns (is_valid, error_messages)"""
        errors = []
        
        if not self.openai_api_key:
            errors.append("OpenAI API Key is required")
        
        if self.action_delay_ms < 0:
            errors.append("Action delay must be non-negative")
        
        if self.frame_sample_interval <= 0:
            errors.append("Frame sample interval must be positive")
        
        return len(errors) == 0, errors


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance"""
    global _config
    if _config is None:
        _config = Config.load()
    return _config


def save_config() -> None:
    """Save the global configuration"""
    global _config
    if _config is not None:
        _config.save()
