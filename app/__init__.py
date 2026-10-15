import getpass
import os
import sqlite3
from flask import Flask, abort, flash, redirect, session, url_for
from werkzeug.security import generate_password_hash
from .common import money, page
from .db import db, init_db
from .auth import auth
from .booking import booking
from .service import service
from .invoices import invoices


def create_app():
    application = Flask(__name__)
    application.secret_key = os.environ.get('SECRET_KEY', 'dev-only-change-me')
    application.config['DATABASE'] = os.environ.get('DATABASE_PATH', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'service.db'))
    application.jinja_env.globals['money'] = money
    application.register_blueprint(auth)
    application.register_blueprint(booking)
    application.register_blueprint(service)
    application.register_blueprint(invoices)

    @application.route('/')
    def home():
        if not session.get('user_id'):
            return redirect(url_for('auth.login'))
        if session['role'] == 'admin':
            return redirect(url_for('service.admin_appointments'))
        return redirect(url_for('booking.customer_home'))

    @application.errorhandler(403)
    def forbidden(error):
        return page('Forbidden', '<h1>Access denied</h1><p>You are not authorized to view this page.</p>'), 403

    @application.cli.command('init-db')
    def init_db_command():
        init_db(application)
        print('Database initialized.')

    @application.cli.command('create-admin')
    def create_admin_command():
        init_db(application)
        name = input('Admin name: ').strip()
        email = input('Admin email: ').strip()
        password = getpass.getpass('Password (8+ chars): ')
        if len(password) < 8:
            print('Password must be at least 8 characters.')
            return
        with application.app_context():
            connection = db()
            try:
                connection.execute('INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,"admin")', (name, email, generate_password_hash(password)))
                connection.commit()
                print('Admin created.')
            except sqlite3.IntegrityError:
                print('That email already exists.')
            finally:
                connection.close()

    return application

app = create_app()
