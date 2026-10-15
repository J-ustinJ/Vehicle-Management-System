from functools import wraps
from flask import abort, redirect, render_template, render_template_string, session, url_for

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('auth.login'))
        return view(*args, **kwargs)
    return wrapped

def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get('role') != 'admin':
            abort(403)
        return view(*args, **kwargs)
    return wrapped

def page(title, body, **context):
    return render_template('base.html', title=title, body=render_template_string(body, **context), **context)

def money(paise):
    return '₹{:,.2f}'.format(paise / 100)
