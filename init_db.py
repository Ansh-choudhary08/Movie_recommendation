from app import app, db
from models import User, WatchlistItem
import os
import sys

def init_database():
    try:
        # Get the absolute path to the instance directory
        instance_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'instance'))
        
        # Create instance directory if it doesn't exist
        if not os.path.exists(instance_path):
            os.makedirs(instance_path)
            print(f"Created instance directory at {instance_path}")
        
        # Set proper permissions for the directory
        os.chmod(instance_path, 0o755)
        
        # Get the database file path
        db_path = os.path.join(instance_path, 'movie_finder.db')
        
        with app.app_context():
            # Drop all tables
            db.drop_all()
            print("Dropped all existing tables")
            
            # Create all tables
            db.create_all()
            print("Created all tables")
            
            # Set proper permissions for the database file
            if os.path.exists(db_path):
                os.chmod(db_path, 0o644)
                print(f"Database file created at {db_path}")
            
            print("Database initialized successfully!")
            
    except Exception as e:
        print(f"Error initializing database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_database() 