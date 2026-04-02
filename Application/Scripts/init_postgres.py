"""PostgreSQL initialization module."""

def init_postgres(db_name: str, user: str, password: str):
    """Initialize PostgreSQL database.
    
    Args:
        db_name: Database name
        user: Database user
        password: Database password
    """
    try:
        from Infrastructure.relationalDB.postgres_repo import PostgresRepository
        repo = PostgresRepository()
        print(f"PostgreSQL database '{db_name}' initialized successfully!")
    except Exception as e:
        print(f"Error initializing PostgreSQL: {e}")
        raise
