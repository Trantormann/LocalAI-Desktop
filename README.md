使用说明

2026.02
Windows / macOS / Linux
基本全是AI coding（（

目录

1. 快速开始
2. 核心功能
3. AI Agent 对话流控制
4. 常见问题解答
5. 故障排除指南

## 1. 快速开始

### 1.1 系统要求

| 平台 | 支持版本 |
|------|---------|
| Windows | 10 / 11 |
| macOS | 11.0+ (Big Sur 及以上) |
| Linux | Ubuntu 20.04+ / Debian 11+ / Fedora 35+ |

**依赖软件：**
- Python 3.10+
- Ollama ([下载地址](https://ollama.com/download))

### 1.2 一键部署

**Windows:**
```
1. 解压 LocalAI-Desktop 压缩包到任意目录
2. 双击运行 deploy.bat
3. 按照提示选择模型
4. 部署成功后，双击运行 start.bat
```

**macOS / Linux:**
```bash
# 1. 解压并进入项目目录
cd LocalAI-Desktop

# 2. 添加执行权限
chmod +x *.sh

# 3. 运行部署脚本
./deploy.sh

# 4. 启动应用
./start.sh
```

**Linux 额外依赖 (截图功能):**
```bash
# Ubuntu/Debian
sudo apt install scrot

# Fedora
sudo dnf install scrot
```

### 1.3 首次使用

1. 启动应用后，侧边栏模型选择器会自动加载已安装模型。
2. 默认推荐模型：
   - 对话：qwen3:8b
   - 视觉：qwen3-vl:8b
   - 编程：qwen2.5-coder:7b
_不建议更改_

## 2. 核心功能

**2.1 对话**
- **逐字输出**：如同原生 ChatGPT 般的线性流式交互。
- **Agent 驱动**：支持自然语言理解，自动识别意图。
- **上下文记忆**：支持多轮对话逻辑。

**2.2 视觉 **
- **精准识别**：基于通义千问3视觉大模型。
- **多模态交互**：支持拖放、粘贴、文件选择上传图片。
- **截图分析**：一键截图并自动发给 AI 进行分析。

## 3. AI Agent 对话流控制

**3.1 什么是对话流控制？**
对话框输入自然语言：
- "帮我打开记事本" -> AI 自动执行
- "截个图看看屏幕内容" -> AI 自动截图并分析
- "查看系统当前状态" -> AI 获取 CPU/内存信息并汇报
- "帮我打开资源管理器" -> AI 自动启动

**3.2 支持的操作白名单**
- **应用程序**：记事本、计算器、画图、资源管理器、任务管理器、控制面板等。
- **系统工具**：截图、获取 CPU/内存/磁盘状态、执行安全白名单命令。

**3.3 如何启用？**
1. 进入 "设置" 标签页。
2. 开启 "允许系统控制" 和 "启用 AI Agent 模式"。
3. 点击 "保存设置"。

## 4. 常见问题解答

Q1: 为什么模型选择栏显示"加载中"？
A1: 请确保 Ollama 服务已启动。如果已启动，请尝试按 Ctrl+Shift+R 强制刷新页面。

Q2: 模型输出 arguments 1 错误？
A2: 已在 v1.1 版本中修复。如果仍出现，请确保路径不包含非法特殊字符。

Q3: AI 说已执行操作但没反应？
A3: 请检查设置中是否开启了"允许系统控制"。部分 GUI 程序在某些环境下可能需要几秒钟启动。

Q4: 如何更换模型？
A4: 
- Windows: 运行 install_models.bat
- macOS/Linux: 运行 ./install_models.sh

## 5. 故障排除

- **日志查看**：所有操作记录在 logs/ 目录下，搜索 "[Agent]" 可查看指令执行详情。
- **环境检查**：
  - Windows: 运行 check_env.bat
  - macOS/Linux: 运行 ./check_env.sh
- **系统测试**：运行 test_system.py

## 6. 项目结构

```
LocalAI-Desktop/
├── core/                # Python 核心模块
├── static/              # 前端静态资源
├── templates/           # HTML 模板
├── logs/                # 日志目录
├── deploy.bat/.sh       # 部署脚本
├── start.bat/.sh        # 启动脚本
├── check_env.bat/.sh    # 环境检查
├── install_models.bat/.sh # 模型管理
├── config.json          # 配置文件
└── webui.py             # 主程序入口
```

trantorman@foxmail.com
