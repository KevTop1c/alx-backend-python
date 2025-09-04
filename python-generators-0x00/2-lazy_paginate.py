import mysql.connector
from contextlib import contextmanager
from dotenv import load_dotenv
import os


load_dotenv()

@contextmanager
def get_connection():
    """Context manager to handle MySQL connection with env variables."""
    connection = mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_DATABASE", "ALX_prodev"),
    )
    try:
        yield connection
    finally:
        connection.close()


def paginate_users(page_size, offset):
    """
    Fetch one page of users starting from a given offset.
    Returns a list of dicts.
    """
    with get_connection() as connection:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(
                "SELECT * FROM user_data LIMIT %s OFFSET %s",
                (page_size, offset),
            )
            return cursor.fetchall()


def lazy_paginate(page_size):
    """
    Generator that lazily loads users page by page.
    Only fetches the next page when needed.
    """
    offset = 0
    while True:
        page = paginate_users(page_size, offset)
        if not page:
            break
        yield page
        offset += page_size


