@echo off
REM Sem 'enabledelayedexpansion' de proposito: com ela, um '!' no caminho da
REM pasta (ex: C:\pasta!\) seria removido de %~dp0. Nao usamos !var! aqui.
setlocal
chcp 65001 >nul
title Truckstar - Instalador e Executor

set "HERE=%~dp0"
set "PS1=%HERE%setup.ps1"
set "RAW=https://raw.githubusercontent.com/devjungleskaue/truckstar_projetointegrador_senac/main/setup.ps1"

REM Se o setup.ps1 nao estiver ao lado do .bat (ex: usuario baixou so o .bat),
REM baixa o instalador do GitHub para a pasta temporaria.
if not exist "%PS1%" (
    echo setup.ps1 nao encontrado ao lado do .bat. Baixando do GitHub...
    set "PS1=%TEMP%\truckstar_setup.ps1"
    powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -UseBasicParsing -Uri '%RAW%' -OutFile '%TEMP%\truckstar_setup.ps1'; exit 0 } catch { Write-Host ('Falha ao baixar: ' + $_.Exception.Message) -ForegroundColor Red; exit 1 }"
    if errorlevel 1 (
        echo.
        echo Nao foi possivel baixar o setup.ps1 do GitHub.
        echo Causas possiveis:
        echo   - sem conexao com a internet;
        echo   - o arquivo ainda nao foi publicado no repositorio ^(push pendente^);
        echo   - URL do repositorio incorreta.
        echo Alternativa: copie o setup.ps1 para a MESMA pasta deste .bat.
        echo.
        pause
        exit /b 1
    )
)

REM Repassa quaisquer parametros extras (ex: -Reset, -Reconfigure) para o PowerShell.
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%" %*
set "RC=%ERRORLEVEL%"

echo.
if not "%RC%"=="0" (
    echo O instalador terminou com erro [codigo %RC%].
) else (
    echo Concluido.
)
echo.
pause
endlocal
