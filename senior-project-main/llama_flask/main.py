"""
虛擬環境:
venv\Scripts\activate

打開 terminal 終端機，
到路徑下打上 python main.py

"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=8000)
