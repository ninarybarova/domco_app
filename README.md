# DOMCO application

This application was developed using the Python-Flask framework. 

It is designed to manage price offers for a company that specializes in house insulation. The application allows users to create and send price offers to customers and contains other functional parts specified by the company.

## Configuration

To ensure the proper functioning of the application, it is important to configure the correct parameters in the _.env_ file:

- MAIL_USERNAME and MAIL_PASSWORD variables correspond to the username and password of the email account used for sending emails
- SQLALCHEMY_DATABASE_URI variable specifies the string used by the application to establish a connection with the database
- SECRET_KEY variable is set to a value that is kept secret and cannot be guessed or shared

## Database
The _domco-database.sql_ file contains a script that creates the database used by the application. To copy the schema from the file into the database, run the following command:
```sh
source domco-database.sql
```

## Getting started
To access the application, login credentials with the username _Admin_ and password _admin_ can be used. 
