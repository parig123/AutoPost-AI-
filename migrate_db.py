from app import create_app
from models.database import db
import sqlalchemy as sa

app = create_app()

with app.app_context():
    engine = db.engine
    inspector = sa.inspect(engine)
    
    # Check existing columns in users table
    columns = [col['name'] for col in inspector.get_columns('users')]
    
    # Check if ideas table exists
    if not inspector.has_table('ideas'):
        db.create_all()
        print("Created new tables (including 'ideas')")
    
    with engine.connect() as conn:
        # User table migrations
        if 'name' not in columns:
            conn.execute(sa.text("ALTER TABLE users ADD COLUMN name VARCHAR(150)"))
            print("Added 'name' column to users")
        
        if 'email' not in columns:
            conn.execute(sa.text("ALTER TABLE users ADD COLUMN email VARCHAR(150)"))
            print("Added 'email' column to users")
        
        if 'profile_picture_url' not in columns:
            conn.execute(sa.text("ALTER TABLE users ADD COLUMN profile_picture_url VARCHAR(500)"))
            print("Added 'profile_picture_url' column to users")
        
        if 'is_active' not in columns:
            conn.execute(sa.text("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1"))
            print("Added 'is_active' column to users")

        # LinkedInAccount table migrations
        acc_columns = [col['name'] for col in inspector.get_columns('linkedin_accounts')]
        if 'account_type' not in acc_columns:
            conn.execute(sa.text("ALTER TABLE linkedin_accounts ADD COLUMN account_type VARCHAR(20) DEFAULT 'PERSON'"))
            print("Added 'account_type' column to linkedin_accounts")
            # Update existing orgs
            conn.execute(sa.text("UPDATE linkedin_accounts SET account_type = 'ORGANIZATION' WHERE linkedin_id LIKE 'urn:li:organization:%'"))
        
        conn.commit()

    
    print("Migration complete!")

