#!/bin/bash

# LocalAI-Desktop macOS/Linux 环境检查脚本
# 版本: v1.1

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "   LocalAI-Desktop 环境检查"
echo "========================================"
echo ""

# 计数器
PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0

# 检测操作系统
echo "[检查] 操作系统..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macOS"
    OS_VERSION=$(sw_vers -productVersion 2>/dev/null || echo "未知")
    echo -e "${GREEN}[OK] macOS $OS_VERSION${NC}"
    ((PASS_COUNT++))
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="Linux"
    if [ -f /etc/os-release ]; then
        OS_VERSION=$(grep PRETTY_NAME /etc/os-release | cut -d'"' -f2)
    else
        OS_VERSION="未知发行版"
    fi
    echo -e "${GREEN}[OK] $OS_VERSION${NC}"
    ((PASS_COUNT++))
else
    echo -e "${RED}[失败] 不支持的操作系统: $OSTYPE${NC}"
    ((FAIL_COUNT++))
fi

# 检查 Python
echo ""
echo "[检查] Python..."
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${RED}[失败] Python 未安装${NC}"
    ((FAIL_COUNT++))
    PYTHON_CMD=""
fi

if [ ! -z "$PYTHON_CMD" ]; then
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
    
    if [[ $PYTHON_MAJOR -lt 3 ]] || [[ $PYTHON_MAJOR -eq 3 && $PYTHON_MINOR -lt 10 ]]; then
        echo -e "${YELLOW}[警告] Python $PYTHON_VERSION (建议 3.10+)${NC}"
        ((WARN_COUNT++))
    else
        echo -e "${GREEN}[OK] Python $PYTHON_VERSION${NC}"
        ((PASS_COUNT++))
    fi
fi

# 检查虚拟环境
echo ""
echo "[检查] 虚拟环境..."
if [ -d "venv" ]; then
    echo -e "${GREEN}[OK] 虚拟环境存在${NC}"
    ((PASS_COUNT++))
else
    echo -e "${RED}[失败] 虚拟环境不存在${NC}"
    echo "       请运行 ./deploy.sh 创建"
    ((FAIL_COUNT++))
fi

# 检查 Ollama
echo ""
echo "[检查] Ollama..."
if command -v ollama &> /dev/null; then
    OLLAMA_VERSION=$(ollama --version 2>&1 | head -1 || echo "未知版本")
    echo -e "${GREEN}[OK] $OLLAMA_VERSION${NC}"
    ((PASS_COUNT++))
    
    # 检查 Ollama 服务
    echo ""
    echo "[检查] Ollama 服务..."
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo -e "${GREEN}[OK] Ollama 服务运行中${NC}"
        ((PASS_COUNT++))
        
        # 列出已安装模型
        echo ""
        echo "[检查] 已安装的模型..."
        MODELS=$(curl -s http://localhost:11434/api/tags 2>/dev/null | grep -o '"name":"[^"]*"' | cut -d'"' -f4)
        if [ -z "$MODELS" ]; then
            echo -e "${YELLOW}[警告] 没有安装任何模型${NC}"
            ((WARN_COUNT++))
        else
            MODEL_COUNT=$(echo "$MODELS" | wc -l | tr -d ' ')
            echo -e "${GREEN}[OK] 已安装 $MODEL_COUNT 个模型${NC}"
            echo "$MODELS" | while read model; do
                echo "       - $model"
            done
            ((PASS_COUNT++))
        fi
    else
        echo -e "${YELLOW}[警告] Ollama 服务未运行${NC}"
        ((WARN_COUNT++))
    fi
else
    echo -e "${RED}[失败] Ollama 未安装${NC}"
    echo "       下载地址: https://ollama.com/download"
    ((FAIL_COUNT++))
fi

# 检查 Python 依赖
echo ""
echo "[检查] Python 依赖..."
if [ -d "venv" ]; then
    source venv/bin/activate 2>/dev/null
    
    check_package() {
        if $PYTHON_CMD -c "import $1" 2>/dev/null; then
            echo -e "${GREEN}  [OK] $1${NC}"
            return 0
        else
            echo -e "${RED}  [缺失] $1${NC}"
            return 1
        fi
    }
    
    MISSING_DEPS=0
    check_package "flask" || ((MISSING_DEPS++))
    check_package "flask_socketio" || ((MISSING_DEPS++))
    check_package "PIL" || ((MISSING_DEPS++))
    check_package "requests" || ((MISSING_DEPS++))
    check_package "psutil" || ((MISSING_DEPS++))
    check_package "pyautogui" || ((MISSING_DEPS++))
    
    if [ $MISSING_DEPS -eq 0 ]; then
        ((PASS_COUNT++))
    else
        echo -e "${RED}[失败] 缺少 $MISSING_DEPS 个依赖${NC}"
        echo "       请运行: source venv/bin/activate && pip install -r requirements.txt"
        ((FAIL_COUNT++))
    fi
else
    echo -e "${YELLOW}[跳过] 虚拟环境不存在${NC}"
fi

# 检查项目文件
echo ""
echo "[检查] 项目文件..."
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}  [OK] $1${NC}"
        return 0
    else
        echo -e "${RED}  [缺失] $1${NC}"
        return 1
    fi
}

MISSING_FILES=0
check_file "webui.py" || ((MISSING_FILES++))
check_file "config.json" || ((MISSING_FILES++))
check_file "requirements.txt" || ((MISSING_FILES++))
check_file "core/__init__.py" || ((MISSING_FILES++))
check_file "core/chat_manager.py" || ((MISSING_FILES++))
check_file "templates/index.html" || ((MISSING_FILES++))
check_file "static/css/style.css" || ((MISSING_FILES++))
check_file "static/js/main.js" || ((MISSING_FILES++))

if [ $MISSING_FILES -eq 0 ]; then
    echo -e "${GREEN}[OK] 核心文件完整${NC}"
    ((PASS_COUNT++))
else
    echo -e "${RED}[失败] 缺少 $MISSING_FILES 个文件${NC}"
    ((FAIL_COUNT++))
fi

# Linux 额外检查
if [[ "$OS" == "Linux" ]]; then
    echo ""
    echo "[检查] Linux 截图依赖..."
    if command -v scrot &> /dev/null; then
        echo -e "${GREEN}[OK] scrot 已安装${NC}"
        ((PASS_COUNT++))
    else
        echo -e "${YELLOW}[警告] scrot 未安装 (截图功能可能不可用)${NC}"
        echo "       安装命令: sudo apt install scrot"
        ((WARN_COUNT++))
    fi
fi

# 汇总结果
echo ""
echo "========================================"
echo "           检查结果汇总"
echo "========================================"
echo ""
echo -e "${GREEN}通过: $PASS_COUNT${NC}"
echo -e "${YELLOW}警告: $WARN_COUNT${NC}"
echo -e "${RED}失败: $FAIL_COUNT${NC}"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    if [ $WARN_COUNT -eq 0 ]; then
        echo -e "${GREEN}环境检查完全通过!${NC}"
    else
        echo -e "${YELLOW}环境基本正常，但有一些警告需要注意${NC}"
    fi
    echo "可以运行 ./start.sh 启动应用"
else
    echo -e "${RED}存在 $FAIL_COUNT 个问题需要解决${NC}"
    echo "请根据上述提示修复后再试"
fi

echo ""
echo "========================================"
