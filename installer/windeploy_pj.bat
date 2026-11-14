@echo off
REM Deploy Qt dependencies for PlotJuggler and all its plugins
REM This script runs windeployqt on the main executable and all plugin DLLs
REM
REM Usage: windeploy_pj.bat [path_to_windeployqt.exe]
REM   If windeployqt.exe is not in PATH, provide the full path as argument
REM   Example: windeploy_pj.bat C:\Qt\5.15.2\msvc2019_64\bin\windeployqt.exe

setlocal enabledelayedexpansion

set DATA_DIR=%~dp0io.plotjuggler.application\data

REM Use provided windeployqt path or default to PATH
if "%~1"=="" (
    set WINDEPLOYQT=windeployqt.exe
) else (
    set WINDEPLOYQT=%~1
)

echo Deploying Qt dependencies for PlotJuggler...
echo Using: %WINDEPLOYQT%

REM Deploy for main executable
echo Processing: plotjuggler.exe
"%WINDEPLOYQT%" --release "%DATA_DIR%\plotjuggler.exe"
if errorlevel 1 exit /b 1
"%WINDEPLOYQT%" --release "%DATA_DIR%\plotjuggler-launcher.exe"
if errorlevel 1 exit /b 1

REM Deploy the Qt5 plugin target families in this 3.x tree. Runtime DLLs just
REM copied by windeployqt (D3Dcompiler, MSVC, wasmer, etc.) are not Qt modules.
for %%f in ("%DATA_DIR%\Data*.dll" "%DATA_DIR%\Parser*.dll" "%DATA_DIR%\ProtobufParser.dll" "%DATA_DIR%\Toolbox*.dll" "%DATA_DIR%\Publisher*.dll") do (
    if exist "%%f" (
        echo Processing: %%~nxf
        "%WINDEPLOYQT%" --release "%%f"
        if errorlevel 1 exit /b 1
    )
)

echo Done.
