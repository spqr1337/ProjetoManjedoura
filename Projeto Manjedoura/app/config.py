import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "altere-esta-chave-antes-de-produzir")
    DATABASE_PATH = Path(
        os.getenv("DATABASE_PATH", BASE_DIR / "data" / "projeto_manjedoura.db")
    )
    DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"
