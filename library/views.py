from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy import or_, text
from sqlalchemy.exc import SQLAlchemyError

from .models import Book, Member, db

bp = Blueprint("main", __name__)


@bp.get("/")
def index():
    issued = Book.query.filter(Book.member_id.is_not(None)).order_by(Book.issued_at.desc()).all()
    return render_template(
        "index.html",
        book_count=Book.query.count(),
        member_count=Member.query.count(),
        issued=issued,
    )


@bp.get("/books")
def books():
    q = request.args.get("q", "").strip()
    query = Book.query
    if q:
        query = query.filter(or_(Book.title.ilike(f"%{q}%"), Book.author.ilike(f"%{q}%")))
    return render_template(
        "books.html",
        books=query.order_by(Book.title).all(),
        members=Member.query.order_by(Member.name).all(),
        q=q,
    )


@bp.post("/books")
def add_book():
    title = request.form.get("title", "").strip()
    author = request.form.get("author", "").strip()
    if title and author:
        db.session.add(Book(title=title, author=author))
        db.session.commit()
        flash(f'Added "{title}".')
    else:
        flash("Title and author are required.", "error")
    return redirect(url_for("main.books"))


@bp.post("/books/<int:book_id>/delete")
def delete_book(book_id):
    book = db.get_or_404(Book, book_id)
    db.session.delete(book)
    db.session.commit()
    flash(f'Deleted "{book.title}".')
    return redirect(url_for("main.books"))


@bp.post("/books/<int:book_id>/issue")
def issue_book(book_id):
    book = db.get_or_404(Book, book_id)
    member_id = request.form.get("member_id", type=int)
    member = db.session.get(Member, member_id) if member_id else None
    if member is None:
        flash("Choose a member to issue the book to.", "error")
        return redirect(url_for("main.books"))
    try:
        book.issue_to(member)
    except ValueError as error:
        flash(str(error), "error")
    else:
        db.session.commit()
        flash(f'Issued "{book.title}" to {member.name}.')
    return redirect(url_for("main.books"))


@bp.post("/books/<int:book_id>/return")
def return_book(book_id):
    book = db.get_or_404(Book, book_id)
    try:
        book.give_back()
    except ValueError as error:
        flash(str(error), "error")
    else:
        db.session.commit()
        flash(f'"{book.title}" was returned.')
    return redirect(url_for("main.books"))


@bp.get("/members")
def members():
    return render_template("members.html", members=Member.query.order_by(Member.name).all())


@bp.post("/members")
def add_member():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    if name and email:
        db.session.add(Member(name=name, email=email))
        db.session.commit()
        flash(f"Added member {name}.")
    else:
        flash("Name and email are required.", "error")
    return redirect(url_for("main.members"))


@bp.get("/health")
def health():
    try:
        db.session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return {"status": "error"}, 503
    return {"status": "ok"}
