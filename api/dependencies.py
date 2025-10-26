from db import sessionLocal


def get_db():
    """Database session dependency."""
    db = sessionLocal()
    try:
        yield db
    finally:
        db.close()