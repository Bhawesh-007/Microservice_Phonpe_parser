import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Use environment variable for the database URL, fallback to local for testing
db_password = os.getenv("DB_PASSWORD", "root") # Fallback to avoid crash if not set
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    f"mysql+pymysql://root:{db_password}@localhost:3306/phonepe_manager"
)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, pool_pre_ping=True
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_all_category_names():
    db = SessionLocal()
    try:
        # Import inside to avoid circular import if models imports database
        from models import Category
        names = db.query(Category.name).distinct().all()
        return [name[0] for name in names] if names else []
    except Exception as e:
        print(f"Error fetching categories from DB: {e}")
        return []
    finally:
        db.close()
