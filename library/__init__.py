import os

from flask import Flask

from .models import Book, Member, db
from .views import bp


def create_app(config=None):
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL") or "sqlite:///library.db"
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or "dev"
    if config:
        app.config.update(config)

    db.init_app(app)
    app.register_blueprint(bp)

    with app.app_context():
        db.create_all()
        if not app.testing:
            add_sample_data()

    return app


def add_sample_data():
    if Book.query.first() or Member.query.first():
        return
    db.session.add_all([
        Book(title="Clean Code", author="Robert C. Martin"),
        Book(title="The Pragmatic Programmer", author="Andrew Hunt and David Thomas"),
        Book(title="Introduction to Algorithms", author="Thomas H. Cormen"),
        Book(title="Computer Networks", author="Andrew S. Tanenbaum"),
        Book(title="Operating System Concepts", author="Abraham Silberschatz"),
        Member(name="Riya Sen", email="riya@example.com"),
        Member(name="Arjun Roy", email="arjun@example.com"),
        Member(name="Meera Iyer", email="meera@example.com"),
    ])
    db.session.commit()
