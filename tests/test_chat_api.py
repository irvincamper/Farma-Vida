import json
import types
import pytest
import os
import sys

# ensure project root is on sys.path so imports like `app` work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import Config


@pytest.fixture
def app_client(mock_supabase):
    # Create a minimal Flask app and register only the chat blueprint to avoid app-wide hooks
    from flask import Flask, g, session
    # import the chat blueprint after mocks are in place
    import app.routes.chat as chatmod

    flask_app = Flask(__name__)
    flask_app.secret_key = 'test-secret'
    flask_app.register_blueprint(chatmod.chat_bp, url_prefix='/chat')

    # simple before_request to set g.profile from session (mimic app behavior)
    @flask_app.before_request
    def load_profile():
        g.profile = None
        user_info = session.get('user')
        if user_info and 'id' in user_info:
            # use mocked storage profile
            g.profile = mock_supabase.get('profile')

    return flask_app.test_client()


class MockResponse:
    def __init__(self, data=None, count=None):
        self.data = data
        self.count = count


class MockTable:
    def __init__(self, name, storage):
        self.name = name
        self.storage = storage

    def select(self, *args, **kwargs):
        return self

    def maybe_single(self):
        return self

    def eq(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def or_(self, *args, **kwargs):
        return self

    def insert(self, payload):
        # simulate insert by appending to storage
        if self.name == 'mensajes':
            entry = dict(payload)
            entry.setdefault('id', 'msg-' + str(len(self.storage.get('mensajes', [])) + 1))
            self.storage.setdefault('mensajes', []).append(entry)
            # store last insert and return self so .execute() can be called afterwards
            self._last_insert = [entry]
            return self
        return MockResponse([])

    def execute(self):
        if self.name == 'perfiles':
            # return profile for a given user id stored in storage['profile'] if set
            p = self.storage.get('profile')
            return MockResponse(p)
        if self.name == 'mensajes':
            # if called after insert, return the inserted record(s)
            if hasattr(self, '_last_insert'):
                val = self._last_insert
                delattr(self, '_last_insert')
                return MockResponse(val)
            return MockResponse(self.storage.get('mensajes', []))
        return MockResponse([])


class MockClient:
    def __init__(self, storage):
        self.storage = storage

    def table(self, name):
        return MockTable(name, self.storage)


@pytest.fixture(autouse=True)
def mock_supabase(monkeypatch):
    # storage holds mock DB state
    storage = {
        'profile': {'id': 'user-1', 'nombre_completo': 'Paciente Test', 'roles': {'nombre': 'paciente'}}
    }
    mock_client = MockClient(storage)

    # monkeypatch the supabase client used in app.extensions
    import app.extensions as ext
    monkeypatch.setattr(ext, 'supabase', types.SimpleNamespace(client=mock_client))
    # monkeypatch the client used in app.decorators (load_user_profile uses this)
    import app.decorators as dec
    # Ensure create_app uses our mock client instead of creating a real supabase client
    monkeypatch.setattr(dec, 'create_client', lambda url, key: mock_client)
    return storage


def test_api_conversation_returns_messages(mock_supabase, app_client):
    client = app_client

    # prepare session with user id
    with client.session_transaction() as sess:
        sess['user'] = {'id': 'user-1'}

    # seed some messages between user-1 and user-2
    mock_supabase.setdefault('mensajes', []).extend([
        {'id': 'm1', 'sender_id': 'user-1', 'receiver_id': 'user-2', 'content': 'Hola Doc', 'created_at': '2025-01-01T12:00:00Z'},
        {'id': 'm2', 'sender_id': 'user-2', 'receiver_id': 'user-1', 'content': 'Hola Paciente', 'created_at': '2025-01-01T12:00:05Z'}
    ])

    resp = client.get('/chat/api/conversation/user-2')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'messages' in data
    assert len(data['messages']) == 2


def test_api_send_creates_message(mock_supabase, app_client):
    client = app_client
    with client.session_transaction() as sess:
        sess['user'] = {'id': 'user-1'}

    payload = {'receiver_id': 'user-2', 'content': 'Mensaje de prueba'}
    resp = client.post('/chat/api/send', data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get('ok') is True
    # check that response returns the created message
    msg = data.get('message')
    assert msg is not None
    # message may be returned as list
    if isinstance(msg, list):
        msg = msg[0]
    assert msg.get('content') == 'Mensaje de prueba'
