# 建立 url 及 route 關聯
from flask import Flask
from app.route import index, predict
import os
from dotenv import load_dotenv


def create_app():
    # Load environment variables from .env file
    load_dotenv()

    app = Flask(__name__)

    # Set the secret key from environment variables
    app.secret_key = os.getenv("SECRET_KEY")

    # 載入配置，例如靜態檔案、模板等
    app.config["TEMPLATES_AUTO_RELOAD"] = True

    # 載入路由
    from .route import app as route_blueprint

    app.register_blueprint(route_blueprint)

    return app
