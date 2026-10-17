import logging
import os
import re
import secrets
from logging.handlers import TimedRotatingFileHandler
from typing import Dict, Any


def setup_logging():
    """设置日志配置（按天轮转，保留 14 天，避免重复初始化）"""
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
    os.makedirs(log_dir, exist_ok=True)

    root = logging.getLogger()
    if root.handlers:
        # 已初始化过，避免重复添加 handler 导致日志重复输出
        return
    root.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    file_handler = TimedRotatingFileHandler(
        os.path.join(log_dir, 'localai.log'),
        when='midnight',
        backupCount=14,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)


class ThinkFilter:
    """流式过滤 <think>...</think> 推理内容的状态机。

    跨 chunk 安全：即使标签被拆分到多个 chunk 中也能正确处理，
    并保留可能是未完成标签前缀的尾部字符，避免误输出 "<" 等残片。
    """

    START = '<think>'
    END = '</think>'

    def __init__(self):
        self.in_think = False
        self.buffer = ""

    def feed(self, chunk: str) -> str:
        """输入一个 chunk，返回当前可安全输出的文本。"""
        self.buffer += chunk
        out = []
        while True:
            if self.in_think:
                end_idx = self.buffer.find(self.END)
                if end_idx != -1:
                    self.buffer = self.buffer[end_idx + len(self.END):]
                    self.in_think = False
                else:
                    # 仍在 think 块内：丢弃内容，但保留可能是结束标签前缀的尾部
                    _, self.buffer = self._split_partial(self.buffer, self.END)
                    break
            else:
                start_idx = self.buffer.find(self.START)
                if start_idx != -1:
                    if start_idx > 0:
                        out.append(self.buffer[:start_idx])
                    self.buffer = self.buffer[start_idx + len(self.START):]
                    self.in_think = True
                else:
                    # 输出安全部分，保留可能是开始标签前缀的尾部
                    safe, partial = self._split_partial(self.buffer, self.START)
                    if safe:
                        out.append(safe)
                    self.buffer = partial
                    break
        return ''.join(out)

    def flush(self) -> str:
        """流结束时调用，输出剩余缓冲区内容。"""
        if self.in_think:
            self.buffer = ""
            return ""
        out, self.buffer = self.buffer, ""
        return out

    @staticmethod
    def _split_partial(buffer: str, tag: str):
        """将 buffer 拆分为 (安全输出部分, 可能是 tag 前缀的尾部)。"""
        safe_len = len(buffer)
        for i in range(1, min(len(tag), len(buffer)) + 1):
            if buffer.endswith(tag[:i]):
                safe_len = len(buffer) - i
                break
        return buffer[:safe_len], buffer[safe_len:]


def strip_think(text: str) -> str:
    """从完整文本中移除 <think>...</think> 推理块。"""
    if not text:
        return ''
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    # 处理未闭合的 <think> 块（例如生成被截断）
    cleaned = re.sub(r'<think>.*$', '', cleaned, flags=re.DOTALL)
    return cleaned.strip()

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
            'allowed_commands': ['notepad', 'calc', 'mspaint', 'explorer', 'taskmgr'],
            'screenshot_quality': 85,
            'max_file_size': 5242880  # 5MB
        },
        'chat': {
            'max_history_per_user': 100,
            'num_predict': 2048,
            'temperature': 0.7,
            'top_p': 0.9
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

def generate_secret_key() -> str:
    """生成安全的 Secret Key"""
    return secrets.token_hex(32)

def get_secret_key() -> str:
    """获取 Secret Key，优先从环境变量读取，否则生成并缓存"""
    key = os.environ.get('LOCALAI_SECRET_KEY')
    if key:
        return key
    
    # 尝试从文件读取
    key_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.secret_key')
    if os.path.exists(key_file):
        try:
            with open(key_file, 'r', encoding='utf-8') as f:
                key = f.read().strip()
                if key:
                    return key
        except OSError:
            pass

    # 生成新 key 并保存
    key = generate_secret_key()
    try:
        with open(key_file, 'w', encoding='utf-8') as f:
            f.write(key)
    except OSError:
        pass  # 文件写入失败时仅使用临时 key

    return key

def format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"