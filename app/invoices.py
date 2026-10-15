import sqlite3
from datetime import datetime
from flask import Blueprint, abort, flash, redirect, request, session, url_for
from .common import admin_required, login_required, page
from .db import db

invoices = Blueprint('invoices', __name__)

@invoices.route('/admin/orders/<int:sid>/invoice', methods=['POST'])
@login_required
@admin_required
def invoice_generate(sid):
    connection = db()
    try:
        order = connection.execute('SELECT * FROM service_orders WHERE id=? AND status="Completed"', (sid,)).fetchone()
        if not order:
            flash('Complete the service before invoicing.')
            connection.close()
            return redirect(url_for('service.service_order', sid=sid))
        existing = connection.execute('SELECT id FROM invoices WHERE service_order_id=?', (sid,)).fetchone()
        if existing:
            flash('Invoice already exists.')
            invoice_id = existing['id']
        else:
            lines = connection.execute('SELECT p.name,p.unit_price_paise,sop.quantity FROM service_order_parts sop JOIN spare_parts p ON p.id=sop.spare_part_id WHERE sop.service_order_id=?', (sid,)).fetchall()
            total = order['labour_paise'] + sum(line['unit_price_paise'] * line['quantity'] for line in lines)
            number = 'INV-{:06d}'.format(sid)
            connection.execute('INSERT INTO invoices(service_order_id,invoice_number,issued_at,total_paise) VALUES(?,?,?,?)', (sid, number, datetime.now().strftime('%Y-%m-%d %H:%M'), total))
            invoice_id = connection.execute('SELECT last_insert_rowid()').fetchone()[0]
            for line in lines:
                connection.execute('INSERT INTO invoice_items(invoice_id,part_name,quantity,unit_price_paise) VALUES(?,?,?,?)', (invoice_id, line['name'], line['quantity'], line['unit_price_paise']))
            connection.commit()
            flash('Invoice generated.')
        connection.close()
        return redirect(url_for('invoices.invoice_view', iid=invoice_id))
    except sqlite3.IntegrityError:
        connection.rollback()
        connection.close()
        flash('Invoice already exists.')
        return redirect(url_for('service.admin_appointments'))

@invoices.route('/invoices/by-order/<int:sid>')
@login_required
@admin_required
def invoice_by_order(sid):
    connection = db()
    invoice = connection.execute('SELECT id FROM invoices WHERE service_order_id=?', (sid,)).fetchone()
    connection.close()
    if invoice:
        return redirect(url_for('invoices.invoice_view', iid=invoice['id']))
    return redirect(url_for('service.service_order', sid=sid))

@invoices.route('/invoices/<int:iid>')
@login_required
def invoice_view(iid):
    connection = db()
    invoice = connection.execute('SELECT i.*,s.labour_description,s.labour_paise,a.service_type,a.preferred_at,u.name customer,v.registration_number,v.make,v.model FROM invoices i JOIN service_orders s ON s.id=i.service_order_id JOIN appointments a ON a.id=s.appointment_id JOIN vehicles v ON v.id=a.vehicle_id JOIN users u ON u.id=v.user_id WHERE i.id=?', (iid,)).fetchone()
    if not invoice:
        connection.close()
        abort(404)
    if session['role'] == 'customer':
        owner = connection.execute('SELECT v.user_id FROM vehicles v JOIN appointments a ON a.vehicle_id=v.id JOIN service_orders s ON s.appointment_id=a.id WHERE s.id=?', (invoice['service_order_id'],)).fetchone()
        if owner['user_id'] != session['user_id']:
            connection.close()
            abort(403)
    items = connection.execute('SELECT * FROM invoice_items WHERE invoice_id=?', (iid,)).fetchall()
    connection.close()
    return page(invoice['invoice_number'], '''<div class="d-flex justify-content-between"><h1>Invoice {{i.invoice_number}}</h1><button class="btn btn-outline-secondary no-print" onclick="window.print()">Print</button></div><p>Date: {{i.issued_at}}</p><p>Customer: {{i.customer}}</p><p>Vehicle: {{i.registration_number}} — {{i.make}} {{i.model}}</p><p>Service: {{i.service_type}} · Order #{{i.service_order_id}}</p><table class="table"><thead><tr><th>Description</th><th>Qty</th><th>Unit price</th><th>Amount</th></tr></thead><tbody><tr><td>Labour — {{i.labour_description}}</td><td>1</td><td>{{money(i.labour_paise)}}</td><td>{{money(i.labour_paise)}}</td></tr>{% for x in items %}<tr><td>{{x.part_name}}</td><td>{{x.quantity}}</td><td>{{money(x.unit_price_paise)}}</td><td>{{money(x.unit_price_paise*x.quantity)}}</td></tr>{% endfor %}</tbody><tfoot><tr><th colspan="3">Total</th><th>{{money(i.total_paise)}}</th></tr></tfoot></table><p>Payment status: <b>{{i.payment_status}}</b></p>{% if session.role=='admin' %}<form class="no-print" method="post" action="/invoices/{{i.id}}/payment"><select class="form-select" name="status"><option>Pending</option><option {% if i.payment_status=='Paid' %}selected{% endif %}>Paid</option></select><button class="btn btn-primary mt-2">Update payment status</button></form>{% endif %}''', i=invoice, items=items)

@invoices.route('/invoices/<int:iid>/payment', methods=['POST'])
@login_required
@admin_required
def payment(iid):
    status = request.form.get('status')
    if status not in ('Paid', 'Pending'):
        abort(400)
    connection = db()
    connection.execute('UPDATE invoices SET payment_status=? WHERE id=?', (status, iid))
    connection.commit()
    connection.close()
    return redirect(url_for('invoices.invoice_view', iid=iid))
