import sqlite3
from flask import Blueprint, abort, flash, redirect, request, url_for, session
from .common import admin_required, login_required, page
from .db import db

service = Blueprint('service', __name__)

@service.route('/admin/appointments')
@login_required
@admin_required
def admin_appointments():
    connection = db()
    appointments = connection.execute('SELECT a.*,v.registration_number,v.make,v.model,u.name customer,m.name mechanic,s.id order_id,s.status order_status FROM appointments a JOIN vehicles v ON v.id=a.vehicle_id JOIN users u ON u.id=v.user_id LEFT JOIN service_orders s ON s.appointment_id=a.id LEFT JOIN mechanics m ON m.id=s.mechanic_id ORDER BY a.id DESC').fetchall()
    mechanics = connection.execute('SELECT * FROM mechanics').fetchall()
    connection.close()
    return page('Appointments', '''<h1>Appointments</h1><p><a class="btn btn-outline-primary" href="/admin/mechanics">Manage mechanics</a> <a class="btn btn-outline-primary" href="/admin/parts">Manage parts</a></p>{% for a in appointments %}<article class="card p-3 mb-3"><b>{{a.registration_number}} — {{a.make}} {{a.model}}</b><p>{{a.customer}} · {{a.service_type}} · {{a.preferred_at}} · {{a.status}}</p><p>{{a.problem}}</p>{% if not a.order_id %}<form method="post" action="/admin/appointments/{{a.id}}/assign"><select class="form-select" name="mechanic_id" required><option value="">Assign mechanic</option>{% for m in mechanics %}<option value="{{m.id}}">{{m.name}}</option>{% endfor %}</select><button class="btn btn-primary mt-2">Assign and create service order</button></form>{% elif a.order_status!='Completed' %}<a class="btn btn-primary" href="/admin/orders/{{a.order_id}}">Update service order</a>{% else %}<a class="btn btn-success" href="/invoices/by-order/{{a.order_id}}">View invoice / create</a>{% endif %}</article>{% else %}<p>No appointments.</p>{% endfor %}''', appointments=appointments, mechanics=mechanics)

@service.route('/admin/mechanics', methods=['GET', 'POST'])
@login_required
@admin_required
def mechanics():
    connection = db()
    if request.method == 'POST' and request.form.get('name', '').strip():
        connection.execute('INSERT INTO mechanics(name,phone) VALUES(?,?)', (request.form['name'].strip(), request.form.get('phone', '').strip()))
        connection.commit()
        flash('Mechanic added.')
    mechanics_list = connection.execute('SELECT * FROM mechanics ORDER BY name').fetchall()
    connection.close()
    return page('Mechanics', '''<h1>Mechanics</h1><form method="post"><input class="form-control" name="name" placeholder="Name" required><input class="form-control mt-2" name="phone" placeholder="Phone (optional)"><button class="btn btn-primary mt-2">Add mechanic</button></form><ul class="mt-3">{% for m in mechanics %}<li>{{m.name}}{% if m.phone %} — {{m.phone}}{% endif %}</li>{% endfor %}</ul><a href="/admin/appointments">Appointments</a>''', mechanics=mechanics_list)

@service.route('/admin/parts', methods=['GET', 'POST'])
@login_required
@admin_required
def parts():
    connection = db()
    if request.method == 'POST':
        try:
            connection.execute('INSERT INTO spare_parts(name,unit_price_paise) VALUES(?,?)', (request.form['name'].strip(), int(round(float(request.form['price']) * 100))))
            connection.commit()
            flash('Spare part added.')
        except (ValueError, sqlite3.IntegrityError):
            flash('Invalid or duplicate part.')
    parts_list = connection.execute('SELECT * FROM spare_parts ORDER BY name').fetchall()
    connection.close()
    return page('Spare parts', '''<h1>Spare parts</h1><form method="post"><input class="form-control" name="name" placeholder="Part name" required><input class="form-control mt-2" name="price" type="number" step="0.01" min="0" placeholder="Unit price (₹)" required><button class="btn btn-primary mt-2">Add part</button></form><ul class="mt-3">{% for p in parts %}<li>{{p.name}} — {{money(p.unit_price_paise)}}</li>{% endfor %}</ul><a href="/admin/appointments">Appointments</a>''', parts=parts_list)

@service.route('/admin/appointments/<int:aid>/assign', methods=['POST'])
@login_required
@admin_required
def assign(aid):
    connection = db()
    try:
        connection.execute('INSERT INTO service_orders(appointment_id,mechanic_id) VALUES(?,?)', (aid, int(request.form['mechanic_id'])))
        connection.execute("UPDATE appointments SET status='Assigned' WHERE id=?", (aid,))
        connection.commit()
        flash('Mechanic assigned and service order created.')
    except (sqlite3.Error, ValueError):
        connection.rollback()
        flash('Assignment failed. Check appointment and mechanic; an order may already exist.')
    connection.close()
    return redirect(url_for('service.admin_appointments'))

@service.route('/admin/orders/<int:sid>', methods=['GET', 'POST'])
@login_required
@admin_required
def service_order(sid):
    connection = db()
    order = connection.execute('SELECT s.*,a.status appointment_status,a.service_type,v.registration_number FROM service_orders s JOIN appointments a ON a.id=s.appointment_id JOIN vehicles v ON v.id=a.vehicle_id WHERE s.id=?', (sid,)).fetchone()
    parts_list = connection.execute('SELECT * FROM spare_parts ORDER BY name').fetchall()
    if not order:
        connection.close()
        abort(404)
    if request.method == 'POST' and order['status'] != 'Completed':
        action = request.form.get('action')
        try:
            connection.execute('UPDATE service_orders SET labour_description=?,labour_paise=? WHERE id=?', (request.form.get('labour_description', '').strip(), int(round(float(request.form.get('labour_charge', '0')) * 100)), sid))
            if action == 'add_part':
                connection.execute('INSERT INTO service_order_parts(service_order_id,spare_part_id,quantity) VALUES(?,?,?)', (sid, int(request.form['part_id']), int(request.form['quantity'])))
            if action == 'complete':
                connection.execute("UPDATE service_orders SET status='Completed' WHERE id=?", (sid,))
                connection.execute("UPDATE appointments SET status='Completed' WHERE id=(SELECT appointment_id FROM service_orders WHERE id=?)", (sid,))
            connection.commit()
            flash('Service order updated.')
        except (ValueError, sqlite3.Error):
            connection.rollback()
            flash('Could not update order; check charges and part quantity.')
        connection.close()
        return redirect(url_for('service.service_order', sid=sid))
    lines = connection.execute('SELECT sop.*,p.name,p.unit_price_paise FROM service_order_parts sop JOIN spare_parts p ON p.id=sop.spare_part_id WHERE sop.service_order_id=?', (sid,)).fetchall()
    connection.close()
    return page('Service order', '''<h1>Service order #{{s.id}}</h1><p>{{s.registration_number}} · {{s.service_type}} · {{s.status}}</p><h2>Labour and parts</h2><form method="post"><label>Labour description</label><input class="form-control" name="labour_description" value="{{s.labour_description}}" {% if s.status=='Completed' %}disabled{% endif %}><label>Labour charge (₹)</label><input class="form-control" type="number" min="0" step="0.01" name="labour_charge" value="{{'%.2f'|format(s.labour_paise/100)}}" {% if s.status=='Completed' %}disabled{% endif %}><button class="btn btn-outline-primary mt-2" name="action" value="save" {% if s.status=='Completed' %}disabled{% endif %}>Save labour</button></form><ul>{% for p in lines %}<li>{{p.name}} × {{p.quantity}} at {{money(p.unit_price_paise)}}</li>{% else %}<li>No parts recorded.</li>{% endfor %}</ul>{% if s.status!='Completed' %}<form method="post"><input type="hidden" name="labour_description" value="{{s.labour_description}}"><input type="hidden" name="labour_charge" value="{{'%.2f'|format(s.labour_paise/100)}}"><select class="form-select" name="part_id" required>{% for p in parts %}<option value="{{p.id}}">{{p.name}} — {{money(p.unit_price_paise)}}</option>{% endfor %}</select><input class="form-control mt-2" type="number" name="quantity" min="1" value="1" required><button class="btn btn-outline-primary mt-2" name="action" value="add_part">Add parts used</button></form><form method="post" class="mt-3"><input type="hidden" name="labour_description" value="{{s.labour_description}}"><input type="hidden" name="labour_charge" value="{{'%.2f'|format(s.labour_paise/100)}}"><button class="btn btn-success" name="action" value="complete">Mark Completed</button></form>{% else %}<form method="post" action="/admin/orders/{{s.id}}/invoice"><button class="btn btn-primary">Generate invoice</button></form>{% endif %}<p class="mt-3"><a href="/admin/appointments">Back to appointments</a></p>''', s=order, lines=lines, parts=parts_list)
