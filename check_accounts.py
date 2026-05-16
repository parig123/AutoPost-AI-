from app import create_app
from models.database import db, LinkedInAccount

app = create_app()
with app.app_context():
    accounts = LinkedInAccount.query.all()
    print("--- LinkedIn Accounts ---")
    for acc in accounts:
        print(f"ID: {acc.id}, Name: {acc.name}, LinkedIn ID: {acc.linkedin_id}")
