@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo   XboxInput Unified - Compilador de Plugin (.XEX)
echo   Suporte: Xbox One/Series (GIP) + DualShock/DualSense/Switch/Ipega (HID)
echo ========================================================
echo.

set "MSBUILD_PATH="

:: Procura pelo MSBuild do VS2010 ou versões com suporte ao XDK
if exist "%ProgramFiles(x86)%\MSBuild\12.0\Bin\MSBuild.exe" set "MSBUILD_PATH=%ProgramFiles(x86)%\MSBuild\12.0\Bin\MSBuild.exe"
if exist "%ProgramFiles(x86)%\MSBuild\14.0\Bin\MSBuild.exe" set "MSBUILD_PATH=%ProgramFiles(x86)%\MSBuild\14.0\Bin\MSBuild.exe"
if exist "%ProgramFiles(x86)%\Microsoft Visual Studio\2019\Community\MSBuild\Current\Bin\MSBuild.exe" set "MSBUILD_PATH=%ProgramFiles(x86)%\Microsoft Visual Studio\2019\Community\MSBuild\Current\Bin\MSBuild.exe"
if exist "%ProgramFiles(x86)%\Microsoft Visual Studio\2017\Community\MSBuild\15.0\Bin\MSBuild.exe" set "MSBUILD_PATH=%ProgramFiles(x86)%\Microsoft Visual Studio\2017\Community\MSBuild\15.0\Bin\MSBuild.exe"
if exist "%WINDIR%\Microsoft.NET\Framework\v4.0.30319\MSBuild.exe" set "MSBUILD_PATH=%WINDIR%\Microsoft.NET\Framework\v4.0.30319\MSBuild.exe"

if "%MSBUILD_PATH%"=="" (
    where msbuild.exe >nul 2>&1
    if %errorlevel% equ 0 set "MSBUILD_PATH=msbuild.exe"
)

if "%MSBUILD_PATH%"=="" (
    echo [ERRO] Nao foi possivel localizar o MSBuild no seu sistema.
    echo.
    echo Para compilar este plugin para o Xbox 360 voce precisa ter instalado:
    echo  1. Visual Studio 2010 SP1
    echo  2. Microsoft Xbox 360 SDK (XDK)
    echo.
    pause
    exit /b 1
)

echo [INFO] Usando MSBuild: "%MSBUILD_PATH%"
echo [INFO] Iniciando compilacao do projeto XboxInput-Unified...
echo.

"%MSBUILD_PATH%" "source\XboxInput.vcxproj" /p:Configuration="Release Retail" /p:Platform="Xbox 360" /m /v:m

if %errorlevel% neq 0 (
    echo.
    echo [ERRO] Falha durante a compilacao. Verifique se o Xbox 360 SDK esta instalado corretamente.
    pause
    exit /b %errorlevel%
)

echo.
echo [SUCESSO] Compilacao concluida com sucesso!
echo.

set "TARGET_XEX=source\Release Retail\XboxInput.xex"
set "FINAL_XEX=XboxInput.xex"

if exist "%TARGET_XEX%" (
    echo [INFO] Convertendo para Retail com XexTool...
    where XexTool.exe >nul 2>&1
    if %errorlevel% equ 0 (
        XexTool.exe -r a -m r "%TARGET_XEX%"
        copy /y "%TARGET_XEX%" "%FINAL_XEX%" >nul
        echo [OK] Arquivo final gerado: %FINAL_XEX% pronto para o Xbox 360!
    ) else (
        if exist "XexTool.exe" (
            XexTool.exe -r a -m r "%TARGET_XEX%"
            copy /y "%TARGET_XEX%" "%FINAL_XEX%" >nul
            echo [OK] Arquivo final gerado: %FINAL_XEX% pronto para o Xbox 360!
        ) else (
            copy /y "%TARGET_XEX%" "%FINAL_XEX%" >nul
            echo [AVISO] XexTool.exe nao encontrado no PATH. Copiado direto para: %FINAL_XEX%
            echo         Recomenda-se rodar: XexTool.exe -r a -m r %FINAL_XEX% antes de usar no console.
        )
    )
) else (
    echo [AVISO] Arquivo gerado nao encontrado em %TARGET_XEX%.
)

echo.
echo Concluido!
pause
