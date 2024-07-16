import sqlite3


class Database:
    def __init__(self):
        self.connection = sqlite3.connect('database.db')
        self.cursor = self.connection.cursor()
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS audios (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        path TEXT NOT NULL,
                        title TEXT NOT NULL,
                        author TEXT NOT NULL,
                        url TEXT NOT NULL UNIQUE,
                        file_id TEXT UNIQUE
                        )''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS videos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        path TEXT NOT NULL,
                        title TEXT NOT NULL,
                        author TEXT NOT NULL,
                        url TEXT NOT NULL UNIQUE,
                        file_id TEXT UNIQUE
                        )''')
        self.connection.commit()
        self.connection.close()

    def insert(self, path, url, filetype, file_id='', title='', author=''):
        self.connection = sqlite3.connect('database.db')
        self.cursor = self.connection.cursor()
        try:
            self.cursor.execute(f'INSERT INTO {filetype}s (path, url, file_id, title, author) VALUES (?,?,?,?,?)', (path, url, file_id, title, author))
        except sqlite3.IntegrityError:
            return
        self.connection.commit()
        self.connection.close()

    def update(self, url, filetype, file_id):
        self.connection = sqlite3.connect('database.db')
        self.cursor = self.connection.cursor()
        self.cursor.execute(f'UPDATE {filetype}s SET file_id = ? WHERE url = ?', (file_id, url))
        self.connection.commit()
        self.connection.close()

    def get_id(self, url, filetype):
        self.connection = sqlite3.connect('database.db')
        self.cursor = self.connection.cursor()
        self.cursor.execute(f'SELECT file_id FROM {filetype}s WHERE url = ?', (url,))
        result = self.cursor.fetchone()
        self.connection.close()
        return result[0] if result else None
