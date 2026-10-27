@echo off
setlocal
cd /d "%~dp0"
echo ===========================================
echo  Discord VPN Helper Pro - Criar EXE
echo ===========================================
where py >nul 2>nul
if errorlevel 1 (
  echo Python nao foi encontrado. Instale Python 3 para Windows e marque "Add Python to PATH".
  pause
  exit /b 1
)
py -m pip install --upgrade pip
if errorlevel 1 goto error
py -m pip install --upgrade pyinstaller
if errorlevel 1 goto error
py -m PyInstaller --noconfirm --clean --onefile --windowed --name DiscordVPNHelperPro app.py
if errorlevel 1 goto error
echo.
echo SUCESSO: dist\DiscordVPNHelperPro.exe
pause
exit /b 0
:error
echo.
echo Ocorreu um erro. Confira se o Python esta instalado e se a internet funciona.
pause
exit /b 1
