@echo off
title Muestreo de Internet - Dataset Manager
color 0A

echo ========================================================
echo         INICIANDO ENTORNO DE MUESTREO DE INTERNET
echo ========================================================
echo.

:: Verificar si Python está instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR CRITICO] Python no esta instalado o no se encuentra en el PATH del sistema.
    echo Por favor instala Python antes de ejecutar este script.
    pause
    exit /b
)

:: Comprobar e instalar dependencias desde requirements.txt
echo [1/2] Verificando e instalando dependencias necesarias...
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo [ADVERTENCIA] Hubo un pequeño problema al actualizar dependencias mediante pip. Intentando continuar...
) else (
    echo [OK] Dependencias verificadas correctamente.
)

:: Verificar y crear estructura de directorios requerida
echo [2/2] Verificando estructura de directorios y carpetas...
if not exist "salidas" (
    mkdir salidas
    echo [OK] Carpeta 'salidas' creada exitosamente.
)

echo.
echo ========================================================
echo        SISTEMA LISTO - INICIANDO APLICACION
echo ========================================================
echo.

:: Ejecutar script principal de Python desde la raíz
python main.py

echo.
echo ========================================================
echo              PROGRAMA FINALIZADO CON EXITO
echo ========================================================
pause