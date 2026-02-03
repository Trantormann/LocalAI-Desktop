import base64
from io import BytesIO
from PIL import Image
import requests
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class VisionProcessor:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ollama_url = config['ollama']['base_url']
        self.vision_model = config['ollama'].get('vision_model', 'qwen3-vl:8b')
    
    def get_available_models(self) -> list:
        """获取可用的模型列表"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get('models', [])
                return [model['name'] for model in models]
        except requests.exceptions.ConnectionError:
            logger.warning("无法连接到Ollama服务")
        return []
    
    def analyze_image(self, image_file, prompt: str = "描述这张图片") -> Dict[str, str]:
        """分析图片"""
        try:
            # 检查模型是否存在
            available_models = self.get_available_models()
            if available_models and self.vision_model not in available_models:
                logger.warning(f"视觉模型 {self.vision_model} 不可用，已安装模型: {available_models}")
                return {
                    'analysis': f"错误: 视觉模型 '{self.vision_model}' 未安装。\n\n已安装的模型: {', '.join(available_models)}\n\n请运行 install_models.bat 安装视觉模型（如 qwen3-vl:8b 或 llava:7b）。",
                    'description': '模型未安装'
                }
            
            # 读取图片
            image = Image.open(image_file)
            
            # 调整图片大小（避免太大）
            max_size = (1024, 1024)
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # 转换为base64
            buffered = BytesIO()
            image.save(buffered, format="JPEG", quality=85)
            img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            # 准备请求
            payload = {
                'model': self.vision_model,
                'prompt': prompt,
                'images': [img_base64],
                'stream': False,
                'options': {
                    'temperature': 0.2,
                    'num_predict': 512
                }
            }
            
            # 发送请求
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                analysis = data.get('response', '')
                
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
                    logger.error(f"错误详情: {error_detail}")
                    return {
                        'analysis': f"错误: API返回状态码 {response.status_code}\n详情: {error_detail}",
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
    
    def extract_text_from_image(self, image_file) -> str:
        """从图片中提取文本（OCR功能）"""
        try:
            # 这里可以集成OCR库，如pytesseract
            # 暂时返回简单提示
            return "OCR功能需要安装额外的依赖库。"
        except Exception as e:
            logger.error(f"OCR失败: {str(e)}")
            return f"OCR处理失败: {str(e)}"