@echo off

:start
transfer.py
waitfor /t 120 nothingnothing
goto start