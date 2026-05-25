import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-change-me-in-production")
    _db_url = os.environ.get("DATABASE_URL")
    if _db_url:
        SQLALCHEMY_DATABASE_URI = _db_url
    else:
        _mysql_user = os.environ.get("MYSQL_USER", "root")
        _mysql_password = os.environ.get("MYSQL_PASSWORD", "1234")
        _mysql_host = os.environ.get("MYSQL_HOST", "127.0.0.1")
        _mysql_port = os.environ.get("MYSQL_PORT", "3306")
        _mysql_db = os.environ.get("MYSQL_DB", "sromsdb")
        SQLALCHEMY_DATABASE_URI = (
            "mysql+pymysql://"
            f"{_mysql_user}:{_mysql_password}@{_mysql_host}:{_mysql_port}/{_mysql_db}"
            "?charset=utf8mb4"
        )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
