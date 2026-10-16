from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    books = db.relationship("Book", back_populates="member")


class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    # Set while the book is issued, empty while it is on the shelf.
    member_id = db.Column(db.Integer, db.ForeignKey("member.id"))
    issued_at = db.Column(db.DateTime)
    member = db.relationship("Member", back_populates="books")

    @property
    def is_available(self):
        return self.member is None

    def issue_to(self, member):
        if not self.is_available:
            raise ValueError(f'"{self.title}" is already issued to {self.member.name}.')
        self.member = member
        self.issued_at = datetime.now(timezone.utc)

    def give_back(self):
        if self.is_available:
            raise ValueError(f'"{self.title}" is not issued.')
        self.member = None
        self.issued_at = None
