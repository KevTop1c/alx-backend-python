import sqlite3


class DatabaseConnection:
    def __init__(self, db_name):
        self.db_name = db_name
        self.conn = None
        self.cursor = None


    def __enter__(self):
        try:
            self.conn = sqlite3.connect(self.db_name)
            self.cursor = self.conn.cursor()
            print(f"Connected to database: {self.db_name}")
            return self.cursor
        except sqlite3.Error as e:
            print(f"Error while connecting to database: {e}")
            raise


    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.cursor:
            self.cursor.close()
            print(f"Closed database cursor: {self.cursor}")

        if self.conn:
            if exc_type is None:
                self.conn.commit()
                print("Changes committed to database")
            else:
                self.conn.rollback()
                print("Changes rolled back due to exception")

            self.conn.close()
            print(f"Closed database connection: {self.conn}")

        return False



def setup_sample_database():
    """Create a sample database with some test data"""
    try:
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL
            )
            """
        )

        # Insert some sample data
        cursor.execute("""DELETE FROM users""") # Clear existing data

        sample_user = [
            ("John Doe", "john@example.com"),
            ("Jane Smith", "jane@example.com"),
            ("Bob Johnson", "bob@example.com"),
        ]

        cursor.executemany("INSERT INTO users (name, email) VALUES (?, ?)", sample_user)
        conn.commit()
        conn.close()
        print("Sample database setup complete")

    except sqlite3.Error as e:
        print(f"Error while connecting to database: {e}")


def main():
    setup_sample_database()

    try:
        with DatabaseConnection("users.db") as cursor:
            # Execute the query
            cursor.execute("SELECT * FROM users")

            # Fetch and print the users
            result = cursor.fetchall()
            print("\nQuery results:")
            print("ID | Name | Email")
            print("-" * 30)
            for row in result:
                user_id, name, email = row
                print(f"{user_id} | {name} | {email}")

    except sqlite3.Error as e:
        print(f"Error while connecting to database: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise



if __name__ == "__main__":
    main()