@echo off
setlocal
chcp 65001 >nul

cd /d "%~dp0"

echo ==========================================
echo   Medical AI Assistant - Dev Launcher
echo ==========================================

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] 未找到 Python，请先安装 Python 3.10+ 并加入 PATH。
  pause
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] 未找到 npm，请先安装 Node.js 18+。
  pause
  exit /b 1
)

if not exist ".env" (
  if exist ".env.example" (
    copy /Y ".env.example" ".env" >nul
    echo [INFO] 已根据 .env.example 生成 .env，请检查并填写你的 API Key。
  ) else (
    echo [WARN] 未找到 .env.example，请手动创建 .env。
  )
)

if not exist ".venv\Scripts\python.exe" (
  echo [INFO] 正在创建 Python 虚拟环境 .venv ...
  python -m venv .venv
)

echo [INFO] 正在安装/更新后端依赖 ...
call ".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
call ".venv\Scripts\python.exe" -m pip install -r requirements.txt

if not exist "frontend-vue\node_modules" (
  echo [INFO] 正在安装前端依赖 ...
  pushd "frontend-vue"
  call npm install
  popd
)

echo [INFO] 启动后端： http://127.0.0.1:8000
start "Medical-AI Backend" cmd /k "cd /d %~dp0 && call .venv\Scripts\activate.bat && python app\api.py"

echo [INFO] 启动前端： http://127.0.0.1:3000
start "Medical-AI Frontend" cmd /k "cd /d %~dp0\frontend-vue && npm run dev"

echo.
echo [DONE] 已在两个窗口中启动服务。
echo        前端: http://127.0.0.1:3000
echo        后端: http://127.0.0.1:8000
echo.
pause

