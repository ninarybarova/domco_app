# -*- coding: utf-8 -*-
from flask import render_template,url_for, request, redirect, session, flash,make_response
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from flask_mail import Mail, Message
from sqlalchemy import desc
from flask_ckeditor import CKEditor
from flask_wtf.csrf import CSRFProtect
from datetime import datetime
from itsdangerous import URLSafeTimedSerializer
from forms import EmailForm, PasswordForm, LoginForm
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from config import app
from model import User, Offer, Customer, Drive, Address, Product, db

import pdfkit
import locale
import os
import time

mail = Mail(app)

csrf = CSRFProtect(app)
ckeditor = CKEditor(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = u"Pred pokračovaním sa prosím prihláste."


os.environ["TZ"] = "Europe/Bratislava"
time.tzset()
locale.setlocale(locale.LC_ALL, 'sk_SK')


project_folder = os.path.expanduser('~/domco_bc')
PDFKIT_CONFIGURATION = pdfkit.configuration(wkhtmltopdf= os.path.join(project_folder, 'wkhtml-install/usr/local/bin/wkhtmltopdf'))
PDF_NAME = "domco_cenova_ponuka.pdf"
ITEMS_PER_PAGE = 5



"""
    A callback used to reload the user object
    Code is sourced from Real Python
    Available from: https://realpython.com/using-flask-login-for-user-management-with-flask/#the-user_loader
"""
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)



@app.route("/login", methods = ["POST", "GET"])
def login():

    form = LoginForm()
    if form.validate_on_submit():

        username = form.username.data
        password = form.password.data

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):

            login_user(user, remember=True)
            return redirect("/")

        flash("Nesprávne meno alebo heslo")
        return redirect("/login")

    return render_template("login.html", form=form)


@app.route("/logout")
@login_required
def logout():

    logout_user()

    return redirect("/login")


@app.route("/", methods =["POST","GET"])
@app.route("/home", methods =["POST","GET"])
@login_required
def index():

    if request.method == "POST":

        try:
            offer, files = createOffer(request)
            addProducts(request, offer.id)
        except:
            flash("Cenovú ponuku sa nepodarilo vytvoriť")
            raise

        products = Product.query.filter_by(offer_id=offer.id).all()
        if products:
            calculated_prices, price = calculate_price(products)

            rendered_template = render_template("pdf_price_offer.html", offer=offer, products=products, price = price, calculated_prices = calculated_prices)
            pdf = pdfkit.from_string(rendered_template, False, configuration=PDFKIT_CONFIGURATION)
            html = render_template('email_body.html', customer = offer.customer)
            send_email("Domco s.r.o. - cenová ponuka", [current_user.email, offer.customer.email], html, pdf, offer.id, files)

            flash("Cenová ponuka bola úspešne poslaná")
        return redirect("/")


    page = get_session_argument(request, 'page', 1)
    state = get_session_argument(request, 'state', 0)
    drives = Drive.query.all()

    states = [{'page':1,'filter':(lambda q: q)},
                {'page':1,'filter':(lambda q: q.filter_by(state="SVK"))},
                {'page':1,'filter':(lambda q: q.filter_by(state="CZ"))},
                {'page':1,'filter':(lambda q: q.filter_by(state="AT"))}]

    states[state]["page"] = page
    query = Offer.query.order_by(desc(Offer.date_of_creation))
    offers = [state["filter"](query).paginate(page=state["page"], per_page=ITEMS_PER_PAGE, error_out=False) for state in states]


    return render_template("index.html", svk_offers = offers[1], cz_offers = offers[2],
                            at_offers = offers[3], all_offers = offers[0],
                            drives = drives, state = state)


def get_session_argument(request, arg, default_value):

    if session.get(arg, None) is None and request is not None:
        return request.args.get(arg, default_value, type=int)

    result = session.get(arg, None)
    session.pop(arg, default=None)

    return result


def calculate_price(products):

    calculated_prices = []
    final_price = 0
    for product in products:
        p_dict = {}
        if product is not None:
            total_no_vat = round(product.height * product.area * product.unit_price * ((100 - product.discount) /100), 2)
            total_vat = round((1+(product.vat/100))* total_no_vat, 2)
            amount_of_discount = round(product.height * product.area * product.unit_price * (product.discount/100), 2)
            final_price += total_vat
        else:
            total_no_vat = ""
            total_vat = ""
            amount_of_discount = ""
        p_dict["total_no_vat"] = total_no_vat
        p_dict["total_vat"] = total_vat
        p_dict["amount_of_discount"] = amount_of_discount
        calculated_prices.append(p_dict)

    return calculated_prices, final_price


def add_item_to_db(item):
    try:
        db.session.add(item)
        db.session.commit()
    except:
        db.session.rollback()
        raise


def addProducts(request, offer_id):

    for num in range(5):
        row = "priceOfferRows[{}].".format(num)

        name = request.form[row + "name"]
        if name == "Vyberte":
            continue

        height= request.form[row + "height"]
        area = request.form[row + "area"]
        discount = request.form[row + "discount"]
        unit_price= request.form[row + "unitPrice"]
        vat = request.form[row + "vat"]

        new_product= Product(name=name,
                            offer_id = offer_id,
                            height=height,
                            area=area,
                            discount = discount,
                            unit_price = unit_price,
                            vat = vat)

        add_item_to_db(new_product)


def createOffer(request):

    state = request.form["state"].upper()
    name = request.form["name"]
    last_name = request.form["surname"]
    city = request.form["city"]
    street = request.form["street"]
    zipcode = request.form["zipcode"]
    email = request.form["email"]
    phone_number = request.form["phone_number"]
    organization = request.form["organization"]
    realization_date = request.form["realization_date"]
    other_street = request.form["object_street"]
    other_city = request.form["object_city"]
    other_zipcode = request.form["object_zipcode"]
    user = User.query.filter_by(username = request.form["assign"]).first()
    user_id = user.id
    state_of_offer = request.form["status"]
    user_notes = request.form.get("user_notes")
    offer_notes = request.form.get("offer_notes")
    files = request.files.getlist("file")


    if all((item.filename != '') for item in files):
        for file in files:
            file.save(os.path.join(app.root_path, 'uploads_user', secure_filename(file.filename) ))
    else:
        files = []

    customer = Customer.query.filter_by(name = name, surname = last_name,
                                        email = email, phone_number = phone_number).first()
    if customer is None:

        customer_address = Address(city = city, street = street,
                            zipcode = zipcode, state = state)
        add_item_to_db(customer_address)

        customer = Customer(name = name, surname = last_name,
                            email = email, phone_number = phone_number,
                            organization = organization, address_id = customer_address.id)
        add_item_to_db(customer)
    else:
        customer.address.city = city
        customer.address.street = street
        customer.address.zipcode = zipcode
        customer.address.state = state

        flash('Pre tohto zákazníka už bola v minulosti vypracovaná cenová ponuka.')
        try:
            db.session.commit()
        except:
            db.session.rollback()
            raise


    # if the object address is not stated, the object address is the same as customer address
    if other_street == "":
        offer_address = Address(city = customer.address.city, street = customer.address.street,
                            zipcode = customer.address.zipcode, state = state)
    else:
        offer_address = Address(city = other_city, street = other_street,
                            zipcode = other_zipcode, state = state)
    add_item_to_db(offer_address)

    offer = Offer(user_id = user_id, customer_id = customer.id, state = state,
                date_of_realization = realization_date, status=state_of_offer,
                user_notes = user_notes, offer_notes = offer_notes, address_id = offer_address.id)
    add_item_to_db(offer)

    return (offer, files)


"""
    Updating a price offer
"""

def update_offer(request, offer):
    original_date_of_realization = offer.date_of_realization

    #update user
    offer.date_of_realization = request.form["realization_date"]
    offer.status = request.form["status"]
    offer.user_notes = request.form.get("user_notes")
    offer.offer_notes = request.form.get("offer_notes")
    user = User.query.filter_by(username = request.form["assign"]).first()
    offer.user_id = user.id


    #update customer
    customer = Customer.query.filter_by(id = offer.customer_id).first()
    customer.name = request.form["name"]
    customer.surname = request.form["surname"]
    customer.email = request.form["email"]
    customer.phone_number = request.form["phone_number"]
    customer.organization = request.form["organization"]
    customer.address.city = request.form["city"]
    customer.address.street = request.form["street"]
    customer.address.zipcode = request.form["zipcode"]


    #update user address
    object_city = request.form["object_city"]
    object_street = request.form["object_street"]
    object_zipcode = request.form["object_zipcode"]

    offer.address.city = object_city if object_city else customer.address.city
    offer.address.street = object_street if object_street else customer.address.street
    offer.address.zipcode = object_zipcode if object_zipcode else customer.address.zipcode


    if original_date_of_realization != offer.date_of_realization:
        drives = Drive.query.filter_by(offer_id = offer.id).all()
        date = offer.date_of_realization.split("-")
        for d in drives:

            #delete car drive if the car is not available for new date of realization
            if duplicite_drive(date, d.car_id):
                message = "Auto {}  nie je dostupné pre tento dátum. Jazda bola odstránená.".format(d.car_id)
                flash(message)

                try:
                    db.session.delete(d)
                    db.session.commit()
                except:
                    db.session.rollback()
                continue

            #update date in car drive
            d.date = datetime(int(date[2]), int(date[1]), int(date[0]))

    try:
        db.session.commit()
    except:
        db.session.rollback()
        raise


def update_products(request, products_all, id):

    for num, product in enumerate(products_all):
        row = "priceOfferRows[{}].".format(num)
        product_name = request.form[row + "name"]

        if product and product_name == "Vyberte":
            try:
                db.session.delete(product)
                db.session.commit()
                product = None
            except:
                db.session.rollback()
                raise

        if not product and product_name != "Vyberte":
            product = Product(offer_id=id)

        if product:
            product.name = request.form[row + "name"]
            product.height = request.form[row + "height"]
            product.discount = request.form[row + "discount"]
            product.area = request.form[row + "area"]
            product.unit_price = request.form[row + "unitPrice"]
            product.vat = request.form[row + "vat"]

            add_item_to_db(product)


@app.route("/update/<int:id>", methods = ["POST","GET"])
@login_required
def update(id):

    offer = Offer.query.get_or_404(id)
    users = User.query.order_by(User.username).all()
    products = Product.query.filter_by(offer_id=id).all()
    products_all = products + [None] * (5 - len(products))

    if offer.user_id == current_user.id or current_user.admin:
        if request.method == "POST":
            update_offer(request, offer)
            update_products(request, products_all, id)

            products = Product.query.filter_by(offer_id=id).all()
            products_all = products + [None] * (5 - len(products))
            calculated_prices, _ = calculate_price(products_all)

            return render_template("update.html", users = users, products_all = products_all,
                                                offer=offer, calculated_prices = calculated_prices)

        calculated_prices, _ = calculate_price(products_all)

        return render_template("update.html", users = users, products_all = products_all,
                                            offer=offer, calculated_prices = calculated_prices)

    flash("Nemáte prístup k tejto akcii")
    return redirect("/")


@app.route("/deleteoffer", methods = ["POST", "GET"])
@login_required
def delete_offer():

    data = request.get_json()
    offer_id = data[0]["id"]
    offer = Offer.query.get_or_404(offer_id)

    session['page'] = data[1]["page"]
    session['state'] = data[2]["state"]


    if current_user.admin or offer.user_id == current_user.id and request.method == "POST":

        customer_address = offer.customer.address

        try:
            if len(offer.customer.orders) == 1:
                db.session.delete(offer.customer)
                db.session.delete(customer_address)
            db.session.delete(offer.address)
            db.session.delete(offer)

            db.session.commit()
        except:
            db.session.rollback()
            raise
    else:

        flash("Nemáte prístup k tejto akcii")


"""
    Confirm a price offer
"""

@app.route("/confirmoffer", methods = ["POST", "GET"])
@login_required
def confirm_offer():

    data = request.get_json()
    offer_id = data[0]["id"]
    offer = Offer.query.get_or_404(offer_id)

    session['page'] = data[1]["page"]
    session['state'] = data[2]["state"]

    if current_user.admin or offer.user_id == current_user.id and request.method == "POST":

        status = offer.status
        offer.status = "Nová objednávka" if status == "Potvrdené" else "Potvrdené"
        try:
            db.session.commit()
        except:
            db.session.rollback()
            raise
    else:
        flash("Nemáte prístup k tejto akcii")


@app.route("/confirmed_offers")
@login_required
def confirmed_offers():

    # 0 = all, 1 = svk, 2 = cz, 3 = at
    page = request.args.get("page", 1, type=int)
    state = request.args.get("state", 0, type=int)
    drives = Drive.query.all()

    states = [{'page':1,'filter':(lambda q: q.filter_by(status="Potvrdené"))},
                {'page':1,'filter':(lambda q: q.filter_by(state="SVK", status="Potvrdené"))},
                {'page':1,'filter':(lambda q: q.filter_by(state="CZ", status="Potvrdené"))},
                {'page':1,'filter':(lambda q: q.filter_by(state="AT", status="Potvrdené"))}]


    states[state]["page"] = page
    query = Offer.query.order_by(desc(Offer.date_of_creation))
    offers = [state["filter"](query).paginate(page=state["page"], per_page=ITEMS_PER_PAGE, error_out=False) for state in states]


    return render_template("price_offers.html",
            svk_offers = offers[1], cz_offers = offers[2], at_offers = offers[3],
            all_offers = offers[0], drives = drives, state = state)


"""
    Display a form for a new price offer
"""

@app.route("/orders/<state>")
@login_required
def orders(state):
    users = User.query.order_by(User.username).all()

    return render_template("new_offer.html", state=state, users = users)


"""
    Display a price offer
"""

@app.route("/pdf/<int:id>")
@login_required
def pdf_template(id):


    offer = Offer.query.get_or_404(id)
    products = Product.query.filter_by(offer_id=id).all()
    calculated_prices, price = calculate_price(products)

    rendered_template = render_template("pdf_price_offer.html", offer=offer, products=products, price = price, calculated_prices = calculated_prices)
    pdf = pdfkit.from_string(rendered_template, False, configuration=PDFKIT_CONFIGURATION)

    response = make_response(pdf)
    response.headers["Content-Type"] ="application/pdf"
    response.headers["Content-Disposition"] = "inline; filename=domco_cenova_ponuka.pdf"

    return response


"""
    Display a profile
"""
@app.route("/profile")
@login_required
def profile():

    return render_template("profile.html")


@app.route("/newpassword",methods=["POST","GET"])
@login_required
def newpassword():


    if request.method =="POST":
        pswd1 = request.form["pswd1"]
        pswd2 = request.form["pswd2"]

        if pswd1 =="" or pswd2 =="":
            flash("Uveďte nové heslo")

            return render_template("newpassword.html")
        elif pswd1 != pswd2:
            flash("Heslá nie sú zhodné")

            return render_template("newpassword.html")
        elif check_password_hash(current_user.password, pswd1):
            flash("Nemožno použiť terajšie heslo")

            return render_template("newpassword.html")
        elif pswd1 == pswd2:

            current_user.password = generate_password_hash(pswd1)
            try:
                db.session.commit()
            except:
                db.session.rollback()
                raise
        return render_template("profile.html")

    return render_template("newpassword.html")


@app.route("/newdata",methods=["POST","GET"])
@login_required
def newdata():

    if request.method =="POST":
        user = User.query.filter_by(username= current_user.username).first()
        user.email = request.form["email"]
        try:
            db.session.commit()
        except:
            db.session.rollback()
            raise
        return render_template("profile.html")

    return render_template("newdata.html")


@app.route("/users",methods=["POST","GET"])
@login_required
def users():

    return add_user(False, request)


@app.route("/admins",methods=["POST","GET"])
@login_required
def admins():

    return add_user(True, request)


def add_user(is_admin, request):

    if current_user.admin is True:
        page = request.args.get("page",1, type=int)
        users = User.query.filter_by(admin=is_admin).order_by(User.username).paginate(page=page,per_page=ITEMS_PER_PAGE, error_out=False)

        if request.method == "POST":
            newusername = request.form["newusername"]
            newemail = request.form["newemail"]
            newpassword = request.form["newpassword"]

            newuser = User(username=newusername, email=newemail, password=generate_password_hash(newpassword), admin = is_admin)

            try:
                add_item_to_db(newuser)
            except:

                flash("Užívateľské meno, email alebo heslo sa zhoduje s iným užívateľom.")
                if is_admin:
                    return redirect("/admins")
                return redirect("/users")

            users = User.query.filter_by(admin=is_admin).order_by(User.username).paginate(page=page,per_page=ITEMS_PER_PAGE, error_out=False)

        if is_admin:
            return render_template("admins.html",admins=users)
        return render_template("users.html",users=users)

    flash("Nemáte prístup k tejto akcii")
    return redirect("/")


@app.route("/delete/user/<int:id>")
@login_required
def delete_user(id):

    user_to_delete = User.query.get_or_404(id)

    if current_user.id == id or user_to_delete.username == "Admin":
        flash("Neplatná akcia")
        return redirect("/")

    page = request.args.get("page",1, type=int)

    if current_user.admin:

        #move user's drives and offers to current user
        Drive.query.filter_by(user_id = id).update(dict(user_id=current_user.id))
        Offer.query.filter_by(user_id = id).update(dict(user_id=current_user.id))

        try:
            db.session.delete(user_to_delete)
            db.session.commit()
        except:
            db.session.rollback()
            raise

        users = User.query.filter_by(admin=user_to_delete.admin).order_by(User.username).paginate(page=page,per_page=ITEMS_PER_PAGE, error_out=False)

        if user_to_delete.admin:
            return render_template("admins.html",admins=users)
        return render_template("users.html",users=users)


@app.route("/update/user/<int:id>",methods=["GET","POST"])
@login_required
def updateuser(id):

    if current_user.admin:

        user = User.query.get_or_404(id)

        if request.method == "POST":
            user.username = request.form["username"]
            user.email = request.form["email"]

            try:
                db.session.commit()
            except:
                db.session.rollback()
                raise

            return redirect("/users")

        return render_template("update_user.html",user=user)

    flash("Nemáte prístup k tejto akcii")
    return redirect("/")


"""
    Code for send_reset_email() and reset_with_token() functions is sourced from the flask-app-blueprint project
    Available from github: https://github.com/jelmerdejong/flask-app-blueprint/blob/3e47d083a2d0566a6d9d150729213abcbda196b3/project/users/views.py
"""

def send_reset_email(user_email):

    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    password_reset_url = url_for(
        'reset_with_token',
        token = serializer.dumps(user_email, salt='secret-password-reset-salt'),
        _external=True)


    html = render_template('password_reset_email.html', link=password_reset_url)
    send_email(subject='Zmena hesla Domco s.r.o.', recipients=[user_email],
                html=html, pdf=None, offer_id=None, files=[])


@app.route('/reset/<token>', methods=["GET", "POST"])
def reset_with_token(token):

    try:
        serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
        email = serializer.loads(token, salt='secret-password-reset-salt', max_age=3600)
    except:
        flash('Link na zmenu hesla vypršal. Skúste znova.', 'error')
        return redirect(url_for('login'))

    form = PasswordForm()
    if form.validate_on_submit():
        try:
            user = User.query.filter_by(email=email).first_or_404()
        except:
            flash('Neplatná emailová adresa', 'error')
            return redirect(url_for('login'))

        user.password = generate_password_hash(form.password.data)
        try:
            db.session.commit()
        except:
            db.session.rollback()
            raise

        flash('Vaše heslo bolo zmenené', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password_token.html', form=form, token=token)


@app.route('/reset', methods=["GET", "POST"])
def reset():

    form = EmailForm()
    if form.validate_on_submit():

        try:
            user = User.query.filter_by(email=form.email.data).first_or_404()
        except:
            flash('Neplatná emailová adresa')
            return render_template('password_reset.html', form=form)

        send_reset_email(user.email)

        flash('Link na zmenu hesla bol odoslaný na Váš email')
        return redirect(url_for('login'))

    return render_template('password_reset.html', form=form)


"""
    Send emails with a price offer
"""

def send_email(subject, recipients, html, pdf, offer_id, files):
    msg = Message()
    msg.subject = subject
    msg.recipients = recipients
    msg.html = html
    msg.sender = app.config["MAIL_SENDER"]

    if pdf:
        msg.attach(PDF_NAME, "application/pdf", pdf)

    for file in files:
        filename = secure_filename(file.filename)
        with app.open_resource("uploads_user/" + filename) as fp:
            msg.attach(filename, 'text/plain', fp.read())

    attach_certificates(msg, offer_id)
    mail.send(msg)


def attach_certificates(msg, offer_id):

    certificates = {'EcoPura_4000' : 'Technický_list_SFI_4000.pdf', 'EcoPura_5000' : 'Technický_list_SFI_5000.pdf'}

    if Product.query.filter_by(offer_id = offer_id, name ="EcoPura SFI4000").first():
        with app.open_resource("uploads/tech__SFI_4000.pdf") as fp:
            msg.attach(certificates["EcoPura_4000"], "application/pdf", fp.read())

    if Product.query.filter_by(offer_id = offer_id, name ="EcoPura SFI5000").first():
        with app.open_resource("uploads/tech_SFI_5000.pdf") as fp:
            msg.attach(certificates["EcoPura_5000"], "application/pdf", fp.read())


@app.route("/send/offer/<int:id>", methods = ["POST", "GET"])
@login_required
def send_basic(id):

    if request.method == "POST":
        offer = Offer.query.get_or_404(id)
        products = Product.query.filter_by(offer_id=id).all()
        calculated_prices, price = calculate_price(products)

        offer_files = request.files.getlist("file")
        if all((item.filename != '') for item in offer_files):
            for file in offer_files:
                file.save(os.path.join(app.root_path, 'uploads_user', secure_filename(file.filename) ))
        else:
            offer_files = []

        rendered_template = render_template("pdf_price_offer.html", offer=offer, products=products, price = price, calculated_prices = calculated_prices)
        pdf = pdfkit.from_string(rendered_template, False, configuration=PDFKIT_CONFIGURATION)
        html = render_template('email_body.html', customer = offer.customer)

        send_email("Domco s.r.o. - cenová ponuka", [offer.customer.email, current_user.email], html, pdf, offer.id, offer_files)

        flash("Cenová ponuka bola úspešne poslaná")
        return redirect("/")

    flash("Nemožno poslať cenovú ponuku")
    return redirect("/")


"""
    Search for a price offer
"""

def filter_customers(name, surname):

    if name and surname:
        return Customer.query.filter_by(name = name, surname = surname).all()
    elif name:
        return Customer.query.filter_by(name = name).all()
    elif surname:
        return Customer.query.filter_by(surname = surname).all()

    return []


def get_searched_offers(name, surname, city, page):

    customers = filter_customers(name, surname)
    customers_ids = [c.id for c in customers]

    if customers_ids:
        offers = Offer.query.filter(Offer.customer_id.in_(customers_ids))
    else:
        offers = Offer.query

    if city:
        addresses = Address.query.filter_by(city = city).all()
        city_ids = [a.id for a in addresses]
        offers = offers.filter(Offer.address_id.in_(city_ids))

    return offers.order_by(desc(Offer.date_of_creation)).paginate(page=page, per_page=ITEMS_PER_PAGE, error_out=False)


@app.route("/searchcustomer",methods=["POST","GET"])
@login_required
def search():

    if request.method == "POST":
        name= request.form["searchname"]
        surname = request.form["searchsurname"]
        city  = request.form["searchcity"]

    else:
        name= request.args.get("name","", type=str)
        surname = request.args.get("surname","", type=str)
        city  = request.args.get("city","", type=str)

    drives = Drive.query.all()
    page = request.args.get("page",1, type=int)
    offers = get_searched_offers(name, surname, city, page)

    return render_template("search.html", offers= offers, name= name, surname=surname, city=city, drives = drives)

"""
    Calendar and car drives
"""

@app.route("/calendar")
@login_required
def calendar():

    session.pop('year', None)
    session.pop('month', None)

    return redirect(url_for("drives"))


@app.route("/drives", methods =["POST","GET"])
@login_required
def drives():

    drives = Drive.query.all()
    today = datetime.now()

    year = session.get('year', today.year)
    month = session.get('month', today.month)

    json_drives = []
    for drive in drives:
        json_drive = {}
        json_drive['id'] = drive.id
        json_drive['user_id'] = drive.user_id
        json_drive['offer_id'] = drive.offer_id
        json_drive['car_id'] = drive.car_id
        json_drive['day'] = drive.date.strftime("%d")
        json_drive['month'] = drive.date.strftime("%m")
        json_drive['year'] = drive.date.strftime("%Y")
        json_drive['curr_user_id'] = current_user.id
        json_drive['admin'] = current_user.admin
        json_drive['can_delete'] = current_user.id == drive.user_id
        json_drives.append(json_drive)

    date = {"year": year, "month" : month}

    return render_template("drives.html", drives = json_drives, displayed_date = date)


def duplicite_drive(date, car_id):

    d = datetime(int(date[2]), int(date[1]), int(date[0])).date()

    return Drive.query.filter_by(car_id = car_id, date = d).first()


@app.route('/adddrive/<int:offer_id>/<int:car_id>/<int:page>/<int:state>', methods=['POST', 'GET'])
@login_required
def add_drive_to_offer(offer_id, car_id, page, state):
    offer = Offer.query.get_or_404(offer_id)
    date = offer.date_of_realization.split("-")
    same_drive = Drive.query.filter_by(offer_id = offer.id, car_id = car_id).first()

    if not current_user.admin and current_user.id != offer.user_id:
        flash('Nemáte prístup k tejto akcii')
        return redirect(url_for("confirmed_offers", page=page, state=state))

    if not offer.date_of_realization:
        flash('Najskôr zadajte dátum realizácie do objednávky')
        return redirect(url_for("confirmed_offers", page=page, state=state))


    if duplicite_drive(date, car_id) and not same_drive:
        flash('Auto nie je dostupné pre tento dátum')
        return redirect(url_for("confirmed_offers", page=page, state=state))


    same_drive = Drive.query.filter_by(offer_id = offer.id, car_id = car_id).first()
    if same_drive:
        try:
            db.session.delete(same_drive)
            db.session.commit()
        except:
            db.session.rollback()
            raise
        flash('Jazda bola úspešne vymazaná.')
        return redirect(url_for("confirmed_offers", page=page, state=state))


    drive = Drive(car_id = car_id, user_id = current_user.id, date = datetime(int(date[2]), int(date[1]), int(date[0])), offer_id = offer.id)
    add_item_to_db(drive)

    return redirect(url_for("confirmed_offers", page=page, state=state))


@app.route('/removedrive', methods=['POST', 'GET'])
@login_required
def removedrive():

    if request.method == "POST":
        data = request.get_json()
        drive_id = data[0]["id"]
        session['year'] = data[2]["year"]
        session['month'] = data[1]["month"]

        drive_to_delete = Drive.query.get_or_404(drive_id)

        try:
            db.session.delete(drive_to_delete)
            db.session.commit()
        except:
            db.session.rollback()
            raise


@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html'), 500


@app.errorhandler(502)
def bad_gateway_error(e):
    return render_template('error.html'), 502


with app.app_context():
    db.create_all()

