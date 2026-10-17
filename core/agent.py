#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
from typing import Dict, Any, List, Callable, Optional, Generator
import requests

from core.utils import ThinkFilter, strip_think

logger = logging.getLogger(__name__)

# 工具显示名称映射
TOOL_DISPLAY_NAMES = {
    'execute_command': '执行命令',
    'open_application': '打开应用',
    'take_screenshot': '截取屏幕',
    'get_system_info': '获取系统信息',
    'analyze_screen': '分析屏幕内容'
}


class AIAgent:
    """AI Agent - 支持 Function Calling 的智能助手"""

    def __init__(self, config: Dict[str, Any], system_controller, vision_processor):
        self.config = config
        self.ollama_url = config['ollama']['base_url']
        self.default_model = config['ollama']['default_model']
        self.system_controller = system_controller
        self.vision_processor = vision_processor
        self.chat_config = config.get('chat', {})

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
                                "enum": ["notepad", "calc", "mspaint", "explorer", "taskmgr", "control", "write", "charmap", "snippingtool"]
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
                    "description": "截取当前屏幕并返回截图，用于查看屏幕内容或分析界面",
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
                    "name": "analyze_screen",
                    "description": "截取当前屏幕并用视觉模型分析屏幕上显示的内容（文字、窗口、界面元素等）。当用户询问屏幕上有什么、帮你看看屏幕、读取屏幕文字时使用此工具",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "想了解屏幕上的什么内容，例如：屏幕上显示了什么文字？当前打开的是什么窗口？"
                            }
                        },
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
    
    def _get_options(self) -> Dict[str, Any]:
        """从配置获取生成参数"""
        return {
            'temperature': self.chat_config.get('temperature', 0.7),
            'top_p': self.chat_config.get('top_p', 0.9),
            'num_predict': self.chat_config.get('num_predict', 2048)
        }
    
    def _get_function_handler(self, function_name: str) -> Optional[Callable]:
        """获取函数处理器"""
        handlers = {
            "open_application": self._handle_open_application,
            "take_screenshot": self._handle_take_screenshot,
            "analyze_screen": self._handle_analyze_screen,
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

    def _handle_analyze_screen(self, question: str = "描述屏幕上显示的内容") -> Dict[str, Any]:
        """截图并用视觉模型分析屏幕内容（产品特色：让 Agent 真正“看懂”屏幕）"""
        logger.info(f"[Agent] 分析屏幕内容: {question}")
        try:
            screenshot_data = self.system_controller.take_screenshot()
            analysis = self.vision_processor.analyze_base64_image(screenshot_data, question)
            return {
                'success': True,
                'analysis': analysis,
                'message': '屏幕分析完成'
            }
        except Exception as e:
            logger.error(f"屏幕分析失败: {str(e)}")
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
        """支持工具调用的对话

        注意：不会修改传入的 messages 列表（避免污染持久化历史），
        工具调用过程中的中间消息仅存在于本次请求的副本中。
        """
        if model is None:
            model = self.default_model

        # 使用副本，避免污染持久化历史
        messages = [dict(m) for m in messages]

        # 第一步：发送消息和工具定义给模型
        payload = {
            'model': model,
            'messages': messages,
            'stream': False,
            'tools': self.tools,
            'options': self._get_options()
        }
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json=payload,
                timeout=120
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
        """执行工具调用并继续对话（messages 已是副本，可安全修改）"""
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

            # 工具结果可能包含大体积数据（如截图 base64），
            # 注入模型上下文前进行裁剪，避免撑爆上下文窗口
            tool_content = self._sanitize_tool_result(function_name, result)

            # 添加工具响应到消息历史
            messages.append({
                'role': 'tool',
                'content': tool_content
            })
        
        # 第二步：将工具执行结果发送给模型，获取最终回复
        payload = {
            'model': model,
            'messages': messages,
            'stream': False,
            'options': self._get_options()
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
    
    def _sanitize_tool_result(self, function_name: str, result: Dict[str, Any]) -> str:
        """将工具结果转换为可安全注入模型上下文的文本。

        截图 base64 等大体积数据不进入上下文（模型无法直接读取 base64，
        应使用 analyze_screen 工具让视觉模型分析），仅保留摘要信息。
        """
        sanitized = dict(result)
        if 'screenshot' in sanitized:
            del sanitized['screenshot']
            sanitized['note'] = '截图已保存。如需了解屏幕内容，请调用 analyze_screen 工具。'
        # 限制工具结果长度，防止异常数据撑爆上下文
        content = json.dumps(sanitized, ensure_ascii=False)
        if len(content) > 4000:
            content = content[:4000] + '...(结果过长已截断)'
        return content

    def chat_with_tools_stream(self, messages: List[Dict], model: str = None) -> Generator[str, None, None]:
        """支持工具调用的流式对话

        注意：不会修改传入的 messages 列表（避免污染持久化历史）。
        """
        if model is None:
            model = self.default_model

        # 使用副本，避免污染持久化历史
        messages = [dict(m) for m in messages]

        # 第一步：尝试发送消息和工具定义给模型
        payload = {
            'model': model,
            'messages': messages,
            'stream': False,
            'tools': self.tools,
            'options': self._get_options()
        }
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json=payload,
                timeout=120
            )
            
            # 如果返回 400，可能是模型不支持 function calling，回退到普通模式
            if response.status_code == 400:
                logger.warning(f"模型 {model} 可能不支持 function calling，回退到普通对话模式")
                yield from self._fallback_stream(messages, model)
                return
            
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

                        # 发送工具调用状态反馈
                        tool_display_name = TOOL_DISPLAY_NAMES.get(function_name, function_name)
                        yield f"\n🔧 正在{tool_display_name}...\n\n"

                        handler = self._get_function_handler(function_name)
                        try:
                            result_data = handler(**arguments) if handler else {'success': False, 'error': f'未知函数: {function_name}'}
                        except TypeError as e:
                            # 模型给出的参数与工具签名不匹配
                            logger.error(f"工具参数错误: {function_name}: {e}")
                            result_data = {'success': False, 'error': f'参数错误: {e}'}
                        except Exception as e:
                            logger.error(f"工具执行异常: {function_name}: {e}")
                            result_data = {'success': False, 'error': str(e)}

                        # 发送工具执行结果摘要
                        if result_data.get('success'):
                            yield f"✅ {tool_display_name}完成\n\n"
                        else:
                            error_msg = result_data.get('error', result_data.get('message', '未知错误'))
                            yield f"❌ {tool_display_name}失败: {error_msg}\n\n"

                        messages.append({
                            'role': 'tool',
                            'content': self._sanitize_tool_result(function_name, result_data)
                        })
                    
                    # 第二步：执行完工具后，流式输出最终回复
                    final_payload = {
                        'model': model,
                        'messages': messages,
                        'stream': True,
                        'options': self._get_options()
                    }
                    
                    final_resp = requests.post(
                        f"{self.ollama_url}/api/chat",
                        json=final_payload,
                        stream=True,
                        timeout=120
                    )

                    # 使用 ThinkFilter 过滤 <think> 推理内容
                    think_filter = ThinkFilter()
                    full_content = ""

                    for line in final_resp.iter_lines():
                        if line:
                            try:
                                chunk = json.loads(line.decode('utf-8'))
                            except json.JSONDecodeError:
                                continue
                            content = chunk.get('message', {}).get('content', '')
                            if content:
                                out = think_filter.feed(content)
                                if out:
                                    full_content += out
                                    yield out

                    # 输出剩余缓冲区
                    tail = think_filter.flush()
                    if tail:
                        full_content += tail
                        yield tail

                    # 将最终完整回复存入本次请求的消息副本（不污染持久化历史）
                    messages.append({'role': 'assistant', 'content': full_content})
                else:
                    # 没有工具调用，直接返回回复（过滤 think 标签）
                    content = strip_think(message.get('content', ''))
                    if content:
                        yield content
                    messages.append({'role': 'assistant', 'content': content})
            else:
                yield f"错误: API返回状态码 {response.status_code}"
                
        except Exception as e:
            logger.error(f"流式对话错误: {str(e)}")
            yield f"错误: {str(e)}"
    
    def _fallback_stream(self, messages: List[Dict], model: str) -> Generator[str, None, None]:
        """回退到普通流式对话（不使用 function calling）"""
        payload = {
            'model': model,
            'messages': messages,
            'stream': True,
            'options': self._get_options()
        }

        try:
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json=payload,
                stream=True,
                timeout=120
            )

            if response.status_code == 200:
                think_filter = ThinkFilter()

                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line.decode('utf-8'))
                        except json.JSONDecodeError:
                            continue
                        if data.get('done', False):
                            break
                        chunk = data.get('message', {}).get('content', '')
                        if chunk:
                            out = think_filter.feed(chunk)
                            if out:
                                yield out

                tail = think_filter.flush()
                if tail:
                    yield tail
            else:
                yield f"错误: API返回状态码 {response.status_code}"
        except Exception as e:
            logger.error(f"回退流式对话错误: {str(e)}")
            yield f"错误: {str(e)}"
