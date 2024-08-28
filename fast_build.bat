@echo off
python -m venv venv
call venv\Scripts\activate
pip install -r requirements.txt
pyinstaller autopak.spec
pause