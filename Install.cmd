@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
title Portable Developer Environment

rem ---------------------------------------------------------------------------
rem Verify that this is a complete checkout before starting Python.
rem ---------------------------------------------------------------------------
call :ensure_layout
if errorlevel 1 exit /b 1

rem ---------------------------------------------------------------------------
rem Friendly launcher: use an existing Python when available.
rem ---------------------------------------------------------------------------
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 installer.py %*
    exit /b !errorlevel!
)

where python >nul 2>nul
if %errorlevel%==0 (
    python installer.py %*
    exit /b !errorlevel!
)

rem ---------------------------------------------------------------------------
rem No Python installed: bootstrap uv locally, then let uv provide Python.
rem Nothing is installed system-wide and Administrator rights are not required.
rem ---------------------------------------------------------------------------
echo.
echo Python was not found. Preparing a temporary local runtime...
echo This only uses the .bootstrap folder inside this project.
echo.

set "BOOTSTRAP=%CD%\.bootstrap\uv"
set "UV_EXE=%BOOTSTRAP%\uv.exe"

if not exist "%UV_EXE%" (
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
      "$ErrorActionPreference='Stop';" ^
      "$root='%BOOTSTRAP%';" ^
      "New-Item -ItemType Directory -Force -Path $root ^| Out-Null;" ^
      "$release=Invoke-RestMethod -Headers @{'User-Agent'='portable-installer'} -Uri 'https://api.github.com/repos/astral-sh/uv/releases/latest';" ^
      "$asset=$release.assets ^| Where-Object { $_.name -eq 'uv-x86_64-pc-windows-msvc.zip' } ^| Select-Object -First 1;" ^
      "if (-not $asset) { throw 'Unable to find the Windows x64 uv release.' };" ^
      "$zip=Join-Path $env:TEMP 'portable-uv.zip';" ^
      "Invoke-WebRequest -UseBasicParsing -Uri $asset.browser_download_url -OutFile $zip;" ^
      "Expand-Archive -Force -Path $zip -DestinationPath $root;" ^
      "Remove-Item -Force $zip;"

    if errorlevel 1 (
        echo.
        echo Failed to prepare the local runtime.
        echo Check your Internet connection and try again.
        pause
        exit /b 1
    )
)

"%UV_EXE%" run --no-project --python 3.13 python installer.py %*
set "RC=%errorlevel%"
exit /b %RC%


:ensure_layout
if exist "portable_installer\app.py" exit /b 0

echo.
echo ================================================================
echo   Portable Developer Environment - incomplete installation files
echo ================================================================
echo.
echo The required folder "portable_installer" is missing.
echo The launcher and installer.py must be kept together with the full
necho repository contents. Copying only Install.cmd and installer.py is
necho not enough.
echo.

rem If this is a Git checkout and HEAD tracks the package, restore only the
rem missing package. This is safe because this path is currently absent.
where git >nul 2>nul
if not errorlevel 1 if exist ".git" (
    git ls-tree -r --name-only HEAD portable_installer 2>nul | findstr /b /c:"portable_installer/" >nul
    if not errorlevel 1 (
        echo Attempting to restore the missing package from the current Git commit...
        git restore --source=HEAD --worktree -- portable_installer >nul 2>nul
        if exist "portable_installer\app.py" (
            echo Restore completed successfully.
            echo.
            exit /b 0
        )
    )
)

echo Please download or clone the complete repository.
echo.
echo If you are testing PR #1, update the checkout with:
echo.
echo   git fetch origin
echo   git switch feat/modular-installer-v4
echo   git pull origin feat/modular-installer-v4
echo.
echo Required file:
echo   portable_installer\app.py
echo.
pause
exit /b 1
