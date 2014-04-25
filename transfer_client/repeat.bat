@echo off

:start
transfer.py
waitfor /t 30 nothingnothing
goto start