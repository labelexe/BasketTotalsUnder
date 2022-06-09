::pip freeze > requirements.txt

cd %~dp0
python -m venv venv
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
python main.py

