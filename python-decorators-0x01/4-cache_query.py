import sqlite3
import functools

query_cache = {}


def cache_query(func):
    """Decorator that caches query results based on the SQL query string."""

    @functools.wraps(func)
    def wrapper(conn, query, *args, **kwargs):
        # If query is already cached, return cached result
        if query in query_cache:
            print(f"[CACHE HIT] Returning cached result for: {query}")
            return query_cache[query]

        # Otherwise, execute the function and store result
        print(f"[CACHE MISS] Executing and caching result for: {query}")
        result = func(conn, query, *args, **kwargs)
        query_cache[query] = result
        return result
    return wrapper


def with_db_connection(func):
    """Decorator to automatically handle DB connection lifecycle."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        conn = sqlite3.connect("users.db")
        try:
            return func(conn, *args, **kwargs)
        finally:
            conn.close()
    return wrapper


@with_db_connection
@cache_query
def fetch_users_with_cache(conn, query):
    cursor = conn.cursor()
    cursor.execute(query)
    return cursor.fetchall()


#### First call will cache the result
users = fetch_users_with_cache(query="SELECT * FROM users")
print(users)

#### Second call will use the cached result
users_again = fetch_users_with_cache(query="SELECT * FROM users")
print(users_again)
