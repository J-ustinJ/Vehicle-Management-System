import os, tempfile, pytest
from app import app as flask_app, init_db, db
@pytest.fixture
def app():
 fd,path=tempfile.mkstemp(); os.close(fd); flask_app.config.update(TESTING=True,DATABASE=path,SECRET_KEY='test'); init_db(); yield flask_app; os.unlink(path)
@pytest.fixture
def client(app): return app.test_client()
def register(client,email='customer@example.com'):
 return client.post('/register',data={'name':'Customer','email':email,'password':'password123'},follow_redirects=True)
def login(client,email='customer@example.com',password='password123'):
 return client.post('/login',data={'email':email,'password':password},follow_redirects=True)
def admin(app):
 with app.app_context():
  c=db(); from werkzeug.security import generate_password_hash
  c.execute("INSERT INTO users(name,email,password_hash,role) VALUES('Admin','admin@x.test',?,'admin')",(generate_password_hash('password123'),)); c.commit(); c.close()
def test_register_login_and_duplicate(client):
 assert b'Registration complete' in register(client); assert b'already exists' in register(client); assert b'Customer registration' in login(client)
def test_invalid_login_and_customer_authorization(app,client):
 assert b'Invalid email or password' in client.post('/login',data={'email':'none','password':'bad'},follow_redirects=True).data
 register(client); assert client.get('/admin/appointments').status_code==403

def test_complete_workflow_and_ownership(app):
 admin(app); c1=app.test_client(); c2=app.test_client(); register(c1); register(c2,'other@example.com'); login(c1); login(c2)
 c1.post('/vehicles/new',data={'registration_number':'KA01AB1234','make':'Honda','model':'City','year':'2020'}); c2.post('/vehicles/new',data={'registration_number':'KA02XY9999','make':'Tata','model':'Nexon','year':'2022'})
 with app.app_context():
  con=db(); v1=con.execute("select id from vehicles where registration_number='KA01AB1234'").fetchone()['id']; v2=con.execute("select id from vehicles where registration_number='KA02XY9999'").fetchone()['id']; con.close()
 resp=c2.post('/appointments/new',data={'vehicle_id':v1,'service_type':'Oil change','preferred_at':'2026-10-20T10:30','problem':''},follow_redirects=True); assert b'Choose one of your own vehicles' in resp.data
 c1.post('/appointments/new',data={'vehicle_id':v1,'service_type':'Oil change','preferred_at':'2026-10-20T10:30','problem':'Noise'})
 ca=app.test_client(); login(ca,'admin@x.test'); assert b'Oil change' in ca.get('/admin/appointments').data
 ca.post('/admin/mechanics',data={'name':'Manish'});
 with app.app_context():
  con=db(); mid=con.execute('select id from mechanics').fetchone()['id']; aid=con.execute('select id from appointments').fetchone()['id']; con.close()
 ca.post(f'/admin/appointments/{aid}/assign',data={'mechanic_id':mid})
 with app.app_context():
  con=db(); sid=con.execute('select id from service_orders').fetchone()['id']; con.close()
 ca.post('/admin/parts',data={'name':'Oil filter','price':'12.50'}); 
 with app.app_context():
  con=db(); pid=con.execute('select id from spare_parts').fetchone()['id']; con.close()
 ca.post(f'/admin/orders/{sid}',data={'action':'save','labour_description':'Oil service','labour_charge':'75.00'}); ca.post(f'/admin/orders/{sid}',data={'action':'add_part','labour_description':'Oil service','labour_charge':'75.00','part_id':pid,'quantity':'2'}); ca.post(f'/admin/orders/{sid}',data={'action':'complete','labour_description':'Oil service','labour_charge':'75.00'})
 ca.post(f'/admin/orders/{sid}/invoice'); ca.post(f'/admin/orders/{sid}/invoice')
 with app.app_context():
  con=db(); i=con.execute('select * from invoices').fetchone(); assert i['total_paise']==10000; assert con.execute('select count(*) n from invoices').fetchone()['n']==1; iid=i['id']; con.close()
 ca.post(f'/invoices/{iid}/payment',data={'status':'Paid'}); assert b'Paid' in ca.get(f'/invoices/{iid}').data
 c1.get('/logout'); login(c1); assert b'INV-' in c1.get('/customer').data; assert c2.get(f'/invoices/{iid}').status_code==403
