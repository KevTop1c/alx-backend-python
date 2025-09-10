import sqlite3


class ExecuteQuery:
    def __init__(self, query, params=None, db_name="users.db"):
        self.query = query
        self.params = params if params is not None else ()
        self.db_name = db_name
        self.conn = None
        self.cursor = None
        self.result = None


    def __enter__(self):
        """Establish connection, execute query, and return results"""
        try:
            self.conn = sqlite3.connect(self.db_name)
            self.cursor = self.conn.cursor()

            # Execute the query with parameters
            if self.params:
                self.cursor.execute(self.query, self.params)
            else:
                self.cursor.execute(self.query)

            # Fetch all results
            self.result = self.cursor.fetchall()
            return self.result

        except sqlite3.Error as e:
            print(f"Error executing query: {e}")
            if self.conn:
                self.conn.rollback()
            raise


    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up resources"""
        if self.cursor:
            self.cursor.close()

        if self.conn:
            if exc_type is None: # No exception occurred
                self.conn.commit()
            else:
                self.conn.rollback()
            self.conn.close()

        return False


def setup_sample_database():
    """Create a sample database with users of different ages"""
    try:
        conn = sqlite3.connect( "users.db")
        cursor = conn.cursor()

        # Create users table if it doesn't exist
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                email TEXT NOT NULL
            )
            """
        )

        # Clear data if already exists
        cursor.execute("""DELETE FROM users""")

        sample_users = [
            ("John Doe", 28, "john@example.com"),
            ("Jane Smith", 32, "jane@example.com"),
            ("Bob Johnson", 22, "bob@example.com"),
            ("Alice Brown", 45, "alice@example.com"),
            ("Charlie Wilson", 18, "charlie@example.com"),
            ("Efo Kojo", 50, "efokojo@example.com"),
        ]

        cursor.executemany("INSERT INTO users (name, age, email) VALUES (?, ?, ?)", sample_users)
        conn.commit()
        conn.close()
        print("Sample database created with ages")

    except sqlite3.Error as e:
        print(f"Error setting up database: {e}")


def main():
    setup_sample_database()

    # Define our query and parameter
    query = "SELECT * FROM users WHERE age > ?"
    param = (30,)

    print("Executing query: SELECT * FROM users WHERE age > 25")
    print("-" * 50)

    try:
        with ExecuteQuery(query, param) as results:
            if results:
                print("Users older than 25:")
                print("ID | Name | Age | Email")
                print("-" * 40)
                for row in results:
                    user_id, name, age, email = row
                    print(f"{user_id} | {name} | {age} | {email}")
            else:
                print("No users found older than 25")

    except sqlite3.Error as e:
        print(f"Error executing query: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()