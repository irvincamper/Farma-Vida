# app/extensions.py
from supabase import create_client, Client

class SupabaseManager:
    def __init__(self, app=None):
        self.client: Client = None
        if app is not None:
            self.init_app(app)
    def init_app(self, app):
        url = app.config['SUPABASE_URL']
        key = app.config['SUPABASE_KEY']
        self.client = create_client(url, key)

supabase = SupabaseManager()