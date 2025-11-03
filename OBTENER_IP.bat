@echo off
echo ========================================
echo   OBTENER IP LOCAL PARA ACCESO MOVIL
echo ========================================
echo.

echo Obteniendo tu direccion IP local...
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    set ip=%%a
    goto :found
)
:found
set ip=%ip:~1%

echo.
echo ========================================
echo Tu IP local es: %ip%
echo ========================================
echo.
echo Para acceder desde tu celular:
echo http://%ip%:5000
echo.
echo IMPORTANTE:
echo - Ambos dispositivos deben estar en la misma red WiFi
echo - Desactiva el firewall temporalmente si no funciona
echo.
pause



