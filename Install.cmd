@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Portable Developer Environment

rem ---------------------------------------------------------------------------
rem Friendly launcher: use an existing Python when available.
rem ---------------------------------------------------------------------------
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 installer.py %*
    exit /b %errorlevel%
)

where python >nul 2>nul
if %errorlevel%==0 (
    python installer.py %*
    exit /b %errorlevel%
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
