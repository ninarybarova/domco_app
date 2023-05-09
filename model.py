from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from config import app

db = SQLAlchemy(app)


"""
    model class representing a user
"""
class User(UserMixin,db.Model):
    id = db.Column(db.Integer, primary_key = True, autoincrement=True)
    username = db.Column(db.String(100), unique = True)
    password = db.Column(db.String(100))
    email = db.Column(db.String(100),unique = True)
    admin = db.Column(db.Boolean(), default=False)

    offers = db.relationship('Offer', backref='user')



"""
    model class representing a customer
"""
class Customer(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key= True, autoincrement=True)
    address_id = db.Column(db.Integer, db.ForeignKey('address.id'))
    name = db.Column(db.String(100), nullable = False)
    surname = db.Column(db.String(100),nullable = False)
    email = db.Column(db.String(100),  nullable=False)
    phone_number = db.Column(db.String(100), nullable = False)
    organization = db.Column(db.String(100))

    orders = db.relationship('Offer', backref='customer')

"""
    model class representing an address
"""
class Address(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key= True, autoincrement=True)
    city = db.Column(db.String(100))
    street = db.Column(db.String(100))
    zipcode= db.Column(db.String(20))
    state = db.Column(db.String(20))

    customer_address = db.relationship('Customer', backref='address')
    offer_address = db.relationship('Offer', backref='address')

"""
    model class representing a price offer
"""
class Offer(db.Model):
    id = db.Column(db.Integer, primary_key= True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    address_id = db.Column(db.Integer, db.ForeignKey('address.id'))
    state = db.Column(db.String(20), nullable = False)
    date_of_creation = db.Column(db.DateTime, default = datetime.now)
    status = db.Column(db.String(200),nullable= False)
    date_of_realization = db.Column(db.String(100), nullable=True)
    user_notes = db.Column(db.Text)
    offer_notes = db.Column(db.Text)


"""
    model class representing a product
"""
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    offer_id = db.Column(db.Integer, db.ForeignKey('offer.id'))
    name = db.Column(db.String(100))
    height = db.Column(db.Float)
    area = db.Column(db.Float)
    unit_price= db.Column(db.Float)
    discount = db.Column(db.Float)
    vat = db.Column(db.String(200))


"""
    model class representing a car drive
"""
class Drive(db.Model):
    id = db.Column(db.Integer, primary_key = True, autoincrement=True)
    date = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    car_id = db.Column(db.Integer, db.ForeignKey('car.id'))
    offer_id = db.Column(db.Integer, db.ForeignKey('offer.id'))


"""
    model class representing a car
"""
class Car(db.Model):
    id = db.Column(db.Integer, primary_key = True, autoincrement=True)

