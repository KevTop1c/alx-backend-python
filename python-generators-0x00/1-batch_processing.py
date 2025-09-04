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
        database=os.getenv("DB_NAME", "ALX_prodev"),
    )
    try:
        yield connection
    finally:
        connection.close()


def stream_users_in_batches(batch_size):
    """
    Generator that fetches rows in batches from user_data table.
    Yields one batch at a time as a list of dicts.
    """
    with get_connection() as connection:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT * FROM user_data")
            while True:
                batch = cursor.fetchmany(batch_size)
                if not batch:
                    break
                yield batch


def batch_processing(batch_size):
    """Processes users in batches, yielding only users over age 25."""
    for batch in stream_users_in_batches(batch_size):
        filtered = (user for user in batch if int(user["age"]) > 25)
        filtered_list = list(filtered)
        if filtered_list:
            yield filtered_list
    return