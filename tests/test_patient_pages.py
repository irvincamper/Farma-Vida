import pytest
from app import create_app
from config import Config
from types import SimpleNamespace

class FakeTable:
    def __init__(self, name):
        self.name = name
        self._eq = None
        self._selected = None
        self._order = None
        self._maybe_single = False

    def select(self, *args, **kwargs):
        self._selected = args
        return self

    def eq(self, key, value):
        self._eq = (key, value)
        return self

    def order(self, *args, **kwargs):
        self._order = args
        return self

    def maybe_single(self):
        self._maybe_single = True
        return self

    def execute(self):
        # Return different payloads based on the table name & filters
        if self.name == 'perfiles':
            # select by id
            if self._eq and self._eq[0] == 'id' and self._eq[1] == 'test-user':
                return SimpleNamespace(data={'id': 'test-user', 'nombre_completo': 'Test User', 'email': 'test@example.com', 'roles': {'nombre': 'paciente'}})
            return SimpleNamespace(data=None)

        if self.name == 'pacientes':
            if self._eq and self._eq[0] == 'user_id' and self._eq[1] == 'test-user':
                return SimpleNamespace(data={'id': 42})
            return SimpleNamespace(data=None)

        if self.name == 'promociones':
            return SimpleNamespace(data=[{'id':1,'titulo':'Promo1','descripcion':'Desc1','fecha_inicio':'2025-01-01','fecha_fin':'2025-12-31'}])

        if self.name == 'recetas':
            if self._eq and self._eq[0] == 'patient_id' and self._eq[1] == 42:
                return SimpleNamespace(data=[{'id':100,'created_at':'2025-08-02T12:00:00','doctor':{'nombre_completo':'Dr. Test'}, 'medicamento':[{'nombre':'Paracetamol 500mg'}], 'patient_id':42}])
            if self._eq and self._eq[0] == 'id' and self._eq[1] == 100:
                return SimpleNamespace(data={'id':100,'created_at':'2025-08-02T12:00:00','doctor':{'nombre_completo':'Dr. Test'}, 'medicamento':[{'nombre':'Paracetamol 500mg'}], 'patient_id':42})
            return SimpleNamespace(data=[])

        if self.name == 'registros_medicos':
            # fake one record
            return SimpleNamespace(data=[{'id':200,'fecha_consulta':'2025-07-01','tratamiento':'Revisión general','doctor':{'nombre_completo':'Dr. Test'}, 'recetas':[{'id':100}]}])

        # default
        return SimpleNamespace(data=None)

class FakeSupabase:
    def table(self, name):
        return FakeTable(name)

@pytest.fixture
def app():
    app = create_app(Config)
    # override the supabase client with the fake
    from app import extensions
    extensions.supabase.client = FakeSupabase()
    app.testing = True
    return app

@pytest.fixture
def client(app):
    return app.test_client()

def login_as_patient(client):
    # set session user to test-user
    with client.session_transaction() as sess:
        sess['user'] = {'id': 'test-user'}

def test_profile_page(client):
    login_as_patient(client)
    resp = client.get('/patient/profile')
    assert resp.status_code == 200
    data = resp.get_data(as_text=True)
    assert 'Test User' in data
    assert 'test@example.com' in data
    # Profile should include a small recent-history snippet and promotions
    assert 'Revisión general' in data
    assert 'Promo1' in data

def test_promotions_page(client):
    login_as_patient(client)
    resp = client.get('/patient/promotions')
    assert resp.status_code == 200
    assert 'Promo1' in resp.get_data(as_text=True)

def test_history_page(client):
    login_as_patient(client)
    resp = client.get('/patient/history')
    assert resp.status_code == 200
    data = resp.get_data(as_text=True)
    assert 'Revisión general' in data or 'Detalle de la consulta' in data

def test_prescriptions_listing_and_view(client):
    login_as_patient(client)
    resp = client.get('/patient/prescriptions')
    assert resp.status_code == 200
    data = resp.get_data(as_text=True)
    assert 'Paracetamol' in data
    assert 'Dr. Test' in data

    # view the detail page
    resp2 = client.get('/patient/prescription/100')
    assert resp2.status_code == 200
    data2 = resp2.get_data(as_text=True)
    assert 'Paracetamol 500mg' in data2
    assert 'Dr. Test' in data2
