import base64
from io import BytesIO
from PIL import Image
import requests
import time
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class VisionProcessor:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ollama_url = config['ollama']['base_url']
        self.vision_model = config['ollama'].get('vision_model', 'qwen3-vl:8b')
        # 模型列表缓存
        self._models_cache = None
        self._models_cache_time = 0
        self._cache_ttl = 30
    
    def get_available_models(self, force_refresh: bool = False) -> list:
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
        
        if self._models_cache is not None:
            return self._models_cache
        return []
    
    def _encode_image(self, image: Image.Image, max_size: tuple = (1024, 1024), quality: int = 85) -> str:
        """将 PIL 图片缩放并编码为 base64 JPEG"""
        # 转换为 RGB（避免 PNG 透明通道/调色板模式导致 JPEG 编码失败）
        if image.mode not in ('RGB', 'L'):
            image = image.convert('RGB')

        # 调整图片大小（避免太大）
        image.thumbnail(max_size, Image.Resampling.LANCZOS)

        # 转换为base64
        buffered = BytesIO()
        image.save(buffered, format="JPEG", quality=quality)
        return base64.b64encode(buffered.getvalue()).decode('utf-8')

    def analyze_base64_image(self, img_base64: str, prompt: str = "描述这张图片") -> str:
        """分析 base64 编码的图片（供 Agent 的 analyze_screen 工具使用）"""
        try:
            available_models = self.get_available_models()
            if available_models and self.vision_model not in available_models:
                return f"错误: 视觉模型 '{self.vision_model}' 未安装，无法分析图片。"

            chat_config = self.config.get('chat', {})
            payload = {
                'model': self.vision_model,
                'messages': [{
                    'role': 'user',
                    'content': prompt,
                    'images': [img_base64]
                }],
                'stream': False,
                'options': {
                    'temperature': 0.2,
                    'num_predict': chat_config.get('num_predict', 2048)
                }
            }

            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json=payload,
                timeout=(10, 300)
            )

            if response.status_code == 200:
                data = response.json()
                return data.get('message', {}).get('content', '')
            else:
                logger.error(f"视觉分析API错误: {response.status_code}")
                return f"错误: 视觉分析API返回状态码 {response.status_code}"
        except Exception as e:
            logger.error(f"base64图片分析失败: {str(e)}")
            return f"错误: {str(e)}"

    def analyze_image(self, image_file, prompt: str = "描述这张图片") -> Dict[str, str]:
        """分析图片 - 使用 /api/chat 端点（统一API风格，支持多轮对话上下文）"""
        try:
            # 检查模型是否存在（使用缓存）
            available_models = self.get_available_models()
            if available_models and self.vision_model not in available_models:
                logger.warning(f"视觉模型 {self.vision_model} 不可用，已安装模型: {available_models}")
                return {
                    'analysis': f"错误: 视觉模型 '{self.vision_model}' 未安装。\n\n已安装的模型: {', '.join(available_models)}\n\n请运行 install_models.bat 安装视觉模型（如 qwen3-vl:8b 或 llava:7b）。",
                    'description': '模型未安装'
                }
            
            # 读取图片
            image = Image.open(image_file)

            # 缩放并编码为 base64
            img_base64 = self._encode_image(image)
            
            # 使用 /api/chat 端点（统一风格，支持多轮对话）
            chat_config = self.config.get('chat', {})
            payload = {
                'model': self.vision_model,
                'messages': [{
                    'role': 'user',
                    'content': prompt,
                    'images': [img_base64]
                }],
                'stream': False,
                'options': {
                    'temperature': 0.2,
                    'num_predict': chat_config.get('num_predict', 2048)
                }
            }
            
            # 发送请求
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json=payload,
                timeout=(10, 300)
            )
            
            if response.status_code == 200:
                data = response.json()
                # /api/chat 返回格式: {message: {content: "..."}}
                analysis = data.get('message', {}).get('content', '') or data.get('response', '')
                
                # 生成基本描述
                description = self._generate_description(image, analysis)
                
                return {
                    'analysis': analysis,
                    'description': description
                }
            elif response.status_code == 404:
                logger.error(f"视觉模型 {self.vision_model} 不存在")
                return {
                    'analysis': f"错误: 视觉模型 '{self.vision_model}' 未找到。\n\n请确保已通过 Ollama 安装该模型：\nollama pull {self.vision_model}\n\n或运行 install_models.bat 安装视觉模型。",
                    'description': '模型未找到'
                }
            else:
                logger.error(f"视觉分析API错误: {response.status_code}")
                try:
                    error_detail = response.json()
                    error_msg = error_detail.get('error', str(error_detail))
                    logger.error(f"错误详情: {error_msg}")
                    
                    # 检查是否是模型加载失败
                    if 'unable to load model' in error_msg.lower():
                        return {
                            'analysis': f"错误: 视觉模型 '{self.vision_model}' 加载失败。\n\n可能的原因：\n1. 模型文件损坏\n2. 模型下载不完整\n\n解决方案：\n1. 删除并重新下载模型：\n   ollama rm {self.vision_model}\n   ollama pull {self.vision_model}\n\n2. 或者尝试其他视觉模型：\n   ollama pull llava:7b",
                            'description': '模型加载失败'
                        }
                    
                    return {
                        'analysis': f"错误: API返回状态码 {response.status_code}\n详情: {error_msg}",
                        'description': '分析失败'
                    }
                except:
                    return {
                        'analysis': f"错误: API返回状态码 {response.status_code}",
                        'description': '分析失败'
                    }
                
        except requests.exceptions.ConnectionError:
            logger.error("无法连接到Ollama服务")
            return {
                'analysis': "错误: 无法连接到本地AI服务。\n\n请确保 Ollama 正在运行：\n1. 检查任务管理器中是否有 ollama 进程\n2. 手动运行: ollama serve\n3. 或重启 start.bat",
                'description': '连接失败'
            }
        except requests.exceptions.Timeout:
            logger.error("请求超时")
            return {
                'analysis': "错误: 请求超时。模型可能正在加载，请稍后重试。",
                'description': '请求超时'
            }
        except Exception as e:
            logger.error(f"图片分析失败: {str(e)}")
            return {
                'analysis': f"错误: {str(e)}",
                'description': '处理失败'
            }
    
    def _generate_description(self, image: Image.Image, analysis: str) -> str:
        """生成图片描述"""
        width, height = image.size
        format_name = image.format if image.format else '未知'
        
        description = f"""
        图片信息:
        - 尺寸: {width} x {height} 像素
        - 格式: {format_name}
        - 模式: {image.mode}
        
        分析结果:
        {analysis}
        """
        
        return description