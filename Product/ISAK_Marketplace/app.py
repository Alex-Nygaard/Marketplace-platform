"""
ISAK MARKETPLACE

Developed 2020-2021

############################### File structure ###############################

CompSci_Marketplace
|--- app.py                    <- Main flask application file
|--- database.db
|--- requirements.txt                    <- Required libraries
|--- static                    <- Styling, user image files
    |--- styles.css                     <- Main styling file
    |--- styles.scss                    <- Sass styling file (which is compiled to CSS)
    |--- _main.scss                          - Every .scss file separates individual parts of the styling for different pages
    |--- _profile.scss
    |--- _sell.scss
    |--- _itempage.scss
    |--- _purchase-confirmation.scss
    |--- styles.css.map
    |--- item_pics
        |--- ### user picture files ###                    <- User image files
|--- templates                    <- Jinja (HTML) templates
    |--- base.html                     <- Base template (including navbar, every template inherits from this
    |--- item_page.html
    |--- main.html
    |--- profile.html
    |--- purchase_confirmation.html
    |--- sell.html
|--- venv                     <- Virtual environment
    |--- ### virtual environment files ###


############################### Application structure ###############################
 - Importing libraries
 - Defining key variables
 - Database tables
 - Forms
 - Routes
    - Index
    - Store user
    - Login
    - Logout
    - Sell
    - Profile
    - Item page
 - Additional algorithms
 - Running main application

"""

import os
import sys

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
# from flask_migrate import Migrate
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, RadioField
from wtforms.fields.html5 import DateField, IntegerField
from flask_wtf.file import FileField, FileAllowed

from wtforms.validators import DataRequired, Email, EqualTo, length, NumberRange, ValidationError
from flask_login import LoginManager, UserMixin, current_user, login_user, logout_user, login_required
from flask_dance.contrib.google import make_google_blueprint, google
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError, TokenExpiredError

app = Flask(__name__)
app.config["SECRET_KEY"] = "35j93K7Pf11"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"  # The page where flask redirects if the user tries to access a site without being logged in

# Establish contact with Google authentication server -> requires id and secret key
blueprint = make_google_blueprint(client_id="872204614354-41hm7nk3jb89fsrtj4madroi510npoq5.apps.googleusercontent.com",
                                  client_secret="mitMmKkTn15WQSxIkiBTMzu3", offline=False, scope=["profile", "email"],
                                  redirect_url="store_user")  # After authentication, redirects to store_user page to save user information to DB

app.register_blueprint(blueprint, url_prefix="/login")  # Registers blueprint to application (adds Google login)

################################################################################################################
#                                            DATABASE TABLES                                                   #
################################################################################################################

class User(UserMixin, db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    g_id = db.Column(db.String(), unique=True, nullable=False)
    g_name = db.Column(db.String(20), unique=True, nullable=False)
    g_email = db.Column(db.String(128), unique=False, nullable=False)
    g_picture = db.Column(db.String(128))
    items = db.relationship('Item', backref='author', lazy='dynamic')

    def __repr__(self):
        return f"<User {self.g_name} , {self.g_email} , {self.items}>"


class Item(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer(), nullable=False)
    price = db.Column(db.Integer())
    category = db.Column(db.String())
    expiration_date = db.Column(db.DateTime(), nullable=False, default=datetime.now)
    description = db.Column(db.String(), nullable=False)
    pic_file = db.Column(db.String(), default="default_img.png")
    publish_date = db.Column(db.DateTime(), nullable=False, default=datetime.now)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return f"<Item {self.name} , {self.quantity} , {self.price} , {self.expiration_date} , {self.description} , {self.category} , {self.pic_file} , {self.publish_date}>"


class Transaction(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'))
    quantity = db.Column(db.Integer, nullable=False)
    buyer_description = db.Column(db.String)
    transaction_date = db.Column(db.DateTime(), nullable=False, default=datetime.now)

    def __repr__(self):
        return f"<{self.id}, Seller ID: {self.seller_id}, Buyer ID: {self.buyer_id}, Item ID: {self.item_id}, Date: {self.transaction_date}"


db.create_all()  # Initializes the database if it is not created

################################################################################################################
#                                                   FORMS                                                      #
################################################################################################################

class SellForm(FlaskForm):
    # Validators -> determines if the input data is valid based on some requirements

    name = StringField('Name of item(s)', validators=[DataRequired()])
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1, max=500)])
    price = IntegerField("Price (in Yen)", validators=[DataRequired()])
    category = RadioField("Category", choices=["Food", "Drink", "Clothes", "Tech", "Books", "Other"],
                          validators=[DataRequired()])
    expiration_date = DateField("Expiration Date", format="%Y-%m-%d")
    description = StringField("Description", validators=[length(max=200)])
    pic_file = FileField("Picture of item(s)", validators=[FileAllowed(["jpg", "jpeg", "png"], "Image files only")])

    submit = SubmitField('Publish Item')

    def validate_expiration_date(form, field):
        date = form.expiration_date.raw_data[0]
        print("Date:", date)
        if date == "":
            return

        if date[4] == "-":
            date = date.split("-")
        else:
            date = date.split("/")
        print(date)

        if len(date[0]) != 4 or len(date[1]) != 2 or len(date[2]) != 2:
            raise ValidationError("Please submit the date in the form 'YYYY-MM-DD'.")


class SearchForm(FlaskForm):
    search_term = StringField("Search:", render_kw={"placeholder": "Search"})
    sort = RadioField("Sort", default="New-Old", choices=["New-Old", "Old-New", "Price High-Low", "Price Low-High"])
    category = SelectField("Category sort", default="",
                           choices=[("All", "All"), ("Food", "Food"), ("Drink", "Drink"), ("Clothes", "Clothes"),
                                    ("Tech", "Tech"),
                                    ("Books", "Books"), ("Other", "Other")])
    submit = SubmitField("Search")


class PurchaseForm(FlaskForm):
    dynamic_quantity = SelectField("Quantity to purchase:", choices=[], validators=[DataRequired()], coerce=int)
    buyer_description = StringField("Message from buyer:")
    submit = SubmitField("Purchase")


################################################################################################################
#                                                  Routes                                                      #
################################################################################################################

@login_manager.user_loader  # Handles logins, connects a user ID to the current_user
def load_user(id):
    return User.query.get(int(id))


@app.route("/", methods=["POST", "GET"])  # Main page
def index():
    try:
        global resp
        resp = google.get("/oauth2/v1/userinfo")  # Communicates with the Google Authentication server
        resp = resp.json()  # resp is a list of user data (e.g. email, name, profile picture link etc.)

    except (InvalidGrantError, TokenExpiredError) as e:  # or maybe any OAuth2Error
        if google.authorized:
            logout_user()
        return redirect(url_for("google.login"))

    users = User.query.all()  # Passed to the website
    form = SearchForm()  # Links to search form

    category = "All"

    if form.validate_on_submit():  # When user clicks "search" this is True

        #################### STEP 1 - FILTER BASED ON SEARCH TERM ####################

        category = form.category.data
        print("Category:", category)
        search = form.search_term.data  # Gets search term
        s_items_name = Item.query.filter(
            Item.name.contains(search)).all()  # Queries NAMES of items that include search term returns list
        s_items_description = Item.query.filter(
            Item.description.contains(
                search)).all()  # Queries DESCRIPTIONS of items that includes search term, returns list

        # Creates new list, including all items from s_items_name and all items from s_items_descriptions that are not already there
        items = s_items_name + [i for i in s_items_description if i not in s_items_name]

        #################### STEP 2 - SORTING IN CORRECT ORDER ####################

        if len(items) not in [0, 1]:  # If search does not return results (no matches), this is not executed
            sort_type = form.sort.data  # Get sort option from form

            if sort_type == "New-Old":  # Time since published
                items = sort_high_low(items, len(items),
                                      "published_date")  # Sorts items with sort_high_low algorithm (see below)
            elif sort_type == "Old-New":
                items = sort_low_high(items, len(items), "published_date")  # Sorts items with sort_low_high algorithm
            elif sort_type == "Price High-Low":  # Price
                items = sort_high_low(items, len(items), "price")  # Sorts items with sort_high_low algorithm
            else:
                items = sort_low_high(items, len(items), "price")  # Sorts items with sort_low_high algorithm
    else:
        # Runs if form is not submitted yet, or page is refreshed

        # Handles exceptions if there are no items or only one item in store (in which case sorting will not happen)
        try:
            items = sort_high_low(Item.query.all(), len(Item.query.all()), "published_date")
        except:
            items = Item.query.all()  # Don't perform sorting

    # Renders template with the appropriate pre-processed variables
    return render_template("main.html", google=google, users=users, items=items, form=form, category=category,
                           current_date=datetime.now())


@app.route("/login/google/store_user")  # User redirected here after Google Auth.
def store_user():
    resp = google.get("/oauth2/v1/userinfo")  # Gets user info from Google server
    resp = resp.json()

    user = User.query.filter_by(g_id=resp["id"]).first()  # Check if user already exists in database

    if user:  # User already in database
        login_user(user)  # Built in method that registers that user as logged in
        return redirect(url_for("index"))  # Redirects to homepage
    else:  # User is new
        # Get Google user info
        g_id = resp["id"]
        g_email = resp["email"]
        g_name = resp["name"]
        g_picture = resp["picture"]

        user = User(g_id=g_id, g_email=g_email, g_name=g_name, g_picture=g_picture)  # Create new user object
        # Add and commit to DB
        db.session.add(user)
        db.session.commit()

        login_user(user)

        return redirect(url_for("index"))


@app.route("/login/google")
def login():
    if not google.authorized:
        return render_template(url_for("google.login"))  # Redirects to Google login page
    return redirect(url_for("index"))


@app.route('/logout')
def logout():
    token = blueprint.token["access_token"]
    # Communicates to Google that user is logged out
    resp = google.post(
        "https://accounts.google.com/o/oauth2/revoke",
        params={"token": token},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )

    logout_user()  # Delete Flask-Login's session cookie
    del blueprint.token  # Delete OAuth token from storage

    return redirect(url_for('index'))


@app.route("/sell", methods=["POST", "GET"])
@login_required
def sell():
    # if not google.authorized:
    #    return redirect(url_for("login"))

    form = SellForm()

    # Validating the sell form
    if form.validate_on_submit():
        # Handling errors if the user does not submit a file
        try:
            # Attempts to retrieve file data
            img = form.pic_file.data
            filename = secure_filename(img.filename) # Function from werkzeug library to ensure user input does not involve exploits
            filename = "u" + str(current_user.id) + "_" + filename # Create filename format
            img.save(os.path.join(os.getcwd(), "static", "item_pics", filename)) # Saves the file to the correct directory
        except:
            # If no file submitted:
            filename = None # A "None" filename will result in the default item image being used

        item = Item(name=form.name.data, quantity=form.quantity.data, price=form.price.data,
                    category=form.category.data,
                    expiration_date=form.expiration_date.data, description=form.description.data,
                    pic_file=filename,
                    user_id=current_user.id)

        db.session.add(item)
        db.session.commit()

        return redirect(url_for("index"))

    return render_template("sell.html", form=form, google=google)


@app.route("/profile")
@login_required
def profile():
    all_users = User.query.all()
    all_items = Item.query.all()
    current_user_items = Item.query.filter_by(user_id=current_user.id).all()
    transactions = Transaction.query.all()
    transactions = [transaction for transaction in transactions if
                    transaction.buyer_id == current_user.id or transaction.seller_id == current_user.id]

    return render_template("profile.html", google=google, all_users=all_users, current_user_items=current_user_items,
                           all_items=all_items, transactions=transactions, current_date=datetime.now())


@app.route("/item/<id>", methods=["POST", "GET"])
@login_required
def item_page(id):
    # Passed to the website
    item = Item.query.filter_by(id=id).first()
    user = User.query.filter_by(id=item.user_id).first()

    form = PurchaseForm()  # Links to purchase form

    form.dynamic_quantity.choices = [(i, i) for i in range(1, item.quantity + 1)]

    if form.validate_on_submit():  # When user clicks "purchase" this is True

        seller_id = item.user_id
        buyer_id = current_user.id
        item_id = item.id
        quantity = form.dynamic_quantity.data
        buyer_description = form.buyer_description.data

        transaction = Transaction(seller_id=seller_id, buyer_id=buyer_id, item_id=item_id, quantity=quantity,
                                  buyer_description=buyer_description)
        db.session.add(transaction)
        db.session.commit()

        item.quantity -= quantity

        # Render purchase confirmation screen

        return render_template("purchase_confirmation.html", google=google, user=user, item=item, quantity=quantity,
                               buyer_description=buyer_description, seller_id=seller_id)

    return render_template("item_page.html", google=google, user=user, item=item, form=form,
                           current_date=datetime.now())


################################################################################################################
#                                          Sorting algorithms                                                  #
################################################################################################################

def sort_low_high(items, n, metric):
    # Recursive insertion sort
    if n == 1:  # Base case
        return

    # Recursive call
    sort_low_high(items, n - 1, metric)

    last = items[n - 1]
    j = n - 2

    if metric == "price":  # If metric = price, the price attribute of items[j] is compared
        while j >= 0 and items[j].price > last.price:
            items[j + 1] = items[j]
            j -= 1
    elif metric == "published_date":  # If metric = published date, the published date attribute of items[j] is compared
        while j >= 0 and items[j].publish_date > last.publish_date:
            items[j + 1] = items[j]
            j -= 1
    else:
        raise Exception("Wrong metric input")  # For debugging: if wrong metric is passed into the function

    items[j + 1] = last

    return items  # Finally, return item list


def sort_high_low(items, n, metric):  # Returns the reversed the sort_low_high output list
    return reversed(sort_low_high(items, n, metric))


################################################################################################################
#                                    Secure filename algorithms                                                #
################################################################################################################

def secure_filename(filename):
    filename = list(filename) # Convert string to list
    illegal_characters = list("{}[]()%$#!/&=?+*^.") # Which characters to exclude
    last_period_ind = None # Storing the index

    # Looping through characters in filename
    for i in range(len(filename)):
        wrong_char = False # Starts each iteration assuming the char is valid
        for j in range(len(illegal_characters)): # Looping through the illegal char list
            if filename[i] == illegal_characters[j]: # Check if the filename is invalid
                wrong_char = True
                break # Stop checking illegal characters

        if wrong_char: # If the char is invalid...
            if filename[i] == ".": # Checks if the char is a "." to keep track of the last one (which is a part of the .png or .jpg)
                last_period_ind = i
            filename[i] = "_" # Replace the old

    if last_period_ind: # if a period is found
        filename[last_period_ind] = "." # Replace the last found period index with a "."
        return "".join(filename) # Convert the list of characters back to string
    else:
        # Runs if no period found - then it must be invalid
        return "default_img.png"


################################################################################################################
#                                         Main application                                                     #
################################################################################################################

if __name__ == "__main__":
    app.run(debug=True)
