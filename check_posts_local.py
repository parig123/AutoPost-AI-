from app import create_app
from models.database import Post, db

app = create_app()
with app.app_context():
    posts = Post.query.order_by(Post.id.desc()).limit(10).all()
    print("ID | Status | Error Message")
    print("-" * 30)
    for p in posts:
        print(f"{p.id} | {p.status} | {p.error_message}")
