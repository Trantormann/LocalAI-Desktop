#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
from typing import Dict, Any, List, Callable, Optional, Generator
import requests

logger = logging.getLogger(__name__)

class AIAgent:
    """AI Agent - 支持 Function Calling 的智能助手"""
    
    def __init__(self, config: Dict[str, Any], system_controller, vision_processor):
        self.config = config
        self.ollama_url = config['ollama']['base_url']
        self.default_model = config['ollama']['default_model']
        self.system_controller = system_controller
        self.vision_processor = vision_processor
        
        # 定义可用的工具函数
        self.tools = self._define_tools()
        
    def _define_tools(self) -> List[Dict[str, Any]]:
        """定义 Agent 可用的工具函数"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "open_application",
                    "description": "打开Windows应用程序，如记事本、计算器、画图、文件资源管理器、任务管理器等",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "app_name": {
                                "type": "string",
                                "description": "应用程序名称",
                                "enum": ["notepad", "calc", "mspaint", "explorer", "taskmgr", "cmd", "powershell", "control"]
                            }
                        },
                        "required": ["app_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "take_screenshot",
                    "description": "截取当前屏幕，用于查看屏幕内容或分析界面",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_system_info",
                    "description": "获取系统信息，包括CPU使用率、内存使用、磁盘空间等",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "execute_command",
                    "description": "执行系统命令（仅限白名单中的安全命令）",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "要执行的命令"
                            }
                        },
                        "required": ["command"]
                    }
                }
            }
        ]
    
    def _get_function_handler(self, function_name: str) -> Optional[Callable]:
        """获取函数处理器"""
        handlers = {
            "open_application": self._handle_open_application,
            "take_screenshot": self._handle_take_screenshot,
            "get_system_info": self._handle_get_system_info,
            "execute_command": self._handle_execute_command
        }
        return handlers.get(function_name)
    
    def _handle_open_application(self, app_name: str) -> Dict[str, Any]:
        """处理打开应用程序"""
        logger.info(f"[Agent] 打开应用程序: {app_name}")
        result = self.system_controller.execute_command(app_name)
        return result
    
    def _handle_take_screenshot(self) -> Dict[str, Any]:
        """处理截图"""
        logger.info(f"[Agent] 执行截图")
        try:
            screenshot_data = self.system_controller.take_screenshot()
            return {
                'success': True,
                'screenshot': screenshot_data,
                'message': '截图成功'
            }
        except Exception as e:
            logger.error(f"截图失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _handle_get_system_info(self) -> Dict[str, Any]:
        """处理获取系统信息"""
        logger.info(f"[Agent] 获取系统信息")
        info = self.system_controller.get_system_info()
        return info
    
    def _handle_execute_command(self, command: str) -> Dict[str, Any]:
        """处理执行命令"""
        logger.info(f"[Agent] 执行命令: {command}")
        result = self.system_controller.execute_command(command)
        return result
    
    def chat_with_tools(self, messages: List[Dict], model: str = None) -> str:
        """支持工具调用的对话"""
        if model is None:
            model = self.default_model
        
        # 第一步：发送消息和工具定义给模型
        payload = {
            'model': model,
            'messages': messages,
            'stream': False,
            'tools': self.tools,
            'options': {
                'temperature': 0.7,
                'top_p': 0.9,
                'num_predict': 512
            }
        }
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                message = result.get('message', {})
                
                # 检查是否有工具调用
                tool_calls = message.get('tool_calls', [])
                
                if tool_calls:
                    # 执行工具调用
                    return self._execute_tool_calls(tool_calls, messages, model)
                else:
                    # 没有工具调用，直接返回回复
                    return message.get('content', '')
            
            elif response.status_code == 404:
                logger.error(f"模型 {model} 不存在")
                return f"错误: 模型 '{model}' 未找到。请确保已通过 Ollama 安装该模型。"
            else:
                error_msg = f"Ollama API返回状态码 {response.status_code}"
                logger.error(error_msg)
                return f"错误: {error_msg}"
                
        except requests.exceptions.ConnectionError:
            error_msg = "无法连接到本地AI服务"
            logger.error(error_msg)
            return f"错误: {error_msg}。请确保 Ollama 正在运行。"
        except requests.exceptions.Timeout:
            error_msg = "请求超时"
            logger.error(error_msg)
            return f"错误: {error_msg}。模型可能正在加载，请稍后重试。"
        except Exception as e:
            logger.error(f"对话错误: {str(e)}")
            return f"错误: {str(e)}"
    
    def _execute_tool_calls(self, tool_calls: List[Dict], messages: List[Dict], model: str) -> str:
        """执行工具调用并继续对话"""
        logger.info(f"[Agent] 检测到 {len(tool_calls)} 个工具调用")
        
        # 添加助手消息（包含工具调用）
        messages.append({
            'role': 'assistant',
            'content': '',
            'tool_calls': tool_calls
        })
        
        # 执行每个工具调用
        for tool_call in tool_calls:
            function_name = tool_call['function']['name']
            raw_arguments = tool_call['function']['arguments']
            
            # 处理参数：有些版本的 Ollama 返回字符串，有些返回字典
            if isinstance(raw_arguments, str):
                try:
                    arguments = json.loads(raw_arguments)
                except json.JSONDecodeError:
                    logger.error(f"解析函数参数失败: {raw_arguments}")
                    arguments = {}
            else:
                arguments = raw_arguments
            
            logger.info(f"[Agent] 调用函数: {function_name}, 参数: {arguments}")
            
            # 获取函数处理器
            handler = self._get_function_handler(function_name)
            if handler:
                result = handler(**arguments)
            else:
                result = {'success': False, 'error': f'未知函数: {function_name}'}
            
            # 添加工具响应到消息历史
            messages.append({
                'role': 'tool',
                'content': json.dumps(result, ensure_ascii=False)
            })
        
        # 第二步：将工具执行结果发送给模型，获取最终回复
        payload = {
            'model': model,
            'messages': messages,
            'stream': False,
            'options': {
                'temperature': 0.7,
                'top_p': 0.9,
                'num_predict': 512
            }
        }
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('message', {}).get('content', '')
            else:
                return f"错误: API返回状态码 {response.status_code}"
                
        except Exception as e:
            logger.error(f"获取最终回复失败: {str(e)}")
            return f"工具执行成功，但获取回复失败: {str(e)}"
    
    def chat_with_tools_stream(self, messages: List[Dict], model: str = None) -> Generator[str, None, None]:
        """支持工具调用的流式对话"""
        if model is None:
            model = self.default_model
        
        # 第一步：发送消息和工具定义给模型（非流式，因为需要判断工具调用）
        payload = {
            'model': model,
            'messages': messages,
            'stream': False,
            'tools': self.tools,
            'options': {
                'temperature': 0.7,
                'top_p': 0.9,
                'num_predict': 512
            }
        }
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                message = result.get('message', {})
                tool_calls = message.get('tool_calls', [])
                
                if tool_calls:
                    # 如果有工具调用，执行工具
                    # 添加助手消息（包含工具调用）
                    messages.append({
                        'role': 'assistant',
                        'content': '',
                        'tool_calls': tool_calls
                    })
                    
                    for tool_call in tool_calls:
                        function_name = tool_call['function']['name']
                        raw_arguments = tool_call['function']['arguments']
                        
                        # 处理参数：有些版本的 Ollama 返回字符串，有些返回字典
                        if isinstance(raw_arguments, str):
                            try:
                                arguments = json.loads(raw_arguments)
                            except json.JSONDecodeError:
                                logger.error(f"解析函数参数失败: {raw_arguments}")
                                arguments = {}
                        else:
                            arguments = raw_arguments
                        
                        handler = self._get_function_handler(function_name)
                        result_data = handler(**arguments) if handler else {'success': False, 'error': f'未知函数: {function_name}'}
                        
                        messages.append({
                            'role': 'tool',
                            'content': json.dumps(result_data, ensure_ascii=False)
                        })
                    
                    # 第二步：执行完工具后，流式输出最终回复
                    final_payload = {
                        'model': model,
                        'messages': messages,
                        'stream': True,
                        'options': {'temperature': 0.7}
                    }
                    
                    final_resp = requests.post(
                        f"{self.ollama_url}/api/chat",
                        json=final_payload,
                        stream=True,
                        timeout=60
                    )
                    
                    full_content = ""
                    for line in final_resp.iter_lines():
                        if line:
                            chunk = json.loads(line.decode('utf-8'))
                            content = chunk.get('message', {}).get('content', '')
                            full_content += content
                            if content:
                                yield content
                    
                    # 将最终完整回复存入历史
                    messages.append({'role': 'assistant', 'content': full_content})
                else:
                    # 没有工具调用，直接流式模拟输出（或直接返回）
                    content = message.get('content', '')
                    # 为了统一流式体验，我们可以把这个字符串切分输出，或者重新发起一个流式请求
                    # 这里为了性能，直接 yield 这个内容，前端会一次性显示，或者分段 yield
                    if content:
                        yield content
                    messages.append({'role': 'assistant', 'content': content})
            else:
                yield f"错误: API返回状态码 {response.status_code}"
                
        except Exception as e:
            logger.error(f"流式对话错误: {str(e)}")
            yield f"错误: {str(e)}"
