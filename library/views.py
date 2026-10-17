from datetime import timedelta

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from sqlalchemy import func, or_, text
from sqlalchemy.exc import SQLAlchemyError

from .models import LOAN_DAYS, Book, Member, db, utcnow

bp = Blueprint("main", __name__)

PER_PAGE = 24
# Query-string keys that describe the current books view, kept when redirecting back to it.
FILTERS = ("q", "genre", "status", "page")


@bp.app_context_processor
def inject_version():
    return {"app_version": current_app.config["APP_VERSION"]}


def overdue_since():
    return utcnow() - timedelta(days=LOAN_DAYS)


def current_filters(args):
    return {key: args[key] for key in FILTERS if args.get(key)}


def back_to_books():
    return redirect(url_for("main.books", **current_filters(request.args)))


@bp.get("/")
def index():
    issued = Book.query.filter(Book.member_id.is_not(None)).order_by(Book.issued_at).all()
    genres = (
        db.session.query(Book.genre, func.count(Book.id))
        .group_by(Book.genre)
        .order_by(func.count(Book.id).desc(), Book.genre)
        .all()
    )
    book_count = Book.query.count()
    return render_template(
        "index.html",
        book_count=book_count,
        available_count=book_count - len(issued),
        member_count=Member.query.count(),
        issued=issued,
        overdue_count=sum(book.is_overdue for book in issued),
        genres=genres,
        max_genre=max((count for _, count in genres), default=1),
    )


@bp.get("/books")
def books():
    q = request.args.get("q", "").strip()
    genre = request.args.get("genre", "")
    status = request.args.get("status", "")

    query = Book.query
    if q:
        query = query.filter(or_(Book.title.ilike(f"%{q}%"), Book.author.ilike(f"%{q}%")))
    if genre:
        query = query.filter(Book.genre == genre)
    if status == "available":
        query = query.filter(Book.member_id.is_(None))
    elif status == "issued":
        query = query.filter(Book.member_id.is_not(None))
    elif status == "overdue":
        query = query.filter(Book.issued_at < overdue_since())

    page = query.order_by(Book.title).paginate(page=request.args.get("page", 1, type=int), per_page=PER_PAGE, error_out=False)
    return render_template(
        "books.html",
        page=page,
        members=Member.query.order_by(Member.name).all(),
        genres=[g for (g,) in db.session.query(Book.genre).distinct().order_by(Book.genre)],
        q=q,
        genre=genre,
        status=status,
        filters=current_filters(request.args),
    )


@bp.post("/books")
def add_book():
    title = request.form.get("title", "").strip()
    author = request.form.get("author", "").strip()
    genre = request.form.get("genre", "").strip() or "General"
    year = request.form.get("year", type=int)
    if title and author:
        db.session.add(Book(title=title, author=author, genre=genre, year=year))
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
    return back_to_books()


@bp.post("/books/<int:book_id>/issue")
def issue_book(book_id):
    book = db.get_or_404(Book, book_id)
    member_id = request.form.get("member_id", type=int)
    member = db.session.get(Member, member_id) if member_id else None
    if member is None:
        flash("Choose a member to issue the book to.", "error")
        return back_to_books()
    try:
        book.issue_to(member)
    except ValueError as error:
        flash(str(error), "error")
    else:
        db.session.commit()
        flash(f'Issued "{book.title}" to {member.name}. Due back on {book.due_at:%d %b %Y}.')
    return back_to_books()


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
    return back_to_books()


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
    return {"status": "ok", "version": current_app.config["APP_VERSION"]}
