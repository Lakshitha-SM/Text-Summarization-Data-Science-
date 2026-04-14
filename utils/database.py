"""
utils/database.py
------------------
Database setup using Flask-SQLAlchemy for User and Summary History.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    summaries = db.relationship('SummaryHistory', backref='author', lazy=True)

class SummaryHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    original_text = db.Column(db.Text, nullable=False)
    summary_text = db.Column(db.Text, nullable=False)
    method = db.Column(db.String(50))
    input_type = db.Column(db.String(50))
    sentiment = db.Column(db.String(20))
    is_favorite = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def init_db(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()
