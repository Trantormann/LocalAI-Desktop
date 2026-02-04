#!/bin/bash

# LocalAI-Desktop macOS/Linux 模型安装脚本
# 版本: v1.1

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "   LocalAI-Desktop 模型管理工具"
echo "========================================"
echo ""

# 检查 Ollama
check_ollama() {
    if ! command -v ollama &> /dev/null; then
        echo -e "${RED}[错误] Ollama 未安装!${NC}"
        echo "下载地址: https://ollama.com/download"
        exit 1
    fi
    
    # 检查服务
    if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo -e "${YELLOW}[信息] 启动 Ollama 服务...${NC}"
        if [[ "$OSTYPE" == "darwin"* ]]; then
            open -a Ollama 2>/dev/null || ollama serve &
        else
            ollama serve > /dev/null 2>&1 &
        fi
        sleep 3
    fi
}

# 显示已安装的模型
show_installed_models() {
    echo "[已安装的模型]"
    echo ""
    
    MODELS=$(curl -s http://localhost:11434/api/tags 2>/dev/null)
    
    if [ -z "$MODELS" ] || [ "$MODELS" == '{"models":[]}' ]; then
        echo -e "${YELLOW}  (暂无已安装的模型)${NC}"
    else
        echo "$MODELS" | grep -o '"name":"[^"]*"' | cut -d'"' -f4 | while read model; do
            SIZE=$(echo "$MODELS" | grep -A5 "\"name\":\"$model\"" | grep -o '"size":[0-9]*' | head -1 | cut -d':' -f2)
            if [ ! -z "$SIZE" ]; then
                SIZE_GB=$(echo "scale=2; $SIZE / 1073741824" | bc 2>/dev/null || echo "?")
                echo -e "  ${GREEN}* $model${NC} (${SIZE_GB}GB)"
            else
                echo -e "  ${GREEN}* $model${NC}"
            fi
        done
    fi
    echo ""
}

# 推荐模型列表
show_recommended_models() {
    echo "[推荐模型]"
    echo ""
    echo -e "${CYAN}--- 通用对话模型 ---${NC}"
    echo "  1. qwen3:8b          - 通义千问3 8B (推荐, ~5.5GB)"
    echo "  2. qwen3:4b          - 通义千问3 4B (轻量, ~2.5GB)"
    echo "  3. llama3.1:8b       - Meta Llama 3.1 8B (~4.7GB)"
    echo "  4. gemma2:9b         - Google Gemma 2 9B (~5.5GB)"
    echo ""
    echo -e "${CYAN}--- 视觉模型 ---${NC}"
    echo "  5. qwen3-vl:8b       - 通义千问3 视觉 (推荐, ~5GB)"
    echo "  6. llava:7b          - LLaVA 7B (~4.5GB)"
    echo "  7. minicpm-v:8b      - MiniCPM-V 8B (~5GB)"
    echo ""
    echo -e "${CYAN}--- 编程模型 ---${NC}"
    echo "  8. qwen2.5-coder:7b  - 通义千问 编程 (推荐, ~4.7GB)"
    echo "  9. codellama:7b      - Code Llama 7B (~3.8GB)"
    echo "  10. deepseek-coder:6.7b - DeepSeek Coder (~3.8GB)"
    echo ""
    echo -e "${CYAN}--- 轻量模型 (适合低配机器) ---${NC}"
    echo "  11. phi3:mini        - Microsoft Phi-3 Mini (~2.3GB)"
    echo "  12. gemma:2b         - Google Gemma 2B (~1.4GB)"
    echo ""
}

# 安装模型
install_model() {
    local model_name="$1"
    
    echo ""
    echo -e "${BLUE}[下载] $model_name${NC}"
    echo "这可能需要几分钟，取决于网络速度..."
    echo ""
    
    ollama pull "$model_name"
    
    if [ $? -eq 0 ]; then
        echo ""
        echo -e "${GREEN}[完成] $model_name 安装成功!${NC}"
    else
        echo ""
        echo -e "${RED}[错误] $model_name 安装失败${NC}"
    fi
}

# 删除模型
delete_model() {
    echo ""
    echo "[删除模型]"
    echo ""
    
    MODELS=$(curl -s http://localhost:11434/api/tags 2>/dev/null | grep -o '"name":"[^"]*"' | cut -d'"' -f4)
    
    if [ -z "$MODELS" ]; then
        echo -e "${YELLOW}没有可删除的模型${NC}"
        return
    fi
    
    echo "已安装的模型:"
    i=1
    declare -a MODEL_ARRAY
    while read model; do
        echo "  $i. $model"
        MODEL_ARRAY[$i]="$model"
        ((i++))
    done <<< "$MODELS"
    
    echo ""
    read -p "请输入要删除的模型编号 (0 取消): " choice
    
    if [ "$choice" == "0" ] || [ -z "$choice" ]; then
        echo "[取消] 未删除任何模型"
        return
    fi
    
    if [ ! -z "${MODEL_ARRAY[$choice]}" ]; then
        echo ""
        read -p "确认删除 ${MODEL_ARRAY[$choice]}? (y/n): " confirm
        if [[ "$confirm" == "y" || "$confirm" == "Y" ]]; then
            ollama rm "${MODEL_ARRAY[$choice]}"
            echo -e "${GREEN}[完成] 模型已删除${NC}"
        else
            echo "[取消] 未删除模型"
        fi
    else
        echo -e "${RED}[错误] 无效的选项${NC}"
    fi
}

# 自定义安装
custom_install() {
    echo ""
    read -p "请输入模型名称 (如 llama3:8b): " model_name
    
    if [ ! -z "$model_name" ]; then
        install_model "$model_name"
    else
        echo -e "${YELLOW}[取消] 未输入模型名称${NC}"
    fi
}

# 主菜单
main_menu() {
    while true; do
        echo ""
        echo "========================================"
        echo "          操作选项"
        echo "========================================"
        echo ""
        echo "  1-12. 安装推荐模型"
        echo "  i.    自定义安装模型"
        echo "  d.    删除已安装模型"
        echo "  r.    刷新模型列表"
        echo "  q.    退出"
        echo ""
        read -p "请选择操作: " choice
        
        case $choice in
            1)  install_model "qwen3:8b" ;;
            2)  install_model "qwen3:4b" ;;
            3)  install_model "llama3.1:8b" ;;
            4)  install_model "gemma2:9b" ;;
            5)  install_model "qwen3-vl:8b" ;;
            6)  install_model "llava:7b" ;;
            7)  install_model "minicpm-v:8b" ;;
            8)  install_model "qwen2.5-coder:7b" ;;
            9)  install_model "codellama:7b" ;;
            10) install_model "deepseek-coder:6.7b" ;;
            11) install_model "phi3:mini" ;;
            12) install_model "gemma:2b" ;;
            i|I) custom_install ;;
            d|D) delete_model ;;
            r|R) 
                echo ""
                show_installed_models
                show_recommended_models
                ;;
            q|Q) 
                echo ""
                echo "再见!"
                exit 0 
                ;;
            *)
                echo -e "${YELLOW}无效选项，请重新选择${NC}"
                ;;
        esac
    done
}

# 主流程
main() {
    check_ollama
    show_installed_models
    show_recommended_models
    main_menu
}

# 执行
main
