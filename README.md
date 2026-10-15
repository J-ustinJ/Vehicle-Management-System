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

Prices are stored in paise. Invoices keep the part prices used when they were created. Stock tracking and online payments are not included.

## Progress

All four workflow areas are implemented in the current app and connected through SQLite. Tests, including an end-to-end test, are written.

The code is currently compact: most routes and database logic are in `app/__init__.py`. The role assignments below describe the team's planned responsibilities.

## Team roles

| Member | Responsibility |
|---|---|
| Justin | Registration, login, roles, and access checks |
| Joel | Vehicles, appointments, and ownership checks |
| Manish | Mechanics, service orders, labour/parts, and completion |
| Rithik | Invoices, payment status, and customer invoice view |

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

- `app/__init__.py` — app, database, routes, and workflow logic.
- `app/templates/base.html` — shared page layout.
- `run.py` — convenience startup script.
- `tests/test_workflow.py` — automated tests.
- `requirements.txt` — Python dependencies.
