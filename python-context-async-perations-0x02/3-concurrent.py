import asyncio
import aiosqlite
from datetime import datetime


async def async_fetch_users():
    """Fetch all users from the database"""
    try:
        async with aiosqlite.connect("users.db") as db:
            async with db.execute("SELECT * FROM users") as cursor:
                results = await cursor.fetchall()
                print(f"Fetched all users at {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}")
                return results
    except Exception as e:
        print(f"Error in async_fetch_users: {e}")
        return []


async def async_fetch_older_users():
    """Fetch all users older than 40 from the database"""
    try:
        async with aiosqlite.connect("users.db") as db:
            async with db.execute("SELECT * FROM users WHERE age > ?", (40,)) as cursor:
                results = await cursor.fetchall()
                print(f"Fetched all users at {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}")
                return results
    except Exception as e:
        print(f"Error in async_fetch_older_users: {e}")
        return []


async def fetch_concurrently():
    """Run both queries concurrently using asyncio.gather."""
    print("Starting concurrent queries...")
    start_time = datetime.now()

    # Execute both queries concurrently
    results = await asyncio.gather(
        async_fetch_users(),
        async_fetch_older_users(),
    )

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds() * 1000

    print(f"\nFinished concurrent queries in {duration:.2f}ms.")
    return results


async def setup_database():
    try:
        async with aiosqlite.connect("users.db") as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    age INTEGER NOT NULL,
                    email TEXT NOT NULL
                )
                """
            )

            # Clear all data if table exists
            await db.execute("""DELETE FROM users""")

            # Insert sample data
            sample_data = [
                ("John Doe", 34, "john@mail.com"),
                ("Abigail Jane", 23, "abigail@mail.com"),
                ("Jasper Jet", 45, "jet@mail.com"),
                ("Jane Smith", 20, "jane@mail.com"),
                ("Abraham Armstrong", 48, "abh@mail.com"),
                ("Caesar Milton", 40, "caesar@mail.com"),
                ("Amanda Jacobs", 30, "amanda@mail.com"),
            ]

            await db.executemany("""INSERT INTO users (name, age, email) VALUES (?, ?, ?)""", sample_data)
            await db.commit()
            print("Database setup complete.")

    except Exception as e:
        print(f"Error in setup_database: {e}")


async def main():
    # Set up the database
    await setup_database()

    print("\n" + "=" * 60)
    print("RUNNING CONCURRENT QUERIES")
    print("=" * 60)

    # Run the queries concurrently
    all_users, older_users = await fetch_concurrently()

    # Display the results
    print("\nRESULTS:")
    print("-" * 40)

    # 1. For All Users
    print("\nAll Users:")
    print("ID | Name               | Age | Email")
    print("-" * 40)
    for all_user in all_users:
        user_id, name, age, email = all_user
        print(f"{user_id:2} | {name:18} | {age:3} | {email}")
    print(f"\nTotal users: {len(all_users)}")

    # 2. For Users older than 40
    print("\nOlder Users:")
    print("ID | Name               | Age | Email")
    print("-" * 40)
    for older_user in older_users:
        user_id, name, age, email = older_user
        print(f"{user_id:2} | {name:18} | {age:3} | {email}")
    print(f"\nTotal users: {len(older_users)}")


if __name__ == "__main__":
    asyncio.run(main())