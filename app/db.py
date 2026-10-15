import sqlite3
from flask import current_app

SCHEMA = '''
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE COLLATE NOCASE, password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('customer','admin')));
CREATE TABLE IF NOT EXISTS vehicles(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), registration_number TEXT NOT NULL UNIQUE, make TEXT NOT NULL, model TEXT NOT NULL, year INTEGER NOT NULL CHECK(year BETWEEN 1886 AND 2100));
CREATE TABLE IF NOT EXISTS appointments(id INTEGER PRIMARY KEY, vehicle_id INTEGER NOT NULL REFERENCES vehicles(id), service_type TEXT NOT NULL, preferred_at TEXT NOT NULL, problem TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending','Assigned','In Service','Completed')));
CREATE TABLE IF NOT EXISTS mechanics(id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS service_orders(id INTEGER PRIMARY KEY, appointment_id INTEGER NOT NULL UNIQUE REFERENCES appointments(id), mechanic_id INTEGER NOT NULL REFERENCES mechanics(id), labour_description TEXT NOT NULL DEFAULT '', labour_paise INTEGER NOT NULL DEFAULT 0 CHECK(labour_paise>=0), status TEXT NOT NULL DEFAULT 'In Service' CHECK(status IN ('In Service','Completed')));
CREATE TABLE IF NOT EXISTS spare_parts(id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, unit_price_paise INTEGER NOT NULL CHECK(unit_price_paise>=0));
CREATE TABLE IF NOT EXISTS service_order_parts(id INTEGER PRIMARY KEY, service_order_id INTEGER NOT NULL REFERENCES service_orders(id), spare_part_id INTEGER NOT NULL REFERENCES spare_parts(id), quantity INTEGER NOT NULL CHECK(quantity>0));
CREATE TABLE IF NOT EXISTS invoices(id INTEGER PRIMARY KEY, service_order_id INTEGER NOT NULL UNIQUE REFERENCES service_orders(id), invoice_number TEXT NOT NULL UNIQUE, issued_at TEXT NOT NULL, payment_status TEXT NOT NULL DEFAULT 'Pending' CHECK(payment_status IN ('Paid','Pending')), total_paise INTEGER NOT NULL CHECK(total_paise>=0));
CREATE TABLE IF NOT EXISTS invoice_items(id INTEGER PRIMARY KEY, invoice_id INTEGER NOT NULL REFERENCES invoices(id), part_name TEXT NOT NULL, quantity INTEGER NOT NULL CHECK(quantity>0), unit_price_paise INTEGER NOT NULL CHECK(unit_price_paise>=0));
'''

def db():
    connection = sqlite3.connect(current_app.config['DATABASE'])
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys=ON')
    return connection

def init_db(app=None):
    if app is None:
        app = current_app._get_current_object()
    with app.app_context():
        connection = db()
        connection.executescript(SCHEMA)
        connection.commit()
        connection.close()
