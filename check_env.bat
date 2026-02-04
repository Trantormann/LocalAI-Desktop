@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM 获取脚本所在目录并切换到该目录
cd /d "%~dp0"

echo ========================================
echo    LocalAI-Desktop 环境检查工具
echo ========================================
echo.

set error_count=0
set warning_count=0

REM 检查操作系统
echo [检查 1/8] 操作系统版本...
ver | findstr /i "10\. 11\." >nul
if errorlevel 1 (
    echo [警告] 建议使用Windows 10或Windows 11
    set /a warning_count+=1
) else (
    echo [OK] 操作系统版本符合要求
)
echo.

REM 检查Python
echo [检查 2/8] Python安装状态...
where python >nul 2>&1
if errorlevel 1 (
    echo [错误] Python未安装
    echo 请运行 deploy.bat 进行自动安装
    set /a error_count+=1
) else (
    python --version
    python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>nul
    if errorlevel 1 (
        echo [警告] Python版本低于3.10，建议升级
        set /a warning_count+=1
    ) else (
        echo [OK] Python版本符合要求
    )
)
echo.

REM 检查虚拟环境
echo [检查 3/8] Python虚拟环境...
if not exist "venv\Scripts\activate.bat" (
    echo [错误] 虚拟环境不存在
    echo 请运行 deploy.bat 创建虚拟环境
    set /a error_count+=1
) else (
    echo [OK] 虚拟环境已创建
)
echo.

REM 检查Ollama
echo [检查 4/8] Ollama安装状态...
where ollama >nul 2>&1
if errorlevel 1 (
    echo [错误] Ollama未安装
    echo 下载地址: https://ollama.com/download/windows
    set /a error_count+=1
) else (
    echo [OK] Ollama已安装
    
    REM 检查Ollama服务
    tasklist | findstr /i "ollama" >nul
    if errorlevel 1 (
        echo [信息] Ollama服务未运行（启动应用时会自动启动）
    ) else (
        echo [OK] Ollama服务正在运行
    )
)
echo.

REM 检查网络连接
echo [检查 5/8] 网络连接状态...
ping -n 1 www.baidu.com >nul 2>&1
if errorlevel 1 (
    echo [警告] 网络连接异常，可能影响模型下载
    set /a warning_count+=1
) else (
    echo [OK] 网络连接正常
)
echo.

REM 检查依赖包
echo [检查 6/8] Python依赖包...
if not exist "venv\Scripts\activate.bat" (
    echo [跳过] 虚拟环境不存在，无法检查依赖包
) else (
    call venv\Scripts\activate.bat
    
    echo [信息] 检查核心依赖包...
    python -c "import flask" 2>nul
    if errorlevel 1 (
        echo [错误] Flask未安装
        set /a error_count+=1
    ) else (
        echo [OK] Flask已安装
    )
    
    python -c "import requests" 2>nul
    if errorlevel 1 (
        echo [错误] Requests未安装
        set /a error_count+=1
    ) else (
        echo [OK] Requests已安装
    )
    
    python -c "import PIL" 2>nul
    if errorlevel 1 (
        echo [错误] Pillow未安装
        set /a error_count+=1
    ) else (
        echo [OK] Pillow已安装
    )
    
    python -c "import pyautogui" 2>nul
    if errorlevel 1 (
        echo [警告] PyAutoGUI未安装（系统控制功能可选）
        set /a warning_count+=1
    ) else (
        echo [OK] PyAutoGUI已安装
    )
)
echo.

REM 检查配置文件
echo.
echo [检查 7/8] 配置文件...
if not exist "config.json" (
    echo [警告] config.json不存在
    echo 应用将使用默认配置
    set /a warning_count+=1
) else (
    echo [OK] 配置文件存在
)
echo.

REM 检查项目文件
echo.
echo [检查 8/8] 项目文件完整性...
set missing_files=0

if not exist "webui.py" (
    echo [错误] webui.py 缺失
    set /a missing_files+=1
)

if not exist "core\chat_manager.py" (
    echo [错误] core\chat_manager.py 缺失
    set /a missing_files+=1
)

if not exist "core\vision_processor.py" (
    echo [错误] core\vision_processor.py 缺失
    set /a missing_files+=1
)

if not exist "core\system_control.py" (
    echo [错误] core\system_control.py 缺失
    set /a missing_files+=1
)

if not exist "templates\index.html" (
    echo [错误] templates\index.html 缺失
    set /a missing_files+=1
)

if !missing_files! gtr 0 (
    echo [错误] 发现 !missing_files! 个核心文件缺失
    set /a error_count+=!missing_files!
) else (
    echo [OK] 项目文件完整
)
echo.

REM 输出检查结果
echo ========================================
echo          检查结果汇总
echo ========================================
echo.
if !error_count! equ 0 if !warning_count! equ 0 (
    echo [OK] 所有检查通过！环境配置正常
    echo.
    echo 您可以运行 start.bat 启动应用
) else (
    if !error_count! gtr 0 (
        echo [错误] 发现 !error_count! 个错误
        echo.
        echo 建议操作：
        echo 1. 运行 deploy.bat 自动修复环境
        echo 2. 手动安装缺失的组件
    )
    
    if !warning_count! gtr 0 (
        echo [警告] 发现 !warning_count! 个警告
        echo.
        echo 这些警告不影响基本功能，但建议处理
    )
)
echo.
echo ========================================
echo.
pause
