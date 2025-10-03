from database import init_db

if __name__ == '__main__':
    success = init_db()
    if success:
        print("Database initialized successfully!")
    else:
        print("Failed to initialize database!")