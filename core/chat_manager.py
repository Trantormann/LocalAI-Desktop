import json
import requests
from typing import List, Dict, Any, Generator
import logging

logger = logging.getLogger(__name__)

class ChatManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ollama_url = config['ollama']['base_url']
        self.default_model = config['ollama']['default_model']
        
    def get_available_models(self) -> List[str]:
        """获取可用的模型列表"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get('models', [])
                return [model['name'] for model in models]
        except requests.exceptions.ConnectionError:
            logger.warning("无法连接到Ollama服务")
        return ['qwen3:8b', 'qwen3-vl:8b', 'qwen2.5-coder:7b']  # 默认列表
    
    def chat(self, messages: List[Dict], model: str = None, stream: bool = False) -> str:
        """发送聊天消息"""
        if model is None:
            model = self.default_model
        
        # 检查模型是否存在
        available_models = self.get_available_models()
        if available_models and model not in available_models:
            logger.warning(f"模型 {model} 不可用，已安装模型: {available_models}")
            return f"错误: 模型 '{model}' 未安装。\n\n已安装的模型: {', '.join(available_models)}\n\n请运行 install_models.bat 安装模型，或在设置中选择其他模型。"
        
        payload = {
            'model': model,
            'messages': messages,
            'stream': stream,
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
                stream=stream,
                timeout=60
            )
            
            if response.status_code == 200:
                if stream:
                    # 处理流式响应
                    full_response = ""
                    for line in response.iter_lines():
                        if line:
                            data = json.loads(line.decode('utf-8'))
                            if data.get('done', False):
                                break
                            chunk = data.get('message', {}).get('content', '')
                            if chunk:
                                full_response += chunk
                    return full_response
                else:
                    data = response.json()
                    return data.get('message', {}).get('content', '')
            elif response.status_code == 404:
                logger.error(f"模型 {model} 不存在")
                try:
                    error_detail = response.json()
                    logger.error(f"404详情: {error_detail}")
                except:
                    pass
                return f"错误: 模型 '{model}' 未找到。\n\n请确保已通过 Ollama 安装该模型：\nollama pull {model}\n\n或运行 install_models.bat 安装模型。"
            else:
                logger.error(f"Ollama API错误: {response.status_code}")
                try:
                    error_detail = response.json()
                    logger.error(f"错误详情: {error_detail}")
                    return f"错误: Ollama API返回状态码 {response.status_code}\n详情: {error_detail}"
                except:
                    return f"错误: Ollama API返回状态码 {response.status_code}"
                
        except requests.exceptions.ConnectionError:
            logger.error("无法连接到Ollama服务")
            return "错误: 无法连接到本地AI服务。\n\n请确保 Ollama 正在运行：\n1. 检查任务管理器中是否有 ollama 进程\n2. 手动运行: ollama serve\n3. 或重启 start.bat"
        except requests.exceptions.Timeout:
            logger.error("请求超时")
            return "错误: 请求超时。模型可能正在加载，请稍后重试。"
        except Exception as e:
            logger.error(f"聊天请求失败: {str(e)}")
            return f"错误: {str(e)}"
    
    def chat_stream(self, messages: List[Dict], model: str = None) -> Generator[str, None, None]:
        """流式聊天响应"""
        if model is None:
            model = self.default_model
        
        # 检查模型是否存在
        available_models = self.get_available_models()
        if available_models and model not in available_models:
            logger.warning(f"模型 {model} 不可用，已安装模型: {available_models}")
            yield f"\n错误: 模型 '{model}' 未安装。\n\n"
            yield f"已安装的模型: {', '.join(available_models)}\n\n"
            yield "请运行 install_models.bat 安装模型，或在设置中选择其他模型。"
            return
        
        payload = {
            'model': model,
            'messages': messages,
            'stream': True,
            'options': {
                'temperature': 0.7,
                'top_p': 0.9
            }
        }
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json=payload,
                stream=True,
                timeout=60
            )
            
            if response.status_code == 200:
                # 用于过滤 <think> 标签的状态
                in_think_block = False
                buffer = ""
                
                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line.decode('utf-8'))
                            if data.get('done', False):
                                break
                            chunk = data.get('message', {}).get('content', '')
                            if chunk:
                                # 将chunk加入缓冲区处理
                                buffer += chunk
                                
                                # 处理缓冲区，过滤 <think> 内容
                                while True:
                                    if in_think_block:
                                        # 在 think 块内，寻找结束标签
                                        end_idx = buffer.find('</think>')
                                        if end_idx != -1:
                                            # 找到结束标签，跳过 think 内容
                                            buffer = buffer[end_idx + 8:]  # 8 = len('</think>')
                                            in_think_block = False
                                        else:
                                            # 未找到结束标签，清空缓冲区等待更多数据
                                            buffer = ""
                                            break
                                    else:
                                        # 不在 think 块内，寻找开始标签
                                        start_idx = buffer.find('<think>')
                                        if start_idx != -1:
                                            # 找到开始标签，先输出之前的内容
                                            if start_idx > 0:
                                                yield buffer[:start_idx]
                                            buffer = buffer[start_idx + 7:]  # 7 = len('<think>')
                                            in_think_block = True
                                        else:
                                            # 检查是否有不完整的 <think 开始
                                            # 保留可能的部分标签
                                            safe_len = len(buffer)
                                            for i in range(1, min(7, len(buffer) + 1)):
                                                if buffer.endswith('<think>'[:i]):
                                                    safe_len = len(buffer) - i
                                                    break
                                            
                                            if safe_len > 0:
                                                yield buffer[:safe_len]
                                                buffer = buffer[safe_len:]
                                            break
                                            
                        except json.JSONDecodeError:
                            continue
                
                # 输出剩余缓冲区（如果不在think块内）
                if buffer and not in_think_block:
                    yield buffer
            elif response.status_code == 404:
                logger.error(f"模型 {model} 不存在")
                yield f"\n错误: 模型 '{model}' 未找到。\n\n"
                yield f"请确保已通过 Ollama 安装该模型：\n"
                yield f"ollama pull {model}\n\n"
                yield "或运行 install_models.bat 安装模型。"
            else:
                logger.error(f"Ollama API错误: {response.status_code}")
                yield f"\n错误: Ollama API返回状态码 {response.status_code}"
                
        except requests.exceptions.ConnectionError:
            logger.error("无法连接到Ollama服务")
            yield "\n错误: 无法连接到本地AI服务。\n\n"
            yield "请确保 Ollama 正在运行：\n"
            yield "1. 检查任务管理器中是否有 ollama 进程\n"
            yield "2. 手动运行: ollama serve\n"
            yield "3. 或重启 start.bat"
        except requests.exceptions.Timeout:
            logger.error("请求超时")
            yield "\n错误: 请求超时。模型可能正在加载，请稍后重试。"
        except Exception as e:
            logger.error(f"流式聊天失败: {str(e)}")
            yield f"\n错误: {str(e)}"
    
    def check_ollama_connection(self) -> bool:
        """检查Ollama连接"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False