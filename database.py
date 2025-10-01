import json
import os

class Database:
    def __init__(self, filename='data.json'):
        self.filename = filename
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        if not os.path.exists(self.filename):
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump({
                    'exchange_rate': 12.5,
                    'users': [],
                    'statistics': {
                        'total_calculations': 0,
                        'total_users': 0
                    }
                }, f, ensure_ascii=False, indent=4)
    
    def _read_data(self):
        with open(self.filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _write_data(self, data):
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    
    def get_exchange_rate(self):
        data = self._read_data()
        return data.get('exchange_rate', 12.5)
    
    def set_exchange_rate(self, rate):
        data = self._read_data()
        data['exchange_rate'] = float(rate)
        self._write_data(data)
    
    def add_user(self, user_id, username):
        data = self._read_data()
        users = data['users']
        
        # Проверяем, есть ли пользователь уже в базе
        user_exists = any(user['user_id'] == user_id for user in users)
        
        if not user_exists:
            users.append({
                'user_id': user_id,
                'username': username,
                'first_seen': str(datetime.now())
            })
            data['statistics']['total_users'] += 1
            self._write_data(data)
    
    def increment_calculations(self):
        data = self._read_data()
        data['statistics']['total_calculations'] += 1
        self._write_data(data)
    
    def get_statistics(self):
        data = self._read_data()
        return data['statistics']
    
    def get_all_users(self):
        data = self._read_data()
        return data['users']