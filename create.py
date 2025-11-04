import os
from app import app, db

db_path = 'instance/ctm.db'

with app.app_context():
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print(f"Database {db_path} deleted successfully!")
        except PermissionError:
            print(f"⚠️ O banco {db_path} está em uso e não pôde ser removido. Tentando recriar tabelas...")

    db.create_all()
    print("Database created or updated successfully!")
