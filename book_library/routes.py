import uuid
import datetime
import functools
from flask import (
    Blueprint, 
    current_app, 
    render_template, 
    session, 
    redirect, 
    request, 
    url_for,
    flash
)
from dataclasses import asdict
from book_library.forms import BookForm, ExtendedBookForm, RegisterForm, LoginForm
from book_library.models import Book, User
from passlib.hash import pbkdf2_sha256

pages = Blueprint(
    "pages", __name__, template_folder="templates", static_folder="static"
)



def login_required(route):
    @functools.wraps(route)
    def route_wrapper(*args, **kwargs):
        #session.clear()
        if session.get("email") is None:
            return redirect(url_for(".login"))

        return route(*args, **kwargs)

    return route_wrapper

@pages.route("/")
@login_required
def index():
    user_data = current_app.db.user.find_one({"email": session["email"]})
    user = User(**user_data)
    book_data = current_app.db.books.find({"_id": {"$in": user.books}})
    
    books = [Book(**book) for book in book_data]
    return render_template(
        "index.html",
        title="Book Watchlist",
        books_data=books
    )

@pages.route("/add", methods=["GET","POST"])
@login_required
def add_book():
    form = BookForm()


    if form.validate_on_submit():
        book = Book(
            _id= uuid.uuid4().hex,
            title= form.title.data,
            director= form.director.data,
            year= form.year.data
        )

        current_app.db.books.insert_one(asdict(book))
        current_app.db.user.update_one(
            {"_id": session["user_id"]}, {"$push": {"books": book._id}}
        )

        return redirect(url_for(".book", _id=book._id))

    return render_template("new_book.html", title="Book Library - Add Book", form=form)

@pages.route("/register", methods=["GET", "POST"])
def register():
    if session.get("email"):
        return redirect(url_for(".index"))

    form = RegisterForm()

    if form.validate_on_submit():
        user = User(
            _id=uuid.uuid4().hex,
            email=form.email.data,
            password=pbkdf2_sha256.hash(form.password.data),
        )

        current_app.db.user.insert_one(asdict(user))

        flash("User registered successfully", "success")

        return redirect(url_for(".login"))

    return render_template(
        "register.html", title="Book Library - Register", form=form
    )

@pages.route("/login", methods=["GET", "POST"])
def login():
    if session.get("email"):
        return redirect(url_for(".index"))

    form = LoginForm()

    if form.validate_on_submit():
        user_data = current_app.db.user.find_one({"email": form.email.data})
        if not user_data:
            flash("Login credentials not correct", category="danger")
            return redirect(url_for(".login"))
        user = User(**user_data)

        if user and pbkdf2_sha256.verify(form.password.data, user.password):
            session["user_id"] = user._id
            session["email"] = user.email

            return redirect(url_for(".index"))

        flash("Login credentials not correct", category="danger")

    return render_template("login.html", title="Book Tracker - Login", form=form)

@pages.route("/logout")
def logout():
    current_theme = session.get("theme")
    session.clear()
    session["theme"] = current_theme

    return redirect(url_for(".login"))



@pages.get("/book/<string:_id>")
def book(_id:str):
    book_data = current_app.db.books.find_one({"_id":_id})
    book = Book(**book_data)
    return render_template("book_details.html", book=book)


@pages.get("/book/<string:_id>/rate")
@login_required
def rate_book(_id):
    rating = int(request.args.get("rating"))
    current_app.db.books.update_one({"_id":_id}, {"$set": {"rating":rating}})
    
    return redirect(url_for(".book", _id=_id))

@pages.get("/book/<string:_id>/read")
@login_required
def read_today(_id):
    current_app.db.books.update_one(
        {"_id": _id}, {"$set": {"last_watched": datetime.datetime.today()}}
    )

    return redirect(url_for(".book", _id=_id))

@pages.route("/edit/<string:_id>", methods=["GET", "POST"])
@login_required
def edit_book(_id: str):
    book = Book(**current_app.db.books.find_one({"_id": _id}))
    form = ExtendedBookForm(obj=book)
    if form.validate_on_submit():
        book.title = form.title.data
        book.director = form.director.data
        book.year = form.year.data
        book.cast = form.cast.data
        book.series = form.series.data
        book.tags = form.tags.data
        book.description = form.description.data
        book.video_link = form.video_link.data

        current_app.db.books.update_one({"_id": book._id}, {"$set": asdict(book)})
        return redirect(url_for(".book", _id=book._id))
    return render_template("book_form.html", book=book, form=form)




@pages.get("/toggle-theme")
def toggle_theme():
    current_theme = session.get("theme")
    if current_theme == "dark":
        session["theme"] = "light"
    else:
        session["theme"] = "dark"

    return redirect(request.args.get("current_page"))
