@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM 获取脚本所在目录，然后切换到项目根目录
cd /d "%~dp0\.."
set "PROJECT_DIR=%cd%"

echo ========================================
echo      LocalAI-Desktop 一键部署工具
echo ========================================
echo.
echo 版本：v1.2.0
echo 适用环境：Windows 10/11
echo Python版本：3.10
echo 项目目录：%PROJECT_DIR%
echo.
echo ========================================
echo.

REM 检查管理员权限
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo 请以管理员身份运行此脚本！
    echo 右键点击脚本 -> 以管理员身份运行
    pause
    exit /b 1
)

REM 设置颜色
color 0A
echo [1/8] 检查系统环境...
echo.

REM 检查Ollama是否安装
echo [检查] 验证Ollama安装状态...
where ollama >nul 2>&1
if errorlevel 1 (
    echo [错误] Ollama未安装！
    echo.
    echo Ollama是本项目的核心依赖，请先安装。
    echo 下载地址: https://ollama.com/download/windows
    echo.
    echo 安装步骤：
    echo 1. 访问上述网址
    echo 2. 下载Windows版本
    echo 3. 运行安装程序
    echo 4. 安装完成后重新运行此脚本
    echo.
    pause
    exit /b 1
)
echo [✓] Ollama已安装
echo.

REM 检查Python
echo [检查] 验证Python安装状态...
where python >nul 2>&1
if errorlevel 1 (
    echo [警告] Python未安装，正在下载并安装Python 3.10.11...
    echo.
    
    REM 检查是否存在离线安装包
    if exist "python-3.10.11-amd64.exe" (
        echo [信息] 检测到离线安装包，使用本地安装...
        set "installer=python-3.10.11-amd64.exe"
    ) else (
        echo [信息] 正在从官网下载Python安装程序...
        echo 下载地址: https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe
        echo 文件大小: 约27MB，请耐心等待...
        echo.
        
        powershell -Command "$ProgressPreference = 'SilentlyContinue'; try { Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe' -OutFile 'python-3.10.11-amd64.exe' -TimeoutSec 300; Write-Host '[✓] 下载完成' } catch { Write-Host '[错误] 下载失败: ' $_.Exception.Message; exit 1 }"
        
        if errorlevel 1 (
            echo.
            echo [错误] Python下载失败！
            echo 请检查网络连接，或手动下载安装：
            echo https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe
            echo.
            pause
            exit /b 1
        )
        set "installer=python-3.10.11-amd64.exe"
    )
    
    echo [信息] 正在安装Python 3.10.11...
    echo 安装选项：为所有用户安装、添加到PATH、不包含测试组件
    start /wait !installer! /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    
    if errorlevel 1 (
        echo [错误] Python安装失败！
        pause
        exit /b 1
    )
    
    echo [✓] Python安装完成
    
    REM 刷新环境变量
    echo [信息] 刷新环境变量...
    call refreshenv >nul 2>&1
    
    REM 验证安装
    where python >nul 2>&1
    if errorlevel 1 (
        echo [警告] Python未自动添加到PATH，请重启命令提示符后再试
        echo 或手动添加Python到系统PATH环境变量
        pause
        exit /b 1
    )
) else (
    echo [✓] Python已安装
    python --version
)
echo.

REM 创建虚拟环境
echo.
echo [2/8] 创建Python虚拟环境...

if exist "venv" (
    echo [信息] 检测到已存在的虚拟环境
    choice /C YN /M "是否删除并重新创建虚拟环境"
    if errorlevel 2 (
        echo [信息] 保留现有虚拟环境
    ) else (
        echo [信息] 删除旧虚拟环境...
        rmdir /s /q venv
        echo [信息] 创建新虚拟环境...
        python -m venv venv
        if errorlevel 1 (
            echo [错误] 虚拟环境创建失败
            pause
            exit /b 1
        )
    )
) else (
    echo [信息] 创建虚拟环境...
    python -m venv venv
    if errorlevel 1 (
        echo [错误] 虚拟环境创建失败
        echo 请确保Python已正确安装
        pause
        exit /b 1
    )
)
echo [✓] 虚拟环境创建成功
echo.

REM 激活虚拟环境并安装依赖
echo.
echo [3/8] 安装Python依赖包...
echo [信息] 激活虚拟环境...

REM 确保在项目目录
cd /d "%PROJECT_DIR%"

call venv\Scripts\activate.bat

if errorlevel 1 (
    echo [错误] 虚拟环境激活失败
    pause
    exit /b 1
)

echo [信息] 升级pip到最新版本...
python -m pip install --upgrade pip --quiet

echo [信息] 配置pip使用国内镜像源（加速下载）...
pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
pip config set install.trusted-host mirrors.aliyun.com
echo [✓] 已配置阿里云镜像源
echo.

echo [信息] 安装项目依赖包（这可能需要几分钟）...
echo [信息] 当前目录: %PROJECT_DIR%
echo.

REM 检查requirements.txt是否存在
if not exist "%PROJECT_DIR%\requirements.txt" (
    echo [错误] 找不到requirements.txt文件！
    echo 文件应该位于: %PROJECT_DIR%\requirements.txt
    echo.
    echo 当前目录下的txt文件：
    dir /b *.txt
    echo.
    pause
    exit /b 1
)

echo [✓] 找到requirements.txt文件
echo.

REM 使用requirements.txt安装
echo [信息] 从requirements.txt安装依赖...
echo [提示] 优先使用预编译包（wheel）避免编译错误
echo.
pip install -r "%PROJECT_DIR%\requirements.txt" --no-cache-dir --prefer-binary

if errorlevel 1 (
    echo [警告] 部分包安装失败，尝试逐个安装...
    echo.
    echo [1/11] 安装Flask框架...
    pip install flask==2.3.3 --prefer-binary
    echo [2/11] 安装Flask-SocketIO...
    pip install flask-socketio==5.3.4 --prefer-binary
    echo [3/11] 安装Flask-CORS...
    pip install flask-cors==4.0.0 --prefer-binary
    
    echo [4/11] 安装Pillow（图像处理库）...
    pip install Pillow==10.0.0 --prefer-binary --only-binary :all:
    if errorlevel 1 (
        echo [警告] Pillow 10.0.0安装失败，尝试其他版本...
        pip install Pillow --prefer-binary --only-binary :all:
    )
    
    echo [5/11] 安装Requests...
    pip install requests==2.31.0 --prefer-binary
    echo [6/11] 安装psutil（系统信息）...
    pip install psutil==5.9.5 --prefer-binary
    echo [7/9] 安装PyAutoGUI（系统控制）...
    pip install pyautogui==0.9.54 --prefer-binary
    echo [8/9] 安装watchdog...
    pip install watchdog==3.0.0 --prefer-binary
    echo [9/9] 安装python-dotenv...
    pip install python-dotenv==1.0.0 --prefer-binary
)

if errorlevel 1 (
    echo [警告] 部分依赖包安装可能失败
    echo 但核心功能应该可以正常使用
    echo.
    echo 如需完整功能，请手动安装失败的包
    echo.
    choice /C YN /M "是否继续部署"
    if errorlevel 2 exit /b 1
)
echo.
echo [✓] 依赖包安装完成

REM 创建必要目录
echo.
echo [4/8] 创建项目目录结构...
mkdir logs 2>nul
mkdir static 2>nul
mkdir static\css 2>nul
mkdir static\js 2>nul
mkdir static\images 2>nul
mkdir templates 2>nul
mkdir core 2>nul
mkdir models 2>nul
echo [✓] 目录结构创建完成

REM 下载和安装模型
echo.
echo [5/8] 设置本地模型...
echo [信息] 即将下载AI模型，这可能需要较长时间
echo.
echo 可选模型列表：
echo 1. qwen3:8b          (通义千问3，中文友好，约5.5GB，推荐)
echo 2. qwen3-vl:8b       (视觉模型，支持图像理解，约5GB)
echo 3. qwen2.5-coder:7b (编程模型，适合代码生成，约4.7GB)
echo.
choice /C 123S /M "请选择要下载的模型（可多选，按S跳过）"
set model_choice=%errorlevel%

if %model_choice%==4 (
    echo [信息] 跳过模型下载，您可以稍后运行 install_models.bat 安装
    goto skip_models
)

if %model_choice%==1 (
    echo [信息] 正在下载通义千问3对话模型（8B版本，约5.5GB）...
    ollama pull qwen3:8b
    if errorlevel 1 (
        echo [警告] 通义千问3模型下载失败，跳过...
    ) else (
        echo [✓] 通义千问3模型下载完成
    )
)

if %model_choice%==2 (
    echo [信息] 正在下载通义千问3视觉模型（8B版本，约5GB）...
    echo [提示] 模型名称: qwen3-vl:8b
    
    REM 先检查模型是否可用
    ollama list | findstr /C:"qwen3-vl:8b" >nul 2>&1
    if errorlevel 1 (
        REM 模型未安装，尝试下载
        ollama pull qwen3-vl:8b
        if errorlevel 1 (
            echo [警告] qwen3-vl:8b 下载失败
            echo [提示] 可能的原因：
            echo   1. 模型名称变更或未收录
            echo   2. 网络连接问题
            echo   3. Ollama 服务未启动
            echo.
            echo [信息] 您可以稍后手动安装：
            echo   ollama pull qwen3-vl:8b
            echo   或尝试其他视觉模型：
            echo   ollama pull llava:7b
            echo.
        ) else (
            echo [✓] 通义千问3视觉模型下载完成
        )
    ) else (
        echo [✓] 模型已存在，跳过下载
    )
)

if %model_choice%==3 (
    echo [信息] 正在下载通义千问编程模型（7B版本，约4.7GB）...
    ollama pull qwen2.5-coder:7b
    if errorlevel 1 (
        echo [警告] 编程模型下载失败，跳过...
    ) else (
        echo [✓] 通义千问编程模型下载完成
    )
)

:skip_models
echo [✓] 模型设置完成
echo.

REM 创建配置文件
echo.
echo [6/8] 创建配置文件...

if exist "config.json" (
    echo [信息] 配置文件已存在
    choice /C YN /M "是否覆盖现有配置文件"
    if errorlevel 2 (
        echo [信息] 保留现有配置文件
        goto skip_config
    )
)

echo [信息] 创建默认配置文件...
(
echo {
echo   "webui": {
echo     "host": "127.0.0.1",
echo     "port": 7860,
echo     "debug": false
echo   },
echo   "ollama": {
echo     "base_url": "http://localhost:11434",
echo     "default_model": "qwen3:8b",
echo     "vision_model": "qwen3-vl:8b",
echo     "code_model": "qwen2.5-coder:7b"
echo   },
echo   "system": {
echo     "allow_system_control": true,
echo     "allowed_commands": ["notepad", "calc", "cmd", "taskmgr"],
echo     "screenshot_quality": 85,
echo     "max_file_size": 5242880
echo   }
echo }
) > config.json

:skip_config
echo [✓] 配置文件创建完成
echo.

REM 创建启动脚本
echo.
echo [7/8] 验证项目文件...

if not exist "webui.py" (
    echo [错误] webui.py 不存在！
    echo 请确保所有项目文件完整
    pause
    exit /b 1
)

if not exist "core" (
    echo [错误] core 目录不存在！
    echo 请确保所有项目文件完整
    pause
    exit /b 1
)

if not exist "start.bat" (
    echo [警告] start.bat 不存在，项目可能不完整
)

echo [✓] 项目文件验证完成
echo.

REM 安装完成
echo.
echo [8/8] 部署完成测试...
echo [信息] 验证Python环境...
python --version
if errorlevel 1 (
    echo [警告] Python环境验证失败
)

echo [信息] 验证依赖包安装...
python -c "import flask, requests, PIL, pyautogui" 2>nul
if errorlevel 1 (
    echo [警告] 部分依赖包可能未正确安装
) else (
    echo [✓] 核心依赖包验证通过
)

echo.
echo ========================================
echo        部署完成！
echo ========================================
echo.
echo 项目已成功部署到当前目录。
echo.
echo 使用说明：
echo 1. 双击运行 start.bat 启动应用
echo 2. 浏览器访问: http://127.0.0.1:7860
echo 3. 首次启动可能需要等待Ollama服务启动
echo 4. 按Ctrl+C可停止服务
echo.
echo 其他工具：
echo - check_env.bat    : 检查系统环境
echo - install_models.bat : 管理AI模型
echo - update.bat       : 更新项目依赖
echo.
echo 遇到问题？
echo - 查看 logs 目录下的日志文件
echo - 确保Ollama服务正在运行
echo - 检查Python版本是否为3.10+
echo.
echo ========================================
echo.
pauseR E M   W i n d o w s    N.��r�,g
 
 