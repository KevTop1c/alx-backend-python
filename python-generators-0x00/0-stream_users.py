import mysql.connector
from contextlib import contextmanager
from dotenv import load_dotenv
import os

# Load environment variable from .env
load_dotenv()

@contextmanager
def get_connection():
    """Context manager to handle MySQL connection with env variables."""
    connection = mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "ALX_prodev"),
    )
    try:
        yield connection
    finally:
        connection.close()


def stream_users():
    """
    Generator that streams rows from user_data table one by one.
    Uses a single loop with yield.
    """
    with get_connection() as connection:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT * FROM user_data")
            for row in cursor:
                yield row