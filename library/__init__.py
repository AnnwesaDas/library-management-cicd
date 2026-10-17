import csv
import os
import random
from datetime import timedelta
from pathlib import Path

from flask import Flask

from .models import Book, Member, db, utcnow
from .views import bp

BOOKS_CSV = Path(__file__).parent / "data" / "books.csv"

MEMBER_NAMES = [
    "Aarav Sharma", "Ananya Iyer", "Arjun Roy", "Diya Patel", "Ishaan Gupta",
    "Kavya Nair", "Meera Joshi", "Neha Verma", "Rahul Mehta", "Riya Sen",
    "Rohan Das", "Saanvi Reddy", "Siddharth Rao", "Sneha Kulkarni", "Tanvi Bose",
    "Vihaan Singh", "Aditi Chatterjee", "Kabir Malhotra", "Pooja Menon", "Aryan Kapoor",
    "Nisha Pillai", "Varun Bhatt", "Ishita Ghosh", "Karan Saxena", "Priya Desai",
    "Yash Agarwal", "Zoya Khan", "Dev Mishra", "Lakshmi Krishnan", "Om Prakash",
]


def create_app(config=None):
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url(os.environ.get("DATABASE_URL"))
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or "dev"
    app.config["APP_VERSION"] = os.environ.get("APP_VERSION", "dev")[:7]
    if config:
        app.config.update(config)

    db.init_app(app)
    app.register_blueprint(bp)

    with app.app_context():
        db.create_all()
        if not app.testing:
            add_sample_data()

    return app


def database_url(url):
    if not url:
        return "sqlite:///library.db"
    # Hosting providers give postgres:// or postgresql:// URLs; use the installed psycopg 3 driver.
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


def add_sample_data():
    if Book.query.first() or Member.query.first():
        return

    with open(BOOKS_CSV, encoding="utf-8") as f:
        books = [
            Book(title=row["title"], author=row["author"], genre=row["genre"], year=int(row["year"]) if row["year"] else None)
            for row in csv.DictReader(f)
        ]
    members = [Member(name=name, email=name.lower().replace(" ", ".") + "@example.com") for name in MEMBER_NAMES]

    # Issue some books 0-28 days ago so the dashboard shows loans, some of them overdue.
    rng = random.Random(42)
    now = utcnow()
    for book in rng.sample(books, 30):
        book.issue_to(rng.choice(members), when=now - timedelta(days=rng.randint(0, 28), hours=rng.randint(0, 23)))

    db.session.add_all(books + members)
    db.session.commit()
