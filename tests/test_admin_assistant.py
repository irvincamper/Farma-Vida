import pytest
from app import create_app
from config import Config
from types import SimpleNamespace


@pytest.fixture
def app():
    app = create_app(Config)
    # provide minimal supabase mock even though assistant doesn't need it directly
    class Dummy:
        def table(self, name):
            return SimpleNamespace(execute=lambda: SimpleNamespace(data=[]))
    from app import extensions
    extensions.supabase.client = Dummy()
    app.testing = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def login_as_admin(client):
    with client.session_transaction() as sess:
        sess['user'] = {'id': 'admin-1'}


def test_admin_assistant_page(client):
    login_as_admin(client)
    resp = client.get('/admin/assistant')
    assert resp.status_code == 200
    data = resp.get_data(as_text=True)
    assert 'Asistente del Administrador' in data


def test_admin_assistant_api(client, monkeypatch):
    login_as_admin(client)

    # patch call_llm to avoid external call
    from app import llm_client

    def fake_call(prompt, model='gpt-3.5-turbo'):
        return {'ok': True, 'response': f'Fake response to: {prompt}'}

    monkeypatch.setattr(llm_client, 'call_llm', fake_call)

    resp = client.post('/admin/assistant/api', json={'message': 'hola admin'})
    assert resp.status_code == 200
    j = resp.get_json()
    assert j['ok'] is True
    assert 'Fake response to' in j['response']
