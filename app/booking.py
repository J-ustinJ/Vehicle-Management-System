import sqlite3
from flask import Blueprint, abort, flash, redirect, request, session, url_for
from .common import login_required, page
from .db import db

booking = Blueprint('booking', __name__)

@booking.route('/customer')
@login_required
def customer_home():
    if session['role'] != 'customer':
        return redirect(url_for('service.admin_appointments'))
    connection = db()
    vehicles = connection.execute('SELECT * FROM vehicles WHERE user_id=?', (session['user_id'],)).fetchall()
    appointments = connection.execute('SELECT a.*,v.registration_number FROM appointments a JOIN vehicles v ON v.id=a.vehicle_id WHERE v.user_id=? ORDER BY a.id DESC', (session['user_id'],)).fetchall()
    invoices = connection.execute('SELECT i.*,a.service_type,v.registration_number FROM invoices i JOIN service_orders s ON s.id=i.service_order_id JOIN appointments a ON a.id=s.appointment_id JOIN vehicles v ON v.id=a.vehicle_id WHERE v.user_id=? ORDER BY i.id DESC', (session['user_id'],)).fetchall()
    connection.close()
    return page('My service', '''<h1>My service</h1><p><a class="btn btn-primary" href="/vehicles/new">Add vehicle</a> <a class="btn btn-outline-primary" href="/appointments/new">Book appointment</a></p><h2>Vehicles</h2><ul>{% for v in vehicles %}<li>{{v.registration_number}} — {{v.make}} {{v.model}} ({{v.year}})</li>{% else %}<li>No vehicles yet.</li>{% endfor %}</ul><h2>Appointments</h2><ul>{% for a in appointments %}<li>{{a.registration_number}} — {{a.service_type}}, {{a.preferred_at}}, {{a.status}}</li>{% else %}<li>No appointments yet.</li>{% endfor %}</ul><h2>Invoices</h2><ul>{% for i in invoices %}<li><a href="/invoices/{{i.id}}">{{i.invoice_number}}</a> — {{money(i.total_paise)}} ({{i.payment_status}})</li>{% else %}<li>No invoices yet.</li>{% endfor %}</ul>''', vehicles=vehicles, appointments=appointments, invoices=invoices)

@booking.route('/vehicles/new', methods=['GET', 'POST'])
@login_required
def vehicle_new():
    if session['role'] != 'customer':
        abort(403)
    if request.method == 'POST':
        try:
            connection = db()
            connection.execute('INSERT INTO vehicles(user_id,registration_number,make,model,year) VALUES(?,?,?,?,?)', (session['user_id'], request.form['registration_number'].strip().upper(), request.form['make'].strip(), request.form['model'].strip(), int(request.form['year'])))
            connection.commit()
            connection.close()
            flash('Vehicle added.')
            return redirect(url_for('booking.customer_home'))
        except (ValueError, sqlite3.IntegrityError):
            flash('Please check the vehicle details; registration numbers must be unique.')
    return page('Add vehicle', '''<h1>Add vehicle</h1><form method="post"><label>Registration number</label><input class="form-control" name="registration_number" required><label>Make</label><input class="form-control" name="make" required><label>Model</label><input class="form-control" name="model" required><label>Manufacturing year</label><input class="form-control" type="number" name="year" min="1886" max="2100" required><button class="btn btn-primary mt-3">Save vehicle</button></form>''')

@booking.route('/appointments/new', methods=['GET', 'POST'])
@login_required
def appointment_new():
    if session['role'] != 'customer':
        abort(403)
    connection = db()
    vehicles = connection.execute('SELECT * FROM vehicles WHERE user_id=?', (session['user_id'],)).fetchall()
    if request.method == 'POST':
        vehicle = connection.execute('SELECT id FROM vehicles WHERE id=? AND user_id=?', (request.form.get('vehicle_id'), session['user_id'])).fetchone()
        if not vehicle:
            flash('Choose one of your own vehicles.')
        else:
            try:
                connection.execute('INSERT INTO appointments(vehicle_id,service_type,preferred_at,problem) VALUES(?,?,?,?)', (vehicle['id'], request.form['service_type'].strip(), request.form['preferred_at'], request.form.get('problem', '').strip()))
                connection.commit()
                connection.close()
                flash('Appointment booked (Pending).')
                return redirect(url_for('booking.customer_home'))
            except sqlite3.Error:
                flash('Could not save appointment.')
    connection.close()
    return page('Book appointment', '''<h1>Book appointment</h1>{% if not vehicles %}<p>Add a vehicle first.</p>{% else %}<form method="post"><label>Vehicle</label><select class="form-select" name="vehicle_id" required>{% for v in vehicles %}<option value="{{v.id}}">{{v.registration_number}} — {{v.make}} {{v.model}}</option>{% endfor %}</select><label>Requested service</label><input class="form-control" name="service_type" required><label>Preferred date/time</label><input class="form-control" type="datetime-local" name="preferred_at" required><label>Problem description (optional)</label><textarea class="form-control" name="problem"></textarea><button class="btn btn-primary mt-3">Book</button></form>{% endif %}''', vehicles=vehicles)
