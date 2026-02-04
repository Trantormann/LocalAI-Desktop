import os
import subprocess
import psutil
import pyautogui
import json
import logging
import platform
from datetime import datetime
from io import BytesIO
import base64
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# 平台检测
PLATFORM = platform.system()  # 'Windows', 'Darwin' (macOS), 'Linux'

class SystemController:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.allowed_commands = config['system'].get('allowed_commands', [])
        self.screenshot_quality = config['system'].get('screenshot_quality', 85)
        
        # 根据平台设置安全命令白名单
        if PLATFORM == 'Windows':
            self.safe_commands = {
                'notepad': 'notepad.exe',
                'calc': 'calc.exe',
                'cmd': 'cmd.exe',
                'taskmgr': 'taskmgr.exe',
                'mspaint': 'mspaint.exe',
                'explorer': 'explorer.exe',
                'control': 'control.exe',
                'powershell': 'powershell.exe'
            }
        elif PLATFORM == 'Darwin':  # macOS
            self.safe_commands = {
                'notepad': ['open', '-a', 'TextEdit'],
                'calc': ['open', '-a', 'Calculator'],
                'mspaint': ['open', '-a', 'Preview'],
                'explorer': ['open', '.'],
                'control': ['open', '-a', 'System Preferences'],
                'taskmgr': ['open', '-a', 'Activity Monitor'],
                'terminal': ['open', '-a', 'Terminal']
            }
        else:  # Linux
            self.safe_commands = {
                'notepad': ['gedit'],
                'calc': ['gnome-calculator'],
                'mspaint': ['gimp'],
                'explorer': ['nautilus', '.'],
                'control': ['gnome-control-center'],
                'taskmgr': ['gnome-system-monitor'],
                'terminal': ['gnome-terminal']
            }
    
    def execute_command(self, command: str) -> Dict[str, Any]:
        """执行系统命令（有限制）"""
        if not self.config['system'].get('allow_system_control', False):
            return {'success': False, 'error': '系统控制功能已禁用'}
        
        # 安全检查
        command_lower = command.lower().strip()
        
        # 预定义程序的启动逻辑
        if command_lower in self.safe_commands:
            try:
                app_cmd = self.safe_commands[command_lower]
                
                if PLATFORM == 'Windows':
                    # Windows: 使用字符串形式
                    subprocess.Popen(
                        [app_cmd] if isinstance(app_cmd, str) else app_cmd,
                        shell=False,
                        start_new_session=True
                    )
                else:
                    # macOS/Linux: 使用列表形式
                    subprocess.Popen(
                        app_cmd if isinstance(app_cmd, list) else [app_cmd],
                        shell=False,
                        start_new_session=True
                    )
                
                return {
                    'success': True,
                    'message': f'已启动 {command}',
                    'command': command
                }
            except Exception as e:
                logger.error(f"启动应用程序失败: {str(e)}")
                return {'success': False, 'error': str(e)}
        
        # 检查是否是已知的安全命令
        elif command_lower in self.allowed_commands:
            try:
                if PLATFORM == 'Windows':
                    result = subprocess.run(
                        command,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=10,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                else:
                    # macOS/Linux 不支持 creationflags
                    result = subprocess.run(
                        command,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                return {
                    'success': True,
                    'output': result.stdout,
                    'error': result.stderr,
                    'return_code': result.returncode
                }
            except subprocess.TimeoutExpired:
                return {'success': False, 'error': '命令执行超时'}
            except Exception as e:
                logger.error(f"执行命令失败: {str(e)}")
                return {'success': False, 'error': str(e)}
        else:
            logger.warning(f"尝试执行未授权的命令: {command}")
            return {
                'success': False,
                'error': f'命令 "{command}" 不在允许列表中'
            }
    
    def take_screenshot(self) -> str:
        """截取屏幕"""
        try:
            screenshot = pyautogui.screenshot()
            
            # 转换为base64
            buffered = BytesIO()
            screenshot.save(buffered, format="PNG", quality=self.screenshot_quality)
            img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            logger.info(f"截图成功，大小: {len(img_base64)} 字符")
            return img_base64
            
        except Exception as e:
            logger.error(f"截图失败: {str(e)}")
            raise
    
    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        try:
            # CPU信息
            # 不使用 interval=1 避免阻塞，改用默认的上次采样
            cpu_percent = psutil.cpu_percent()
            cpu_count = psutil.cpu_count()
            
            # 内存信息
            memory = psutil.virtual_memory()
            
            # 磁盘信息 - 简化处理
            try:
                disk = psutil.disk_usage('C:')
            except Exception:
                try:
                    disk = psutil.disk_usage('/')
                except Exception:
                    # 如果都失败，返回虚拟数据避免崩溃
                    class MockDisk:
                        total = free = used = percent = 0
                    disk = MockDisk()
            
            # 进程信息
            try:
                processes = len(psutil.pids())
            except Exception:
                processes = 0
            
            # 系统启动时间
            try:
                boot_time = datetime.fromtimestamp(psutil.boot_time()).isoformat()
            except Exception:
                boot_time = datetime.now().isoformat()
            
            return {
                'cpu': {
                    'percent': cpu_percent,
                    'cores': cpu_count
                },
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'percent': memory.percent,
                    'used': memory.used
                },
                'disk': {
                    'total': disk.total,
                    'free': disk.free,
                    'percent': disk.percent,
                    'used': disk.used
                },
                'system': {
                    'processes': processes,
                    'boot_time': boot_time
                }
            }
            
        except Exception as e:
            logger.error(f"获取系统信息失败: {str(e)}")
            return {'error': str(e)}
    
    def get_available_apps(self) -> List[str]:
        """获取可用的应用程序列表"""
        apps = list(self.safe_commands.keys())
        
        # 根据平台添加本地化名称
        if PLATFORM == 'Windows':
            localized_apps = [
                '记事本', '计算器', '画图', '资源管理器',
                '控制面板', '任务管理器', '命令提示符', 'PowerShell'
            ]
        elif PLATFORM == 'Darwin':  # macOS
            localized_apps = [
                '文本编辑', '计算器', '预览', '访达',
                '系统偏好设置', '活动监视器', '终端'
            ]
        else:  # Linux
            localized_apps = [
                '文本编辑器', '计算器', '图像编辑器', '文件管理器',
                '系统设置', '系统监视器', '终端'
            ]
        
        return apps + localized_apps
    
    def open_application(self, app_name: str) -> Dict[str, Any]:
        """打开应用程序"""
        # 根据平台设置本地化名称映射
        if PLATFORM == 'Windows':
            app_mapping = {
                '记事本': 'notepad',
                '计算器': 'calc',
                '画图': 'mspaint',
                '资源管理器': 'explorer',
                '控制面板': 'control',
                '任务管理器': 'taskmgr',
                '命令提示符': 'cmd',
                'PowerShell': 'powershell'
            }
        elif PLATFORM == 'Darwin':  # macOS
            app_mapping = {
                '文本编辑': 'notepad',
                '计算器': 'calc',
                '预览': 'mspaint',
                '访达': 'explorer',
                '系统偏好设置': 'control',
                '活动监视器': 'taskmgr',
                '终端': 'terminal'
            }
        else:  # Linux
            app_mapping = {
                '文本编辑器': 'notepad',
                '计算器': 'calc',
                '图像编辑器': 'mspaint',
                '文件管理器': 'explorer',
                '系统设置': 'control',
                '系统监视器': 'taskmgr',
                '终端': 'terminal'
            }
        
        # 转换本地化名称
        if app_name in app_mapping:
            app_name = app_mapping[app_name]
        
        return self.execute_command(app_name)