# Vehicle Management System

## Objective

Build a web app that lets customers book vehicle service and receive an invoice. The app uses Flask, SQLite, Bootstrap, and runs locally on Windows. Work is planned using the Iterative and Incremental Model: build and connect the core workflow first, then extend it as needed.

## Features in this version

- Customer registration and login; admin login and account setup.
- Customers add vehicles and book appointments for their own vehicles.
- Admins add mechanics and assign them to appointments.
- Admins create service orders, add labour and spare parts, and mark work Completed.
- Admins create invoices and set payment to Paid or Pending.
- Customers view and print their own invoices.

Prices are entered in rupees and stored in paise. Invoices keep the part prices used when they were created. Stock tracking and online payments are not included.

## Progress

All four workflow areas are implemented and connected through SQLite. Tests, including an end-to-end test, are written. The app code is separated by feature; the database and shared helpers are kept in shared files.

## Team roles

| Member | Feature file | Responsibility |
|---|---|---|
| Justin | `app/auth.py` | Registration, login, roles, and access checks |
| Joel | `app/booking.py` | Vehicles, appointments, and ownership checks |
| Manish | `app/service.py` | Mechanics, service orders, labour/parts, and completion |
| Rithik | `app/invoices.py` | Invoices, payment status, and customer invoice view |

## Run on Windows

In PowerShell, from this folder:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
flask --app app init-db
flask --app app create-admin
flask --app app run
```

Create an admin when prompted, then visit http://127.0.0.1:5000. Public registration is for customers. Data is saved in `app/service.db` and remains after the app stops.

To run tests, activate `.venv` and use:

```powershell
python -m pytest -q
```

## Main files

- `app/auth.py` — customer and admin authentication.
- `app/booking.py` — vehicle registration and appointment booking.
- `app/service.py` — mechanic assignment and service orders.
- `app/invoices.py` — invoice generation and payment status.
- `app/db.py` — SQLite tables and database connection.
- `app/common.py` — shared login checks, page helper, and currency display.
- `app/__init__.py` — creates the Flask app and connects the feature files.
- `app/templates/base.html` — shared page layout.
- `run.py` — convenience startup script.
- `tests/test_workflow.py` — automated workflow tests.

