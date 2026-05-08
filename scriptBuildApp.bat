@echo off
echo [BeatSound] Iniciando construcao do APK...
.venv\Scripts\flet.exe build apk app
echo [BeatSound] Processo concluido! Verifique a pasta app/build.
pause