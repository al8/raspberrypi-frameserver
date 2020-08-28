@echo off

:start
sync_all.py
timeout /t 600
goto start