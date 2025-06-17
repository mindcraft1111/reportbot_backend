import os
from dotenv import load_dotenv
from sqlalchemy import create_engine


# =============================================
# GEMINI API KEY 등록
# =============================================
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
os.environ["GOOGLE_API_KEY"] = api_key

# =============================================
# MySQL 연결 설정
# =============================================
user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
host = os.getenv("SERVER_HOST")
port = "3306"
database = os.getenv("DB_NAME")

DB_ENGINE = create_engine(
    f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"
)
