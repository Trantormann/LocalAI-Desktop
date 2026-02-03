import logging
import os
from datetime import datetime
from typing import Dict, Any

def setup_logging():
    """设置日志配置"""
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    log_file = os.path.join(log_dir, f'localai_{datetime.now().strftime("%Y%m%d")}.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """验证和填充配置"""
    defaults = {
        'webui': {
            'host': '127.0.0.1',
            'port': 7860,
            'debug': False
        },
        'ollama': {
            'base_url': 'http://localhost:11434',
            'default_model': 'qwen3:8b',
            'vision_model': 'qwen3-vl:8b',
            'code_model': 'qwen2.5-coder:7b'
        },
        'system': {
            'allow_system_control': True,
            'enable_agent_mode': True,
            'allowed_commands': ['dir', 'echo', 'type'],
            'screenshot_quality': 85,
            'max_file_size': 5242880  # 5MB
        }
    }
    
    # 合并配置
    for category in defaults:
        if category not in config:
            config[category] = defaults[category]
        else:
            for key in defaults[category]:
                if key not in config[category]:
                    config[category][key] = defaults[category][key]
    
    return config

def format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"