#!/bin/bash

# LocalAI-Desktop macOS/Linux 启动脚本
# 版本: v1.2.0

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 获取脚本所在目录，然后切换到项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "========================================"
echo "   LocalAI-Desktop 启动程序"
echo "========================================"
echo ""

# 检测操作系统
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macOS"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="Linux"
else
    echo -e "${RED}[错误] 不支持的操作系统${NC}"
    exit 1
fi

# 检查虚拟环境
check_venv() {
    echo "[检查] 虚拟环境..."
    
    if [ ! -d "venv" ]; then
        echo -e "${RED}[错误] 未找到虚拟环境!${NC}"
        echo ""
        echo "请先运行 ./deploy.sh 部署项目"
        exit 1
    fi
    
    echo -e "${GREEN}[OK] 虚拟环境存在${NC}"
}

# 检查 Ollama 服务
check_ollama() {
    echo "[检查] Ollama 服务..."
    
    if ! command -v ollama &> /dev/null; then
        echo -e "${RED}[错误] Ollama 未安装!${NC}"
        exit 1
    fi
    
    # 检查服务是否运行
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo -e "${GREEN}[OK] Ollama 服务运行中${NC}"
    else
        echo -e "${YELLOW}[信息] Ollama 服务未运行，正在启动...${NC}"
        
        if [[ "$OS" == "macOS" ]]; then
            # macOS: 尝试启动 Ollama 应用
            open -a Ollama 2>/dev/null || ollama serve &
        else
            # Linux: 后台启动服务
            ollama serve > /dev/null 2>&1 &
        fi
        
        # 等待服务启动
        echo "[信息] 等待 Ollama 服务启动..."
        for i in {1..10}; do
            sleep 1
            if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
                echo -e "${GREEN}[OK] Ollama 服务已启动${NC}"
                break
            fi
            if [ $i -eq 10 ]; then
                echo -e "${RED}[错误] Ollama 服务启动超时${NC}"
                exit 1
            fi
        done
    fi
}

# 检查已安装的模型
check_models() {
    echo "[检查] 已安装的模型..."
    
    MODELS=$(curl -s http://localhost:11434/api/tags 2>/dev/null | grep -o '"name":"[^"]*"' | cut -d'"' -f4)
    
    if [ -z "$MODELS" ]; then
        echo -e "${YELLOW}[警告] 没有检测到已安装的模型${NC}"
        echo ""
        echo "请运行 ./install_models.sh 安装模型"
        echo ""
        read -p "是否继续启动? (y/n): " choice
        if [[ "$choice" != "y" && "$choice" != "Y" ]]; then
            exit 1
        fi
    else
        echo -e "${GREEN}[OK] 已安装的模型:${NC}"
        echo "$MODELS" | while read model; do
            echo "    - $model"
        done
    fi
}

# 打开浏览器
open_browser() {
    local url="$1"
    
    sleep 2  # 等待服务器启动
    
    echo ""
    echo "[信息] 正在打开浏览器..."
    
    if [[ "$OS" == "macOS" ]]; then
        open "$url"
    else
        # Linux: 尝试多种方式打开浏览器
        if command -v xdg-open &> /dev/null; then
            xdg-open "$url"
        elif command -v gnome-open &> /dev/null; then
            gnome-open "$url"
        elif command -v firefox &> /dev/null; then
            firefox "$url" &
        elif command -v google-chrome &> /dev/null; then
            google-chrome "$url" &
        else
            echo -e "${YELLOW}[提示] 无法自动打开浏览器，请手动访问: $url${NC}"
        fi
    fi
}

# 启动 WebUI
start_webui() {
    echo ""
    echo "[启动] WebUI 服务..."
    echo ""
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 读取端口配置
    PORT=7860
    if [ -f "config.json" ]; then
        CONFIG_PORT=$(grep -o '"port": *[0-9]*' config.json | grep -o '[0-9]*')
        if [ ! -z "$CONFIG_PORT" ]; then
            PORT=$CONFIG_PORT
        fi
    fi
    
    URL="http://127.0.0.1:$PORT"
    
    echo "========================================"
    echo "  WebUI 地址: $URL"
    echo "  按 Ctrl+C 停止服务"
    echo "========================================"
    echo ""
    
    # 后台打开浏览器
    open_browser "$URL" &
    
    # 启动 Python 应用
    python webui.py
}

# 主流程
main() {
    check_venv
    check_ollama
    check_models
    start_webui
}

# 执行
main
