import csv
import uuid
import os
import mysql.connector
from dotenv import load_dotenv


# ----------------------------
# Connecting to MySQL Server
# ----------------------------

# Load environment variables from .env
load_dotenv()


def connect_db():
    try:
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
        )
        return connection
    except mysql.connector.Error as err:
        print(f"Failed connecting to MySQL database: {err}")
        yield None


# ----------------------------
# Creating DB ALX_prodev
# ----------------------------
def create_database(connection):
    cursor = connection.cursor()
    try:
        cursor.execute("CREATE DATABASE IF NOT EXISTS ALX_prodev")
        print("ALX_prodev database created")
    except mysql.connector.Error as err:
        print(f"Failed creating database: {err}")
    finally:
        cursor.close()


# ----------------------------
# Connecting to DB ALX_prodev
# ----------------------------
def connect_to_prodev():
    try:
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "ALX_prodev"),
        )
        return connection
    except mysql.connector.Error as err:
        print(f"Failed connecting to ALX_prodev: {err}")
        return None


# ----------------------------
# Create user_data table
# ----------------------------
def create_table(connection):
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS user_data (
                user_id CHAR(36) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL,
                age DECIMAL NOT NULL,
                INDEX(email)
            )
        """
        )
        print("Table user_data created successfully")
    except mysql.connector.Error as err:
        print(f"Failed creating user_data table: {err}")
    finally:
        cursor.close()


# ----------------------------
# Insert data into user_data table
# ----------------------------
def insert_data(connection, data):
    cursor = connection.cursor()
    try:
        name, email, age = data
        age_value = int(age)

        cursor.execute("SELECT * FROM user_data WHERE email = %s", (email,))
        result = cursor.fetchone()

        if not result:
            cursor.execute(
                """
                           INSERT INTO user_data (user_id, name, email, age)
                           VALUES (%s, %s, %s, %s)
                           """,
                (str(uuid.uuid4()), name, email, age_value),
            )
            connection.commit()
            print(f"Inserted: {name} - {email}")
        else:
            print(f"Skipped (already exists): {email}")

    except mysql.connector.Error as err:
        print(f"Error inserting data: {err}")
    finally:
        cursor.close()


# -------------------------
# Main Script
# -------------------------
if __name__ == "__main__":
    # Connect to MySQL server
    server_conn = connect_db()
    if server_conn:
        create_database(server_conn)
        server_conn.close()

    # Connect to ALX_prodev DB
    db_conn = connect_to_prodev()
    if db_conn:
        create_table(db_conn)

        with open("user_data.csv", "r") as file:
            reader = csv.reader(file)
            next(reader)
            for row in reader:
                insert_data(db_conn, row)

        db_conn.close()

