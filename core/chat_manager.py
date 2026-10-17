import json
import requests
import time
from typing import List, Dict, Any, Generator
import logging

from core.utils import ThinkFilter

logger = logging.getLogger(__name__)

class ChatManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ollama_url = config['ollama']['base_url']
        self.default_model = config['ollama']['default_model']
        # 模型列表缓存
        self._models_cache = None
        self._models_cache_time = 0
        self._cache_ttl = 30  # 缓存有效期30秒
        
    def get_available_models(self, force_refresh: bool = False) -> List[str]:
        """获取可用的模型列表（带缓存）"""
        now = time.time()
        if not force_refresh and self._models_cache is not None and (now - self._models_cache_time) < self._cache_ttl:
            return self._models_cache
        
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                self._models_cache = [model['name'] for model in models]
                self._models_cache_time = now
                return self._models_cache
        except requests.exceptions.ConnectionError:
            logger.warning("无法连接到Ollama服务")
        except requests.exceptions.Timeout:
            logger.warning("获取模型列表超时")
        
        # 返回缓存（即使过期）或默认列表
        if self._models_cache is not None:
            return self._models_cache
        return ['qwen3:8b', 'qwen3-vl:8b', 'qwen2.5-coder:7b']  # 默认列表
    
    def _get_chat_options(self) -> Dict[str, Any]:
        """从配置获取聊天参数"""
        chat_config = self.config.get('chat', {})
        return {
            'temperature': chat_config.get('temperature', 0.7),
            'top_p': chat_config.get('top_p', 0.9),
            'num_predict': chat_config.get('num_predict', 2048)
        }
    
    def chat(self, messages: List[Dict], model: str = None, stream: bool = False) -> str:
        """发送聊天消息"""
        if model is None:
            model = self.default_model
        
        # 检查模型是否存在（使用缓存）
        available_models = self.get_available_models()
        if available_models and model not in available_models:
            logger.warning(f"模型 {model} 不可用，已安装模型: {available_models}")
            return f"错误: 模型 '{model}' 未安装。\n\n已安装的模型: {', '.join(available_models)}\n\n请运行 install_models.bat 安装模型，或在设置中选择其他模型。"
        
        options = self._get_chat_options()
        payload = {
            'model': model,
            'messages': messages,
            'stream': stream,
            'options': options
        }
        
        try:
            # 连接超时 10s，读取超时 300s（模型加载/生成可能较慢）
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json=payload,
                stream=stream,
                timeout=(10, 300)
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
        
        # 检查模型是否存在（使用缓存）
        available_models = self.get_available_models()
        if available_models and model not in available_models:
            logger.warning(f"模型 {model} 不可用，已安装模型: {available_models}")
            yield f"\n错误: 模型 '{model}' 未安装。\n\n"
            yield f"已安装的模型: {', '.join(available_models)}\n\n"
            yield "请运行 install_models.bat 安装模型，或在设置中选择其他模型。"
            return
        
        options = self._get_chat_options()
        payload = {
            'model': model,
            'messages': messages,
            'stream': True,
            'options': options
        }
        
        try:
            # 连接超时 10s，读取超时 300s（模型加载/生成可能较慢）
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json=payload,
                stream=True,
                timeout=(10, 300)
            )
            
            if response.status_code == 200:
                # 使用 ThinkFilter 过滤 <think> 推理内容
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
                
                # 输出剩余缓冲区
                tail = think_filter.flush()
                if tail:
                    yield tail
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
        except Exception:
            return False