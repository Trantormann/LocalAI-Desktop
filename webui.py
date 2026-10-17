#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import logging
import threading
import time
import hashlib
import functools
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory, g
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import base64
from io import BytesIO

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.chat_manager import ChatManager
from core.vision_processor import VisionProcessor
from core.system_control import SystemController
from core.agent import AIAgent
from core.utils import setup_logging, validate_config, get_secret_key, strip_think

# 设置日志
setup_logging()
logger = logging.getLogger(__name__)

# 加载配置
try:
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
except FileNotFoundError:
    logger.error("配置文件 config.json 未找到")
    config = {
        'webui': {'host': '127.0.0.1', 'port': 7860, 'debug': False},
        'ollama': {'base_url': 'http://localhost:11434'}
    }
except json.JSONDecodeError as e:
    logger.error(f"配置文件 config.json 格式错误: {e}")
    config = {
        'webui': {'host': '127.0.0.1', 'port': 7860, 'debug': False},
        'ollama': {'base_url': 'http://localhost:11434'}
    }

# 验证配置
config = validate_config(config)

# 创建Flask应用
app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')
# 使用安全的 Secret Key
app.config['SECRET_KEY'] = get_secret_key()
app.config['MAX_CONTENT_LENGTH'] = config['system']['max_file_size']

# 启用CORS
CORS(app)

# 初始化SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# 初始化核心模块
chat_manager = ChatManager(config)
vision_processor = VisionProcessor(config)
system_controller = SystemController(config)

# 初始化 AI Agent
agent = AIAgent(config, system_controller, vision_processor)

# ============ 认证机制 ============
AUTH_TOKEN = os.environ.get('LOCALAI_AUTH_TOKEN', '')

def require_auth(f):
    """API认证装饰器 - 如果设置了环境变量 LOCALAI_AUTH_TOKEN 则要求认证"""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not AUTH_TOKEN:
            return f(*args, **kwargs)
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if token != AUTH_TOKEN:
            return jsonify({'error': '未授权访问'}), 401
        return f(*args, **kwargs)
    return decorated

# ============ 对话历史管理 ============
class ConversationManager:
    """对话历史管理器 - 支持持久化、长度限制和线程安全"""

    def __init__(self, config):
        self.config = config
        self.max_history = config.get('chat', {}).get('max_history_per_user', 100)
        self.conversations = {}
        self._lock = threading.RLock()
        self._data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        os.makedirs(self._data_dir, exist_ok=True)

    def get(self, user_id: str) -> list:
        """获取用户对话历史（返回副本，避免外部修改内部状态）"""
        with self._lock:
            if user_id not in self.conversations:
                self.conversations[user_id] = self._load_from_disk(user_id)
            return list(self.conversations[user_id])

    def append(self, user_id: str, message: dict):
        """添加消息到对话历史"""
        with self._lock:
            if user_id not in self.conversations:
                self.conversations[user_id] = self._load_from_disk(user_id)
            self.conversations[user_id].append(message)
            # 超过上限时裁剪，保留最近的历史
            if len(self.conversations[user_id]) > self.max_history:
                self.conversations[user_id] = self.conversations[user_id][-self.max_history:]
            self._save_to_disk(user_id)

    def clear(self, user_id: str):
        """清空用户对话历史"""
        with self._lock:
            self.conversations[user_id] = []
            self._save_to_disk(user_id)
    
    def _disk_path(self, user_id: str) -> str:
        safe_id = hashlib.sha256(user_id.encode()).hexdigest()[:16]
        return os.path.join(self._data_dir, f'conv_{safe_id}.json')
    
    def _load_from_disk(self, user_id: str) -> list:
        path = self._disk_path(user_id)
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return []
        return []
    
    def _save_to_disk(self, user_id: str):
        path = self._disk_path(user_id)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.conversations[user_id], f, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存对话历史失败: {e}")

# 存储对话历史
conv_manager = ConversationManager(config)

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html', 
                         models=chat_manager.get_available_models())

@app.route('/api/config/safe')
@require_auth
def get_safe_config():
    """返回安全的配置信息（不暴露敏感字段）"""
    safe_config = {
        'ollama': {
            'base_url': config['ollama']['base_url'],
            'default_model': config['ollama']['default_model'],
            'vision_model': config['ollama'].get('vision_model', ''),
            'code_model': config['ollama'].get('code_model', '')
        },
        'system': {
            'allow_system_control': config['system']['allow_system_control'],
            'enable_agent_mode': config['system'].get('enable_agent_mode', True),
            'allowed_commands': config['system']['allowed_commands'],
            'screenshot_quality': config['system']['screenshot_quality'],
            'max_file_size': config['system']['max_file_size']
        },
        'chat': {
            'max_history_per_user': config.get('chat', {}).get('max_history_per_user', 100),
            'num_predict': config.get('chat', {}).get('num_predict', 2048)
        }
    }
    return jsonify(safe_config)

@app.route('/api/models')
def get_models():
    """获取可用模型列表"""
    models = chat_manager.get_available_models()
    return jsonify({'models': models})

@app.route('/api/settings', methods=['POST'])
@require_auth
def save_settings():
    """保存设置到 config.json（仅允许修改安全字段）"""
    try:
        data = request.json or {}

        # 允许修改的字段白名单
        if 'ollama' in data:
            ollama = data['ollama']
            if 'base_url' in ollama and isinstance(ollama['base_url'], str) and ollama['base_url'].strip():
                config['ollama']['base_url'] = ollama['base_url'].strip()
        if 'system' in data:
            system = data['system']
            if 'allow_system_control' in system:
                config['system']['allow_system_control'] = bool(system['allow_system_control'])
            if 'enable_agent_mode' in system:
                config['system']['enable_agent_mode'] = bool(system['enable_agent_mode'])
            if 'allowed_commands' in system and isinstance(system['allowed_commands'], list):
                # 过滤空白项，限制数量
                cmds = [str(c).strip() for c in system['allowed_commands'] if str(c).strip()]
                config['system']['allowed_commands'] = cmds[:50]
            if 'screenshot_quality' in system:
                try:
                    q = int(system['screenshot_quality'])
                    config['system']['screenshot_quality'] = max(10, min(100, q))
                except (ValueError, TypeError):
                    pass
            if 'max_file_size' in system:
                try:
                    s = int(system['max_file_size'])
                    config['system']['max_file_size'] = max(1024 * 1024, min(50 * 1024 * 1024, s))
                except (ValueError, TypeError):
                    pass

        # 同步运行时对象
        system_controller.allowed_commands = config['system']['allowed_commands']
        system_controller.screenshot_quality = config['system']['screenshot_quality']
        app.config['MAX_CONTENT_LENGTH'] = config['system']['max_file_size']

        # 写入 config.json
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        logger.info("设置已保存到 config.json")
        return jsonify({'success': True, 'message': '设置已保存'})
    except Exception as e:
        logger.error(f"保存设置失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/history/<user_id>', methods=['GET'])
def get_history(user_id):
    """获取用户对话历史（用于刷新页面后恢复对话）"""
    history = conv_manager.get(user_id)
    return jsonify({'history': history[-50:]})

@app.route('/api/history/<user_id>', methods=['DELETE'])
def clear_history(user_id):
    """清空用户对话历史"""
    conv_manager.clear(user_id)
    return jsonify({'success': True, 'message': '对话已清空'})

@app.route('/api/chat', methods=['POST'])
def chat():
    """文本对话API"""
    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id', 'default')
    message = data.get('message', '')
    model = data.get('model', config['ollama']['default_model'])
    use_agent = data.get('use_agent', True)  # 默认启用 Agent 模式
    
    if not message:
        return jsonify({'error': '消息不能为空'}), 400
    
    # 获取用户对话历史副本（Agent 不会修改它）
    history = conv_manager.get(user_id)

    # 添加用户消息到历史
    conv_manager.append(user_id, {'role': 'user', 'content': message})
    history.append({'role': 'user', 'content': message})
    
    try:
        # 判断是否使用 Agent 模式
        if use_agent and config['system'].get('allow_system_control', False):
            # 使用 Agent 模式，支持工具调用
            response = agent.chat_with_tools(
                messages=history,
                model=model
            )
        else:
            # 普通对话模式
            response = chat_manager.chat(
                messages=history,
                model=model,
                stream=False
            )
        
        # 添加AI回复到历史
        conv_manager.append(user_id, {'role': 'assistant', 'content': response})
        
        updated_history = conv_manager.get(user_id)
        return jsonify({
            'response': response,
            'history': updated_history[-10:]  # 返回最近10条
        })
    except Exception as e:
        logger.error(f"聊天错误: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/vision', methods=['POST'])
def vision_analysis():
    """图像理解API"""
    try:
        if 'image' not in request.files:
            return jsonify({'error': '没有上传图片'}), 400
        
        image_file = request.files['image']
        prompt = request.form.get('prompt', '描述这张图片')
        
        # 处理图像
        result = vision_processor.analyze_image(image_file, prompt)
        
        return jsonify({
            'analysis': result['analysis'],
            'description': result['description']
        })
    except Exception as e:
        logger.error(f"视觉分析错误: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/system/info', methods=['GET'])
def get_system_info():
    """获取系统信息"""
    try:
        info = system_controller.get_system_info()
        return jsonify(info)
    except Exception as e:
        logger.error(f"获取系统信息错误: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/system/command', methods=['POST'])
def system_command():
    """系统命令API"""
    if not config['system']['allow_system_control']:
        return jsonify({'error': '系统控制功能已禁用'}), 403
    
    data = request.get_json(silent=True) or {}
    command = data.get('command', '')
    
    if not command:
        return jsonify({'error': '命令不能为空'}), 400
    
    try:
        result = system_controller.execute_command(command)
        return jsonify(result)
    except Exception as e:
        logger.error(f"系统命令错误: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/system/screenshot', methods=['GET'])
def take_screenshot():
    """屏幕截图API"""
    try:
        screenshot_data = system_controller.take_screenshot()
        
        # 返回base64编码的图片
        return jsonify({
            'screenshot': f"data:image/png;base64,{screenshot_data}",
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"截图错误: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/system/apps', methods=['GET'])
def get_applications():
    """获取可用应用程序列表"""
    try:
        apps = system_controller.get_available_apps()
        return jsonify({'applications': apps})
    except Exception as e:
        logger.error(f"获取应用程序错误: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/system/open-app', methods=['POST'])
def open_application():
    """打开应用程序"""
    data = request.get_json(silent=True) or {}
    app_name = data.get('app', '')
    
    if not app_name:
        return jsonify({'error': '应用程序名不能为空'}), 400
    
    try:
        result = system_controller.open_application(app_name)
        return jsonify(result)
    except Exception as e:
        logger.error(f"打开应用程序错误: {str(e)}")
        return jsonify({'error': str(e)}), 500

# WebSocket事件处理
@socketio.on('connect')
def handle_connect():
    """客户端连接事件"""
    logger.info('客户端已连接')
    emit('connected', {'message': '连接成功'})

@socketio.on('chat_message')
def handle_chat_message(data):
    """WebSocket聊天消息"""
    data = data or {}
    user_id = data.get('user_id', 'default')
    message = data.get('message', '')
    model = data.get('model', config['ollama']['default_model'])
    use_agent = data.get('use_agent', True)  # 默认启用 Agent 模式
    
    if not message:
        emit('error', {'message': '消息不能为空'})
        return
    
    # 获取用户对话历史副本
    history = conv_manager.get(user_id)
    
    # 添加用户消息
    conv_manager.append(user_id, {'role': 'user', 'content': message})
    history.append({'role': 'user', 'content': message})
    
    # 获取当前会话ID（flask.request 在 socketio 事件处理器中被注入 sid 属性）
    session_id = request.sid
    
    try:
        # 判断是否使用 Agent 模式
        if use_agent and config['system'].get('allow_system_control', False):
            # Agent 模式：流式输出
            def agent_response():
                try:
                    full_response = ""
                    current_history = conv_manager.get(user_id)
                    for chunk in agent.chat_with_tools_stream(
                        messages=current_history,
                        model=model
                    ):
                        full_response += chunk
                        socketio.emit('chat_chunk', {
                            'chunk': chunk,
                            'done': False
                        }, room=session_id)

                    # 保存AI回复到历史（过滤 think 内容）
                    full_response = strip_think(full_response)
                    conv_manager.append(user_id, {'role': 'assistant', 'content': full_response})
                    
                    # 发送结束标志
                    socketio.emit('chat_chunk', {
                        'chunk': '',
                        'done': True,
                        'full_response': full_response
                    }, room=session_id)
                except Exception as e:
                    logger.error(f"Agent 流式处理错误: {str(e)}")
                    socketio.emit('error', {'message': str(e)}, room=session_id)
            
            # 在新线程中处理
            thread = threading.Thread(target=agent_response)
            thread.start()
        else:
            # 普通流式响应
            def stream_response():
                full_response = ""
                current_history = conv_manager.get(user_id)
                for chunk in chat_manager.chat_stream(
                    messages=current_history,
                    model=model
                ):
                    full_response += chunk
                    socketio.emit('chat_chunk', {
                        'chunk': chunk,
                        'done': False
                    }, room=session_id)
                
                # 添加AI回复到历史（过滤 think 内容）
                full_response = strip_think(full_response)
                conv_manager.append(user_id, {'role': 'assistant', 'content': full_response})
                
                socketio.emit('chat_chunk', {
                    'chunk': '',
                    'done': True,
                    'full_response': full_response
                }, room=session_id)
            
            # 在新线程中处理流式响应
            thread = threading.Thread(target=stream_response)
            thread.start()
        
    except Exception as e:
        logger.error(f"WebSocket聊天错误: {str(e)}")
        emit('error', {'message': str(e)})

@app.route('/health')
def health_check():
    """健康检查端点"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'ollama_connected': chat_manager.check_ollama_connection()
    })

def main():
    """主函数"""
    logger.info("启动 LocalAI-Desktop WebUI...")
    logger.info(f"服务地址: http://{config['webui']['host']}:{config['webui']['port']}")
    
    try:
        socketio.run(
            app,
            host=config['webui']['host'],
            port=config['webui']['port'],
            debug=config['webui']['debug'],
            allow_unsafe_werkzeug=True
        )
    except KeyboardInterrupt:
        logger.info("正在关闭服务...")
    except Exception as e:
        logger.error(f"启动服务失败: {str(e)}")

if __name__ == '__main__':
    main()