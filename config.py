from flask import Flask

import os
from dotenv import load_dotenv
project_folder = os.path.expanduser('~/domco_app')
load_dotenv(os.path.join(project_folder, '.env'))

app = Flask(__name__)




app.config["MAIL_USERNAME"] = os.getenv('MAIL_USERNAME')
app.config["MAIL_PASSWORD"] = os.getenv('MAIL_PASSWORD')
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 25
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_ASCII_ATTACHMENTS"] = True
app.config["MAIL_SENDER"] = os.getenv('MAIL_USERNAME')

app.config["EXPLAIN_TEMPLATE_LOADING"] = True

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv('SQLALCHEMY_DATABASE_URI')
app.config["SQLALCHEMY_POOL_RECYCLE"] = 299
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


app.config['CKEDITOR_PKG_TYPE'] = 'standard'
app.config['SECURITY_RECOVERABLE'] = True

app.secret_key = os.getenv('SECRET_KEY')
app.jinja_env.filters['zip'] = zip


