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


def stream_user_ages():
    """
    Generator that streams user ages one by one from the database.
    """
    with get_connection() as connection:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT age FROM user_data")
            for row in cursor:
                yield int(row["age"])


def calculate_average_age():
    """
    Calculate average age using the generator without loading all rows.
    """
    total = 0
    count = 0

    for age in stream_user_ages():
        total += age
        count += 1

    average = total / count if count > 0 else 0
    print(f"Average age of users: {average:.2f}")


if __name__ == "__main__":
    calculate_average_age()