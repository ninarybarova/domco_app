# -*- coding: utf-8 -*-
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional


class EmailForm(FlaskForm):
    email = StringField(
        'Email',
        validators=[
            DataRequired(),
            Email(),
            Length(min=6, max=40)]
        )
    submit = SubmitField("Potvrdiť a odoslať")


class PasswordForm(FlaskForm):
    password = PasswordField('Heslo', validators=[DataRequired()])
    submit = SubmitField("Uložiť")


class LoginForm(FlaskForm):

    username = StringField(
        'Užívateľské meno',
        validators=[
            DataRequired()
        ]
    )
    password = PasswordField(
        'Heslo',
        validators=[DataRequired()])
    submit = SubmitField('Prihlásiť sa')


class ConfigForm(FlaskForm):
    conf1 = StringField('Config 1', validators = [DataRequired()])
    conf2 = StringField('Config 2', validators = [DataRequired()])
    confirm = BooleanField('Potvrdiť')
    submit = SubmitField('Submit')