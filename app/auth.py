
import sqlite3
from flask import Blueprint, flash, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from .common import page
from .db import db

auth = Blueprint('auth', __name__)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        if not name or not email or len(password) < 8:
            flash('Enter your name, a valid email and password (at least 8 characters).')
        else:
            connection = db()
            try:
                connection.execute('INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)', (name, email, generate_password_hash(password), 'customer'))
                connection.commit()
                flash('Registration complete. Please log in.')
                return redirect(url_for('auth.login'))
            except sqlite3.IntegrityError:
                flash('An account with that email already exists.')
            finally:
                connection.close()
    return page('Register', '''<h1>Customer registration</h1><form method="post"><label>Name</label><input class="form-control" name="name" required><label>Email</label><input class="form-control" type="email" name="email" required><label>Password (8+ characters)</label><input class="form-control" type="password" name="password" minlength="8" required><button class="btn btn-primary mt-3">Register</button></form>''')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        connection = db()
        user = connection.execute('SELECT * FROM users WHERE email=?', (request.form.get('email', '').strip(),)).fetchone()
        connection.close()
        if user and check_password_hash(user['password_hash'], request.form.get('password', '')):
            session.clear()
            session.update(user_id=user['id'], role=user['role'], name=user['name'])
            return redirect(url_for('home'))
        flash('Invalid email or password.')
    return page('Login', '''<h1>Log in</h1><form method="post"><label>Email</label><input class="form-control" type="email" name="email" required><label>Password</label><input class="form-control" type="password" name="password" required><button class="btn btn-primary mt-3">Log in</button></form><p class="mt-3">New customer? <a href="/register">Register</a></p>''')

@auth.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))




