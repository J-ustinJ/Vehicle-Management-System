import os
import tempfile

import pytest
from werkzeug.security import generate_password_hash

from app import app as flask_app, db, init_db


@pytest.fixture
def app():
    fd, path = tempfile.mkstemp()
    os.close(fd)

    flask_app.config.update(
        TESTING=True,
        DATABASE=path,
        SECRET_KEY="test",
    )

    with flask_app.app_context():
        init_db()

    yield flask_app

    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def client(app):
    return app.test_client()


def register(client, email="customer@example.com"):
    return client.post(
        "/register",
        data={
            "name": "Customer",
            "email": email,
            "password": "password123",
        },
        follow_redirects=True,
    )


def login(client, email="customer@example.com", password="password123"):
    return client.post(
        "/login",
        data={
            "email": email,
            "password": password,
        },
        follow_redirects=True,
    )


def create_admin(app):
    with app.app_context():
        connection = db()
        connection.execute(
            """
            INSERT INTO users (name, email, password_hash, role)
            VALUES (?, ?, ?, ?)
            """,
            (
                "Admin",
                "admin@x.test",
                generate_password_hash("password123"),
                "admin",
            ),
        )
        connection.commit()
        connection.close()


def test_register_login_and_duplicate(client):
    response = register(client)
    assert b"Registration complete" in response.data

    response = register(client)
    assert b"already exists" in response.data

    response = login(client)
    assert b"My service" in response.data


def test_invalid_login_and_customer_authorization(app, client):
    response = client.post(
        "/login",
        data={
            "email": "none@example.com",
            "password": "bad",
        },
        follow_redirects=True,
    )
    assert b"Invalid email or password" in response.data

    register(client)
    login(client)
    assert client.get("/admin/appointments").status_code == 403


def test_complete_workflow_and_ownership(app):
    create_admin(app)

    customer = app.test_client()
    other_customer = app.test_client()

    register(customer)
    register(other_customer, "other@example.com")

    login(customer)
    login(other_customer, "other@example.com")

    customer.post(
        "/vehicles/new",
        data={
            "registration_number": "KA01AB1234",
            "make": "Honda",
            "model": "City",
            "year": "2020",
        },
    )
    other_customer.post(
        "/vehicles/new",
        data={
            "registration_number": "KA02XY9999",
            "make": "Tata",
            "model": "Nexon",
            "year": "2022",
        },
    )

    with app.app_context():
        connection = db()
        vehicle = connection.execute(
            "SELECT id FROM vehicles WHERE registration_number=?",
            ("KA01AB1234",),
        ).fetchone()
        vehicle_id = vehicle["id"]
        connection.close()

    # Another customer cannot book this vehicle.
    response = other_customer.post(
        "/appointments/new",
        data={
            "vehicle_id": vehicle_id,
            "service_type": "Oil change",
            "preferred_at": "2026-10-20T10:30",
            "problem": "",
        },
        follow_redirects=True,
    )
    assert b"Choose one of your own vehicles" in response.data

    # The vehicle owner can book an appointment.
    customer.post(
        "/appointments/new",
        data={
            "vehicle_id": vehicle_id,
            "service_type": "Oil change",
            "preferred_at": "2026-10-20T10:30",
            "problem": "Noise",
        },
    )

    admin_client = app.test_client()
    login(admin_client, "admin@x.test")

    response = admin_client.get("/admin/appointments")
    assert b"Oil change" in response.data

    admin_client.post(
        "/admin/mechanics",
        data={"name": "Manish"},
    )

    with app.app_context():
        connection = db()
        mechanic_id = connection.execute(
            "SELECT id FROM mechanics"
        ).fetchone()["id"]
        appointment_id = connection.execute(
            "SELECT id FROM appointments"
        ).fetchone()["id"]
        connection.close()

    admin_client.post(
        f"/admin/appointments/{appointment_id}/assign",
        data={"mechanic_id": mechanic_id},
    )

    with app.app_context():
        connection = db()
        service_order_id = connection.execute(
            "SELECT id FROM service_orders"
        ).fetchone()["id"]
        connection.close()

    admin_client.post(
        "/admin/parts",
        data={
            "name": "Oil filter",
            "price": "12.50",
        },
    )

    with app.app_context():
        connection = db()
        part_id = connection.execute(
            "SELECT id FROM spare_parts"
        ).fetchone()["id"]
        connection.close()

    admin_client.post(
        f"/admin/orders/{service_order_id}",
        data={
            "action": "save",
            "labour_description": "Oil service",
            "labour_charge": "75.00",
        },
    )
    admin_client.post(
        f"/admin/orders/{service_order_id}",
        data={
            "action": "add_part",
            "labour_description": "Oil service",
            "labour_charge": "75.00",
            "part_id": part_id,
            "quantity": "2",
        },
    )
    admin_client.post(
        f"/admin/orders/{service_order_id}",
        data={
            "action": "complete",
            "labour_description": "Oil service",
            "labour_charge": "75.00",
        },
    )

    admin_client.post(f"/admin/orders/{service_order_id}/invoice")
    admin_client.post(f"/admin/orders/{service_order_id}/invoice")

    with app.app_context():
        connection = db()
        invoice = connection.execute(
            "SELECT * FROM invoices"
        ).fetchone()

        assert invoice["total_paise"] == 10000
        assert connection.execute(
            "SELECT COUNT(*) FROM invoices"
        ).fetchone()[0] == 1

        invoice_id = invoice["id"]
        connection.close()

    admin_client.post(
        f"/invoices/{invoice_id}/payment",
        data={"status": "Paid"},
    )
    assert b"Paid" in admin_client.get(
        f"/invoices/{invoice_id}"
    ).data

    customer.get("/logout")
    login(customer)

    assert b"INV-" in customer.get("/customer").data
    assert other_customer.get(
        f"/invoices/{invoice_id}"
    ).status_code == 403
