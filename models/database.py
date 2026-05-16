from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    default_tone = db.Column(db.String(50), default='Professional')
    default_approval_mode = db.Column(db.String(20), default='Require Approval')
    theme = db.Column(db.String(20), default='light')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    linkedin_accounts = db.relationship('LinkedInAccount', backref='user', lazy=True)

    # Flask-Login properties
    def get_id(self):
        return str(self.id)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

class LinkedInAccount(db.Model):
    __tablename__ = 'linkedin_accounts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    linkedin_id = db.Column(db.String(100), unique=True, nullable=False)
    linkedin_token = db.Column(db.String(512))
    name = db.Column(db.String(150))
    profile_picture_url = db.Column(db.String(500))
    account_type = db.Column(db.String(20), default='PERSON') # PERSON, ORGANIZATION
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    posts = db.relationship('Post', backref='linkedin_account', lazy=True)

class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    linkedin_account_id = db.Column(db.Integer, db.ForeignKey('linkedin_accounts.id'))
    topic = db.Column(db.String(255))
    generated_text = db.Column(db.Text)
    generated_image_url = db.Column(db.String(500))
    status = db.Column(db.String(50)) # Scheduled, Pending Approval, Published, Failed
    scheduled_time = db.Column(db.DateTime)
    timezone = db.Column(db.String(50))
    tone = db.Column(db.String(50))
    length = db.Column(db.String(50))
    image_style = db.Column(db.String(50))
    approval_status = db.Column(db.String(50))
    linkedin_post_id = db.Column(db.String(100))
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Schedule(db.Model):
    __tablename__ = 'schedules'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    day_of_week = db.Column(db.Integer)
    time = db.Column(db.Time)
    is_active = db.Column(db.Boolean, default=True)
    interval_days = db.Column(db.Integer)

class Template(db.Model):
    __tablename__ = 'templates'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    name = db.Column(db.String(100))
    framework_text = db.Column(db.Text)
    tone = db.Column(db.String(50))
    is_default = db.Column(db.Boolean, default=False)

class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))
    action = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    details = db.Column(db.Text)

class Idea(db.Model):
    __tablename__ = 'ideas'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

