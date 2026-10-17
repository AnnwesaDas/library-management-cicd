import zlib
from datetime import datetime, timedelta, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

LOAN_DAYS = 14


def utcnow():
    # Stored without a time zone, so every date in the app is naive UTC.
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    books = db.relationship("Book", back_populates="member")

    @property
    def overdue_count(self):
        return sum(book.is_overdue for book in self.books)


class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(150), nullable=False)
    genre = db.Column(db.String(50), nullable=False, default="General")
    year = db.Column(db.Integer)
    # Set while the book is issued, empty while it is on the shelf.
    member_id = db.Column(db.Integer, db.ForeignKey("member.id"))
    issued_at = db.Column(db.DateTime)
    member = db.relationship("Member", back_populates="books")

    @property
    def is_available(self):
        return self.member is None

    @property
    def due_at(self):
        return self.issued_at + timedelta(days=LOAN_DAYS) if self.issued_at else None

    @property
    def is_overdue(self):
        return self.due_at is not None and self.due_at < utcnow()

    @property
    def days_left(self):
        return (self.due_at - utcnow()).days if self.due_at else None

    @property
    def cover_hue(self):
        # Same colour for every book of a genre, used by the CSS book cover.
        return zlib.crc32(self.genre.encode()) % 360

    def issue_to(self, member, when=None):
        if not self.is_available:
            raise ValueError(f'"{self.title}" is already issued to {self.member.name}.')
        self.member = member
        self.issued_at = when or utcnow()

    def give_back(self):
        if self.is_available:
            raise ValueError(f'"{self.title}" is not issued.')
        self.member = None
        self.issued_at = None
