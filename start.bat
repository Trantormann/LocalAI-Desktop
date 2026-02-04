@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM 获取脚本所在目录并切换到该目录
cd /d "%~dp0"

echo ========================================
echo      LocalAI-Desktop 启动工具
echo ========================================
echo.

REM 设置颜色
color 0B

echo [1/5] 检查虚拟环境...
if not exist "venv\Scripts\activate.bat" (
    echo [错误] Python虚拟环境不存在！
    echo 请先运行 deploy.bat 进行部署。
    echo.
    pause
    exit /b 1
)
echo [OK] 虚拟环境检查通过
echo.

echo [2/5] 检查Ollama服务...
timeout /t 1 >nul

REM 检查Ollama是否运行
tasklist | findstr /i "ollama" >nul
if errorlevel 1 (
    echo [信息] Ollama服务未运行，正在启动...
    
    REM 检查Ollama是否安装
    where ollama >nul 2>&1
    if errorlevel 1 (
        echo [错误] Ollama未安装！
        echo 请先安装Ollama: https://ollama.com/download/windows
        echo.
        pause
        exit /b 1
    )
    
    REM 启动Ollama服务
    start "" ollama serve
    echo 等待Ollama服务启动...
    timeout /t 8 >nul
    
    REM 再次检查
    tasklist | findstr /i "ollama" >nul
    if errorlevel 1 (
        echo [警告] Ollama服务可能未成功启动
        echo 如果遇到问题，请手动启动Ollama
    ) else (
        echo [OK] Ollama服务已启动
    )
) else (
    echo [OK] Ollama服务已在运行
)
echo.

REM 检查是否有可用模型
echo [信息] 检查已安装的模型...
ollama list >nul 2>&1
if errorlevel 1 (
    echo [警告] 无法获取模型列表
) else (
    for /f "tokens=*" %%a in ('ollama list 2^>nul ^| findstr /v "NAME"') do (
        set "has_model=1"
        goto :model_found
    )
    echo [警告] 未检测到已安装的模型！
    echo 请先运行: ollama pull qwen3:8b
    echo 或在 deploy.bat 中选择下载模型
    echo.
    choice /C YN /M "是否继续启动（没有模型将无法对话）"
    if errorlevel 2 exit /b 1
)
:model_found
echo [OK] 模型检查完成
echo.

echo [3/5] 激活Python虚拟环境...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [错误] 激活虚拟环境失败
    pause
    exit /b 1
)
echo [OK] Python环境已激活
echo.

echo [4/5] 检查配置文件...
if not exist "config.json" (
    echo [警告] 配置文件不存在，将使用默认配置
)
echo [OK] 配置检查完成
echo.

echo [5/5] 启动WebUI服务...
echo ========================================
echo.
echo 服务启动中，请稍候...
echo 浏览器将自动打开 http://127.0.0.1:7860
echo.
echo 提示：
echo - 按 Ctrl+C 可停止服务
echo - 关闭此窗口也会停止服务
echo.
echo ========================================
echo.

REM 等待2秒后自动打开浏览器
timeout /t 2 >nul
start http://127.0.0.1:7860

REM 启动WebUI
python webui.py

REM 如果程序意外退出
echo.
echo ========================================
echo 服务已停止
echo ========================================
pause
