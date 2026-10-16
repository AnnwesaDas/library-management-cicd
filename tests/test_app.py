import pytest

from library import create_app
from library.models import Book, Member, db


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
    book = Book(title="Clean Code", author="Robert C. Martin")
    riya = Member(name="Riya", email="riya@example.com")
    arjun = Member(name="Arjun", email="arjun@example.com")
    db.session.add_all([book, riya, arjun])
    db.session.commit()
    return book, riya, arjun


def test_add_book(client):
    response = client.post("/books", data={"title": "Dune", "author": "Frank Herbert"}, follow_redirects=True)

    assert response.status_code == 200
    assert b"Dune" in response.data
    assert Book.query.one().author == "Frank Herbert"


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


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
