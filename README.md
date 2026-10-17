# LocalAI-Desktop

基于 Ollama 的本地 AI 助手，支持对话、视觉理解和系统控制。

## 支持平台

| 平台 | 支持版本 |
|------|---------|
| Windows | 10 / 11 |
| macOS | 11.0+ (Big Sur 及以上) |
| Linux | Ubuntu 20.04+ / Debian 11+ / Fedora 35+ |

## 快速开始

### 前置要求

- Python 3.10+
- [Ollama](https://ollama.com/download)

### 安装部署

**Windows:**
```batch
cd LocalAI-Desktop\scripts
deploy.bat
```

**macOS / Linux:**
```bash
cd LocalAI-Desktop/scripts
chmod +x *.sh
./deploy.sh
```

### 启动应用

**Windows:**
```batch
scripts\start.bat
```

**macOS / Linux:**
```bash
./scripts/start.sh
```

浏览器会自动打开 http://127.0.0.1:7860

## 核心功能

### 智能对话
- 流式输出，逐字呈现
- 多轮对话上下文记忆，刷新页面自动恢复历史
- 自动过滤模型 `<think>` 推理内容，只展示最终回答
- 支持 Markdown 渲染（代码块、粗体、列表、链接等）
- 支持多种 Qwen3 系列模型

### 视觉理解
- 支持图片拖放、粘贴上传（聊天框直接 Ctrl+V 粘贴截图）
- 一键截图分析
- 基于 Qwen3-VL 视觉模型

### 系统控制 (Agent 模式)
自然语言控制电脑：
- "打开记事本" / "打开计算器"
- "截个图看看" / "查看系统状态"
- "看看屏幕上有什么" —— Agent 会截图并调用视觉模型真正"看懂"屏幕内容
- "打开资源管理器"

### 稳定性与安全
- 命令白名单机制，危险命令一律拒绝
- 设置持久化到 `config.json`，重启不丢失
- 日志按天轮转，自动保留 14 天
- 对话历史线程安全管理，防止并发损坏

## 项目结构

```
LocalAI-Desktop/
├── core/                    # Python 核心模块
│   ├── agent.py             # AI Agent 逻辑（Function Calling + 屏幕分析）
│   ├── chat_manager.py      # 对话管理
│   ├── vision_processor.py  # 视觉处理
│   ├── system_control.py    # 系统控制
│   └── utils.py             # 工具函数（ThinkFilter、日志轮转）
├── scripts/                 # 启动脚本
│   ├── deploy.bat/.sh       # 部署脚本
│   ├── start.bat/.sh        # 启动脚本
│   ├── check_env.bat/.sh    # 环境检查
│   └── install_models.bat/.sh # 模型管理
├── static/                  # 前端静态资源
│   ├── css/style.css
│   └── js/main.js
├── templates/               # HTML 模板
│   └── index.html
├── data/                    # 对话历史持久化（运行时生成）
├── logs/                    # 日志目录（按天轮转）
├── config.json              # 配置文件
├── requirements.txt         # Python 依赖
└── webui.py                 # 主程序入口
```

## 其他工具

| 脚本 | 说明 |
|------|------|
| `scripts/check_env.*` | 检查环境配置 |
| `scripts/install_models.*` | 管理 Ollama 模型 |

## 常见问题

**Q: 模型选择栏显示"加载中"？**
A: 确保 Ollama 服务已启动，按 Ctrl+Shift+R 刷新页面。

**Q: AI 执行操作没反应？**
A: 检查设置中是否开启了"允许系统控制"。

**Q: 如何更换模型？**
A: 运行 `scripts/install_models.bat` (Windows) 或 `./scripts/install_models.sh` (macOS/Linux)。

**Q: 设置保存后重启丢失？**
A: 设置现在通过"设置 → 保存"持久化到 `config.json`，重启后自动生效。

**Q: 刷新页面后对话还在吗？**
A: 在。对话历史持久化在 `data/` 目录，刷新自动恢复；点击"清空"按钮可彻底删除。

## 故障排除

- **日志**：查看 `logs/` 目录
- **环境检查**：运行 `scripts/check_env.*`

---

trantorman@foxmail.com
