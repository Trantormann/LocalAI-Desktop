#!/bin/bash

# LocalAI-Desktop macOS/Linux 一键部署脚本
# 版本: v1.2.0

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 获取脚本所在目录，然后切换到项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."
PROJECT_DIR="$(pwd)"

echo "========================================"
echo "   LocalAI-Desktop 一键部署工具"
echo "========================================"
echo ""
echo "版本: v1.2.0"
echo "适用系统: macOS / Linux"
echo "项目目录: $PROJECT_DIR"
echo ""
echo "========================================"
echo ""

# 检测操作系统
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macOS"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="Linux"
    else
        echo -e "${RED}[错误] 不支持的操作系统: $OSTYPE${NC}"
        exit 1
    fi
    echo -e "${GREEN}[OK] 检测到操作系统: $OS${NC}"
}

# 检查 Python
check_python() {
    echo "[检查] Python 安装状态..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo -e "${RED}[错误] Python 未安装!${NC}"
        echo ""
        if [[ "$OS" == "macOS" ]]; then
            echo "请使用 Homebrew 安装: brew install python3"
        else
            echo "请使用包管理器安装: sudo apt install python3 (Ubuntu/Debian)"
            echo "                    sudo dnf install python3 (Fedora)"
        fi
        exit 1
    fi
    
    # 检查版本
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
    
    if [[ $PYTHON_MAJOR -lt 3 ]] || [[ $PYTHON_MAJOR -eq 3 && $PYTHON_MINOR -lt 10 ]]; then
        echo -e "${YELLOW}[警告] Python 版本 $PYTHON_VERSION 低于 3.10，建议升级${NC}"
    else
        echo -e "${GREEN}[OK] Python $PYTHON_VERSION${NC}"
    fi
}

# 检查 Ollama
check_ollama() {
    echo ""
    echo "[检查] Ollama 安装状态..."
    
    if ! command -v ollama &> /dev/null; then
        echo -e "${RED}[错误] Ollama 未安装!${NC}"
        echo ""
        echo "Ollama 是本项目的核心依赖，请先安装。"
        echo "下载地址: https://ollama.com/download"
        echo ""
        if [[ "$OS" == "macOS" ]]; then
            echo "macOS 安装: brew install ollama"
        else
            echo "Linux 安装: curl -fsSL https://ollama.com/install.sh | sh"
        fi
        exit 1
    fi
    
    echo -e "${GREEN}[OK] Ollama 已安装${NC}"
}

# 创建虚拟环境
create_venv() {
    echo ""
    echo "[步骤 1/4] 创建 Python 虚拟环境..."
    
    if [ -d "venv" ]; then
        echo "[信息] 检测到已存在的虚拟环境"
        read -p "是否删除并重新创建? (y/n): " choice
        if [[ "$choice" == "y" || "$choice" == "Y" ]]; then
            rm -rf venv
            echo "[信息] 已删除旧虚拟环境"
        else
            echo "[信息] 保留现有虚拟环境"
            return
        fi
    fi
    
    $PYTHON_CMD -m venv venv
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}[错误] 虚拟环境创建失败${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}[OK] 虚拟环境创建成功${NC}"
}

# 安装依赖
install_dependencies() {
    echo ""
    echo "[步骤 2/4] 安装 Python 依赖包..."
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 升级 pip
    echo "[信息] 升级 pip..."
    pip install --upgrade pip -q
    
    # 检查 requirements.txt
    if [ ! -f "requirements.txt" ]; then
        echo -e "${RED}[错误] 找不到 requirements.txt!${NC}"
        exit 1
    fi
    
    # 安装依赖
    echo "[信息] 安装项目依赖..."
    pip install -r requirements.txt
    
    if [ $? -ne 0 ]; then
        echo -e "${YELLOW}[警告] 部分依赖安装可能失败，尝试逐个安装...${NC}"
        pip install flask flask-socketio flask-cors
        pip install Pillow requests psutil pyautogui
        pip install watchdog python-dotenv
    fi
    
    # Linux 额外依赖提示
    if [[ "$OS" == "Linux" ]]; then
        echo ""
        echo -e "${YELLOW}[提示] Linux 截图功能可能需要安装 scrot:${NC}"
        echo "       sudo apt install scrot  (Ubuntu/Debian)"
        echo "       sudo dnf install scrot  (Fedora)"
    fi
    
    echo -e "${GREEN}[OK] 依赖安装完成${NC}"
}

# 创建配置文件
create_config() {
    echo ""
    echo "[步骤 3/4] 创建配置文件..."
    
    if [ -f "config.json" ]; then
        echo "[信息] 配置文件已存在"
        read -p "是否覆盖? (y/n): " choice
        if [[ "$choice" != "y" && "$choice" != "Y" ]]; then
            echo "[信息] 保留现有配置"
            return
        fi
    fi
    
    cat > config.json << 'EOF'
{
  "webui": {
    "host": "127.0.0.1",
    "port": 7860,
    "debug": false
  },
  "ollama": {
    "base_url": "http://localhost:11434",
    "default_model": "qwen3:8b",
    "vision_model": "qwen3-vl:8b",
    "code_model": "qwen2.5-coder:7b"
  },
  "system": {
    "allow_system_control": true,
    "allowed_commands": ["ls", "pwd", "whoami", "date", "cal"],
    "screenshot_quality": 85,
    "max_file_size": 5242880
  }
}
EOF
    
    echo -e "${GREEN}[OK] 配置文件创建完成${NC}"
}

# 下载模型
download_models() {
    echo ""
    echo "[步骤 4/4] 设置 AI 模型..."
    echo ""
    echo "可选模型:"
    echo "  1. qwen3:8b        - 通义千问3 (推荐, 约5.5GB)"
    echo "  2. qwen3-vl:8b     - 视觉模型 (约5GB)"
    echo "  3. qwen2.5-coder:7b - 编程模型 (约4.7GB)"
    echo "  s. 跳过模型下载"
    echo ""
    read -p "请选择 (1/2/3/s): " model_choice
    
    case $model_choice in
        1)
            echo "[信息] 下载 qwen3:8b..."
            ollama pull qwen3:8b
            ;;
        2)
            echo "[信息] 下载 qwen3-vl:8b..."
            ollama pull qwen3-vl:8b
            ;;
        3)
            echo "[信息] 下载 qwen2.5-coder:7b..."
            ollama pull qwen2.5-coder:7b
            ;;
        *)
            echo "[信息] 跳过模型下载"
            echo "您可以稍后运行 ./install_models.sh 安装模型"
            ;;
    esac
}

# 验证安装
verify_installation() {
    echo ""
    echo "[验证] 检查安装结果..."
    
    source venv/bin/activate
    
    $PYTHON_CMD -c "import flask, requests, PIL, pyautogui" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[OK] 核心依赖验证通过${NC}"
    else
        echo -e "${YELLOW}[警告] 部分依赖可能未正确安装${NC}"
    fi
}

# 主流程
main() {
    detect_os
    check_python
    check_ollama
    create_venv
    install_dependencies
    create_config
    download_models
    verify_installation
    
    echo ""
    echo "========================================"
    echo "         部署完成!"
    echo "========================================"
    echo ""
    echo "使用说明:"
    echo "  1. 运行 ./start.sh 启动应用"
    echo "  2. 浏览器访问: http://127.0.0.1:7860"
    echo ""
    echo "其他工具:"
    echo "  - ./check_env.sh    : 检查环境"
    echo "  - ./install_models.sh : 管理模型"
    echo ""
    echo "========================================"
}

# 执行
main
