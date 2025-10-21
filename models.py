from app import db
from datetime import datetime

class AnalyzedString(db.Model):
    id = db.Column(db.String(64), primary_key=True)
    value = db.Column(db.String(255), unique=True, nullable=False)
    length = db.Column(db.Integer, nullable=False)
    is_palindrome = db.Column(db.Boolean, nullable=False)
    unique_characters = db.Column(db.Integer, nullable=False)
    word_count = db.Column(db.Integer, nullable=False)
    character_frequency_map = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
