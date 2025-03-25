import os
import sqlite3
import pandas as pd
from datetime import datetime

class UserDatabase:
    def __init__(self, db_path='user_ratings.db'):
        
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT, -- В реальном приложении хранить хеш пароля
            created_at TIMESTAMP
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            movie_id INTEGER,
            rating REAL,
            timestamp TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE (user_id, movie_id)
        )
        ''')

        conn.commit()
        conn.close()

    def register_user(self, username, password):

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
            user = cursor.fetchone()
            if user:
                conn.close()
                return None  

            cursor.execute(
                'INSERT INTO users (username, password, created_at) VALUES (?, ?, ?)',
                (username, password, datetime.now())
            )
            user_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return user_id
        except Exception as e:
            print(f"Ошибка при регистрации пользователя: {e}")
            return None

    def authenticate_user(self, username, password):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                'SELECT id FROM users WHERE username = ? AND password = ?',
                (username, password)
            )
            user = cursor.fetchone()
            conn.close()
            return user[0] if user else None
        except Exception as e:
            print(f"Ошибка при аутентификации пользователя: {e}")
            return None

    def save_rating(self, user_id, movie_id, rating):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                'SELECT id FROM user_ratings WHERE user_id = ? AND movie_id = ?',
                (user_id, movie_id)
            )
            existing_rating = cursor.fetchone()

            if existing_rating:
                cursor.execute(
                    'UPDATE user_ratings SET rating = ?, timestamp = ? WHERE user_id = ? AND movie_id = ?',
                    (rating, datetime.now(), user_id, movie_id)
                )
            else:
                cursor.execute(
                    'INSERT INTO user_ratings (user_id, movie_id, rating, timestamp) VALUES (?, ?, ?, ?)',
                    (user_id, movie_id, rating, datetime.now())
                )

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Ошибка при сохранении оценки: {e}")
            return False

    def get_user_ratings(self, user_id):
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                'SELECT movie_id, rating FROM user_ratings WHERE user_id = ?',
                (user_id,)
            )
            ratings = cursor.fetchall()
            conn.close()
            return {str(movie_id): rating for movie_id, rating in ratings}
        except Exception as e:
            print(f"Ошибка при получении оценок пользователя: {e}")
            return {}

    def delete_rating(self, user_id, movie_id):
 
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                'DELETE FROM user_ratings WHERE user_id = ? AND movie_id = ?',
                (user_id, movie_id)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Ошибка при удалении оценки: {e}")
            return False
