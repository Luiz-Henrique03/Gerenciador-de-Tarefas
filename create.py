import os
from app import app, db

# Caminho para o arquivo do banco de dados SQLite
db_path = 'instance/ctm.db'  # Certifique-se de que o caminho está correto para o seu projeto

with app.app_context():
    # Verifica se o banco de dados existe e o remove
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Database {db_path} deleted successfully!")

    # Recria o banco de dados
    db.create_all()
    print("Database created successfully!")
