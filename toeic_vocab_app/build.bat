@echo off
chcp 65001
setlocal

echo ============================================
echo TOEIC 背单词 App 打包脚本
echo ============================================

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

REM 安装依赖
echo [1/4] 安装依赖...
pip install -r requirements.txt pyinstaller

REM 打包
echo [2/4] 开始打包...
pyinstaller --noconfirm --onefile --windowed ^
    --name "TOEIC背单词" ^
    --icon "NONE" ^
    --add-data "assets;assets" ^
    --hidden-import PySide6.QtCore ^
    --hidden-import PySide6.QtGui ^
    --hidden-import PySide6.QtWidgets ^
    --hidden-import matplotlib.backends.backend_qt5agg ^
    main.py

if errorlevel 1 (
    echo [错误] 打包失败
    pause
    exit /b 1
)

REM 复制词库到输出目录
echo [3/4] 复制资源文件...
if not exist "dist\assets" mkdir "dist\assets"
copy /Y "assets\vocabulary.json" "dist\assets\" >nul

REM 完成
echo [4/4] 打包完成！
echo 输出路径: %CD%\dist\TOEIC背单词.exe
echo.
pause
