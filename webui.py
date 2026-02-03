#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import logging
import threading
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
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
from core.utils import setup_logging, validate_config

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

# 验证配置
config = validate_config(config)

# 创建Flask应用
app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')
app.config['SECRET_KEY'] = 'localai-desktop-secret-key-2024'
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

# 存储对话历史
conversations = {}

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html', 
                         models=chat_manager.get_available_models())

@app.route('/config.json')
def get_config():
    """返回配置文件内容"""
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/models')
def get_models():
    """获取可用模型列表"""
    models = chat_manager.get_available_models()
    return jsonify({'models': models})

@app.route('/api/chat', methods=['POST'])
def chat():
    """文本对话API"""
    data = request.json
    user_id = data.get('user_id', 'default')
    message = data.get('message', '')
    model = data.get('model', config['ollama']['default_model'])
    use_agent = data.get('use_agent', True)  # 默认启用 Agent 模式
    
    if not message:
        return jsonify({'error': '消息不能为空'}), 400
    
    # 初始化用户对话历史
    if user_id not in conversations:
        conversations[user_id] = []
    
    # 添加用户消息到历史
    conversations[user_id].append({'role': 'user', 'content': message})
    
    try:
        # 判断是否使用 Agent 模式
        if use_agent and config['system'].get('allow_system_control', False):
            # 使用 Agent 模式，支持工具调用
            response = agent.chat_with_tools(
                messages=conversations[user_id],
                model=model
            )
        else:
            # 普通对话模式
            response = chat_manager.chat(
                messages=conversations[user_id],
                model=model,
                stream=False
            )
        
        # 添加AI回复到历史
        conversations[user_id].append({'role': 'assistant', 'content': response})
        
        return jsonify({
            'response': response,
            'history': conversations[user_id][-10:]  # 返回最近10条
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
    
    data = request.json
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
    data = request.json
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
    user_id = data.get('user_id', 'default')
    message = data.get('message', '')
    model = data.get('model', config['ollama']['default_model'])
    use_agent = data.get('use_agent', True)  # 默认启用 Agent 模式
    
    if not message:
        emit('error', {'message': '消息不能为空'})
        return
    
    # 初始化用户对话历史
    if user_id not in conversations:
        conversations[user_id] = []
    
    # 添加用户消息
    conversations[user_id].append({'role': 'user', 'content': message})
    
    # 获取当前会话ID
    from flask import request
    session_id = request.sid
    
    try:
        # 判断是否使用 Agent 模式
        if use_agent and config['system'].get('allow_system_control', False):
            # Agent 模式：流式输出
            def agent_response():
                try:
                    full_response = ""
                    for chunk in agent.chat_with_tools_stream(
                        messages=conversations[user_id],
                        model=model
                    ):
                        full_response += chunk
                        socketio.emit('chat_chunk', {
                            'chunk': chunk,
                            'done': False
                        }, room=session_id)
                    
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
                for chunk in chat_manager.chat_stream(
                    messages=conversations[user_id],
                    model=model
                ):
                    full_response += chunk
                    socketio.emit('chat_chunk', {
                        'chunk': chunk,
                        'done': False
                    }, room=session_id)
                
                # 添加AI回复到历史
                conversations[user_id].append({'role': 'assistant', 'content': full_response})
                
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