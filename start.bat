@echo off
setlocal
title LoL Dodge Tool
cd /d "%~dp0"
chcp 65001 >nul
set PYTHONIOENCODING=utf-8

rem Falls League nicht im Standardordner installiert ist, hier den Pfad eintragen
rem (die Anfuehrungszeichen und das "rem" am Anfang entfernen):
rem set "LOL_PATH=D:\Spiele\Riot Games\League of Legends"

rem Python suchen: zuerst den "py"-Launcher, sonst "python"
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY (
    echo Python wurde nicht gefunden.
    echo Bitte von https://www.python.org/downloads/ installieren
    echo und dabei "Add python.exe to PATH" anhaken.
    pause
    exit /b 1
)

:menu
cls
echo ==========================================
echo              LoL Dodge Tool
echo ==========================================
echo.
echo   [1] Infos zu meinen Mitspielern
echo   [2] Sofort dodgen
echo   [3] Last-Second-Dodge (kurz vor Spielstart)
echo   [4] Watch-Modus (Enter = dodge)
echo   [5] Status anzeigen
echo   [0] Beenden
echo.
set "choice="
set /p "choice=Auswahl: "

if "%choice%"=="1" set "ARGS=--team"        & goto run
if "%choice%"=="2" set "ARGS="              & goto run
if "%choice%"=="3" set "ARGS=--last-second --quit-fallback" & goto run
if "%choice%"=="4" set "ARGS=--watch"       & goto run
if "%choice%"=="5" set "ARGS=--status"      & goto run
if "%choice%"=="0" exit /b 0
goto menu

:run
echo.
%PY% dodge.py %ARGS%
echo.
pause
goto menu
