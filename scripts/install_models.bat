@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM 获取脚本所在目录，然后切换到项目根目录
cd /d "%~dp0\.."

echo ========================================
echo    LocalAI-Desktop 模型管理工具
echo ========================================
echo.

REM 检查Ollama是否安装
where ollama >nul 2>&1
if errorlevel 1 (
    echo [错误] Ollama未安装！
    echo 请先安装Ollama: https://ollama.com/download/windows
    pause
    exit /b 1
)

:menu
cls
echo ========================================
echo    LocalAI-Desktop 模型管理工具
echo ========================================
echo.
echo 1. 查看已安装的模型
echo 2. 安装推荐模型（基础套装）
echo 3. 安装文字对话模型
echo 4. 安装图像理解模型
echo 5. 安装编程辅助模型
echo 6. 自定义安装模型
echo 7. 删除指定模型
echo 8. 更新模型
echo 9. 查看模型详细信息
echo 0. 返回/退出
echo.
echo ========================================
echo.

choice /C 1234567890 /M "请选择操作"
set choice=%errorlevel%

if %choice%==1 goto list_models
if %choice%==2 goto install_basic
if %choice%==3 goto install_chat
if %choice%==4 goto install_vision
if %choice%==5 goto install_code
if %choice%==6 goto install_custom
if %choice%==7 goto remove_model
if %choice%==8 goto update_model
if %choice%==9 goto model_info
if %choice%==10 goto end

:list_models
cls
echo ========================================
echo          已安装的模型列表
echo ========================================
echo.
ollama list
echo.
echo ========================================
pause
goto menu

:install_basic
cls
echo ========================================
echo        安装基础模型套装
echo ========================================
echo.
echo 包含以下模型：
echo 1. qwen3:8b          - 通义千问3对话模型（5.5GB）
echo 2. qwen3-vl:8b       - 通义千问3视觉模型（5GB）
echo 3. qwen2.5-coder:7b  - 通义千问编程模型（4.7GB）
echo.
echo 总大小约：15GB
echo.
choice /C YN /M "确认安装"
if errorlevel 2 goto menu

echo.
echo [1/3] 正在下载 qwen3:8b（通义千问3对话模型）...
ollama pull qwen3:8b
if errorlevel 1 (
    echo [错误] qwen3:8b 下载失败
) else (
    echo [✓] qwen3:8b 安装成功
)

echo.
echo [2/3] 正在下载 qwen3-vl:8b（通义千问3视觉模型）...
ollama pull qwen3-vl:8b
if errorlevel 1 (
    echo [错误] qwen3-vl:8b 下载失败
) else (
    echo [✓] qwen3-vl:8b 安装成功
)

echo.
echo [3/3] 正在下载 qwen2.5-coder:7b（通义千问编程模型）...
ollama pull qwen2.5-coder:7b
if errorlevel 1 (
    echo [错误] qwen2.5-coder:7b 下载失败
) else (
    echo [✓] qwen2.5-coder:7b 安装成功
)

echo.
echo ========================================
echo 基础模型套装安装完成！
echo ========================================
pause
goto menu

:install_chat
cls
echo ========================================
echo        文字对话模型选择
echo ========================================
echo.
echo 1. qwen3:4b     - 轻量快速（2.5GB，推荐）
echo 2. qwen3:8b     - 高质量对话（5.5GB，推荐）
echo 3. qwen3:14b    - 顶级性能（9GB）
echo 4. qwen2.5:7b   - 上代版本（4.7GB）
echo 5. llama3.2:3b  - 均衡性能（2GB）
echo 6. 返回主菜单
echo.
choice /C 123456 /M "请选择要安装的模型"
set model_choice=%errorlevel%

if %model_choice%==1 (
    set model_name=qwen3:4b
    set model_size=2.5GB
)
if %model_choice%==2 (
    set model_name=qwen3:8b
    set model_size=5.5GB
)
if %model_choice%==3 (
    set model_name=qwen3:14b
    set model_size=9GB
)
if %model_choice%==4 (
    set model_name=qwen2.5:7b
    set model_size=4.7GB
)
if %model_choice%==5 (
    set model_name=llama3.1:8b
    set model_size=4.7GB
)
if %model_choice%==6 goto menu

echo.
echo 正在下载 !model_name!（大小约 !model_size!）...
echo 这可能需要几分钟到几十分钟，请耐心等待...
echo.
ollama pull !model_name!
if errorlevel 1 (
    echo [错误] !model_name! 下载失败
) else (
    echo [✓] !model_name! 安装成功！
)
pause
goto menu

:install_vision
cls
echo ========================================
echo        图像理解模型选择
echo ========================================
echo.
echo 1. qwen3-vl:8b     - 通义千问3视觉（5GB，推荐）
echo 2. llava:7b        - 通用图像理解（4GB）
echo 3. llava:13b       - 高质量分析（8GB）
echo 4. 返回主菜单
echo.
choice /C 1234 /M "请选择要安装的模型"
set model_choice=%errorlevel%

if %model_choice%==1 set model_name=qwen3-vl:8b
if %model_choice%==2 set model_name=llava:7b
if %model_choice%==3 set model_name=llava:13b
if %model_choice%==4 goto menu

echo.
echo 正在下载 !model_name!...
ollama pull !model_name!
if errorlevel 1 (
    echo [错误] !model_name! 下载失败
) else (
    echo [✓] !model_name! 安装成功！
)
pause
goto menu

:install_code
cls
echo ========================================
echo        编程辅助模型选择
echo ========================================
echo.
echo 1. qwen2.5-coder:7b   - 通义千问编程（4.7GB，推荐）
echo 2. qwen2.5-coder:14b  - 高级编程（9GB）
echo 3. deepseek-coder:6.7b - DeepSeek编程（3.8GB）
echo 4. codellama:7b       - CodeLlama（4GB）
echo 5. 返回主菜单
echo.
choice /C 12345 /M "请选择要安装的模型"
set model_choice=%errorlevel%

if %model_choice%==1 set model_name=qwen2.5-coder:7b
if %model_choice%==2 set model_name=qwen2.5-coder:14b
if %model_choice%==3 set model_name=deepseek-coder:6.7b
if %model_choice%==4 set model_name=codellama:7b
if %model_choice%==5 goto menu

echo.
echo 正在下载 !model_name!...
ollama pull !model_name!
if errorlevel 1 (
    echo [错误] !model_name! 下载失败
) else (
    echo [✓] !model_name! 安装成功！
)
pause
goto menu

:install_custom
cls
echo ========================================
echo        自定义安装模型
echo ========================================
echo.
echo 说明：
echo - 支持任何 Ollama 官方模型库中的模型
echo - 模型名称格式：模型名:标签（例: qwen2.5:7b）
echo - 批量安装：用空格分隔多个模型（例: qwen2.5:7b qwen2-vl:7b）
echo - 访问 https://ollama.com/library 查看可用模型
echo.
echo 常用模型示例：
echo   qwen2.5:3b       - 通义千问 3B（2GB）
echo   qwen2.5:7b       - 通义千问 7B（4.7GB，推荐）
echo   qwen2.5:14b      - 通义千问 14B（9GB）
echo   qwen2-vl:7b      - 通义千问视觉（4.5GB）
echo   qwen2.5-coder:7b - 通义千问编程（4.7GB）
echo   llama3.2:3b      - Llama 3.2 3B（2GB）
echo   llama3.1:8b      - Llama 3.1 8B（4.7GB）
echo   llava:7b         - 图像理解（4GB）
echo   deepseek-coder:6.7b - DeepSeek编程（3.8GB）
echo   codellama:7b     - CodeLlama编程（4GB）
echo.
echo ========================================
echo.

REM 显示当前已安装的模型
echo 当前已安装的模型：
echo.
ollama list
echo.
echo ========================================
echo.
echo 提示：
echo - 单个模型：qwen2.5:7b
echo - 多个模型：qwen2.5:7b qwen2-vl:7b qwen2.5-coder:7b
echo - 输入 0 返回主菜单
echo.

set /p custom_model="请输入要安装的模型名称： "

REM 去除前后空格
for /f "tokens=*" %%a in ("!custom_model!") do set custom_model=%%a

if "!custom_model!"=="" (
    echo [错误] 模型名称不能为空
    pause
    goto install_custom
)

if "!custom_model!"=="0" goto menu

echo.
echo 将安装以下模型：!custom_model!
echo.
choice /C YN /M "确认安装"
if errorlevel 2 goto install_custom

echo.
echo [信息] 开始安装...
echo 请耐心等待，根据模型数量、大小和网速，可能需要较长时间...
echo ========================================
echo.

REM 分解多个模型名称
set model_count=0
set success_count=0
set fail_count=0

for %%m in (!custom_model!) do (
    set /a model_count+=1
    echo.
    echo [!model_count!] 正在安装: %%m
    echo ----------------------------------------
    
    ollama pull %%m
    
    if errorlevel 1 (
        echo [✗] %%m 安装失败
        set /a fail_count+=1
    ) else (
        echo [✓] %%m 安装成功
        set /a success_count+=1
    )
)

echo.
echo ========================================
echo           安装完成
echo ========================================
echo 总计: !model_count! 个模型
echo 成功: !success_count! 个
echo 失败: !fail_count! 个
echo ========================================
echo.

if !fail_count! gtr 0 (
    echo [警告] 有 !fail_count! 个模型安装失败！
    echo.
    echo 可能原因：
    echo 1. 模型名称错误或不存在
    echo 2. 网络连接问题
    echo 3. 磁盘空间不足
    echo.
    echo 请访问 https://ollama.com/library 查看正确的模型名称
    echo.
)

if !success_count! gtr 0 (
    echo 当前已安装的模型：
    echo.
    ollama list
    echo.
)

choice /C YN /M "是否继续安装其他模型"
if errorlevel 2 goto menu
goto install_custom

:remove_model
cls
echo ========================================
echo          删除模型
echo ========================================
echo.
echo 当前已安装的模型：
echo.
ollama list
echo.
echo ========================================
set /p model_name="请输入要删除的模型名称（如 qwen2.5:7b）: "

if "!model_name!"=="" (
    echo [错误] 模型名称不能为空
    pause
    goto menu
)

echo.
echo 警告：删除后无法恢复，需要重新下载！
choice /C YN /M "确认删除 !model_name!"
if errorlevel 2 goto menu

ollama rm !model_name!
if errorlevel 1 (
    echo [错误] 删除失败，可能模型不存在
) else (
    echo [✓] !model_name! 已成功删除
)
pause
goto menu

:update_model
cls
echo ========================================
echo          更新模型
echo ========================================
echo.
echo 当前已安装的模型：
echo.
ollama list
echo.
echo ========================================
set /p model_name="请输入要更新的模型名称（如 qwen2.5:7b）: "

if "!model_name!"=="" (
    echo [错误] 模型名称不能为空
    pause
    goto menu
)

echo.
echo 正在更新 !model_name!...
ollama pull !model_name!
if errorlevel 1 (
    echo [错误] 更新失败
) else (
    echo [✓] !model_name! 更新成功
)
pause
goto menu

:model_info
cls
echo ========================================
echo          模型详细信息
echo ========================================
echo.
echo 当前已安装的模型：
echo.
ollama list
echo.
echo ========================================
set /p model_name="请输入要查看的模型名称（如 qwen2.5:7b）: "

if "!model_name!"=="" (
    echo [错误] 模型名称不能为空
    pause
    goto menu
)

echo.
echo 模型信息：
ollama show !model_name!
echo.
pause
goto menu

:end
echo.
echo 感谢使用模型管理工具！
echo.
exit /b 0
