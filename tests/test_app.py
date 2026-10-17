from datetime import timedelta

import pytest

from library import add_sample_data, create_app, database_url
from library.models import Book, Member, db, utcnow


@pytest.fixture
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def book_and_members(app):
    book = Book(title="Clean Code", author="Robert C. Martin", genre="Computer Science")
    riya = Member(name="Riya", email="riya@example.com")
    arjun = Member(name="Arjun", email="arjun@example.com")
    db.session.add_all([book, riya, arjun])
    db.session.commit()
    return book, riya, arjun


def test_add_book(client):
    response = client.post("/books", data={"title": "Dune", "author": "Frank Herbert", "genre": "Science Fiction", "year": "1965"}, follow_redirects=True)

    assert response.status_code == 200
    assert b"Dune" in response.data
    book = Book.query.one()
    assert (book.author, book.genre, book.year) == ("Frank Herbert", "Science Fiction", 1965)


def test_add_member(client):
    response = client.post("/members", data={"name": "Meera", "email": "meera@example.com"}, follow_redirects=True)

    assert response.status_code == 200
    assert b"Meera" in response.data
    assert Member.query.one().email == "meera@example.com"


def test_issue_book_makes_it_unavailable(client, book_and_members):
    book, riya, _ = book_and_members

    client.post(f"/books/{book.id}/issue", data={"member_id": riya.id})

    assert not book.is_available
    assert book.member == riya
    assert book.due_at == book.issued_at + timedelta(days=14)


def test_issuing_an_issued_book_fails(client, book_and_members):
    book, riya, arjun = book_and_members
    client.post(f"/books/{book.id}/issue", data={"member_id": riya.id})

    response = client.post(f"/books/{book.id}/issue", data={"member_id": arjun.id}, follow_redirects=True)

    assert b"already issued" in response.data
    assert book.member == riya


def test_return_book_makes_it_available(client, book_and_members):
    book, riya, _ = book_and_members
    client.post(f"/books/{book.id}/issue", data={"member_id": riya.id})

    client.post(f"/books/{book.id}/return")

    assert book.is_available


def test_book_is_overdue_after_loan_period(book_and_members):
    book, riya, arjun = book_and_members
    late = Book(title="Dune", author="Frank Herbert")
    db.session.add(late)
    book.issue_to(riya, when=utcnow() - timedelta(days=3))
    late.issue_to(arjun, when=utcnow() - timedelta(days=20))

    assert not book.is_overdue
    assert late.is_overdue
    assert arjun.overdue_count == 1


def test_search_and_filters(client, book_and_members):
    book, riya, _ = book_and_members
    db.session.add(Book(title="Dune", author="Frank Herbert", genre="Science Fiction"))
    book.issue_to(riya, when=utcnow() - timedelta(days=20))
    db.session.commit()

    assert b"Dune" in client.get("/books?q=herbert").data
    assert b"Clean Code" not in client.get("/books?q=herbert").data
    assert b"Clean Code" not in client.get("/books?genre=Science+Fiction").data
    assert b"Dune" not in client.get("/books?status=overdue").data
    assert b"Clean Code" in client.get("/books?status=overdue").data


def test_sample_data_loads_once(app):
    add_sample_data()
    add_sample_data()

    assert Book.query.count() == 256
    assert Member.query.count() == 30
    assert Book.query.filter(Book.member_id.is_not(None)).count() == 30


def test_pages_render(client, app):
    add_sample_data()

    for url in ("/", "/books", "/books?page=11", "/members"):
        assert client.get(url).status_code == 200


def test_database_url_uses_psycopg_driver():
    assert database_url("postgres://u:p@host/db") == "postgresql+psycopg://u:p@host/db"
    assert database_url("postgresql://u:p@host/db") == "postgresql+psycopg://u:p@host/db"
    assert database_url(None) == "sqlite:///library.db"


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"
