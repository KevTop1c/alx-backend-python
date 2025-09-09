import sqlite3
import functools


def with_db_connection(func):
    """Decorator that automatically handles opening and closing database connections"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        conn = sqlite3.connect('users.db')
        try:
            result = func(conn, *args, **kwargs)
            conn.commit()
            return result
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    return wrapper


def transactional(func):
    """Decorator that ensures database operations are wrapped in a transaction"""
    @functools.wraps(func)
    def wrapper(conn, *args, **kwargs):
        # Check if we're already in a transaction (nested transactions)
        original_autocommit = conn.isolation_level
        savepoint_name = None
        try:
            # If not already in a transaction, start one
            if conn.isolation_level is None:  # Autocommit mode
                conn.isolation_level = 'DEFERRED'  # Start a transaction
            else:
                # Create a savepoint for nested transactions
                savepoint_name = f"sp_{id(conn)}_{id(func)}"
                conn.execute(f"SAVEPOINT {savepoint_name}")

            # Execute the function
            result = func(conn, *args, **kwargs)

            # Commit or release savepoint
            if savepoint_name:
                conn.execute(f"RELEASE SAVEPOINT {savepoint_name}")
            else:
                conn.commit()
                conn.isolation_level = original_autocommit  # Restore original mode
            return result

        except Exception as e:
            # Rollback or rollback to savepoint
            if savepoint_name:
                conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
            else:
                conn.rollback()
                conn.isolation_level = original_autocommit  # Restore original mode
            raise e

    return wrapper


@with_db_connection
@transactional
def update_user_email(conn, user_id, new_email):
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET email = ? WHERE id = ?", (new_email, user_id))


# Update user's email with automatic transaction handling
update_user_email(user_id=1, new_email='Crawford_Cartwright@hotmail.com')