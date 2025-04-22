import os
import sqlite3
import json
from dotenv import load_dotenv
import logging

load_dotenv()

class DatabaseManager:
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.connect()

    def connect(self):
        """Establish database connection"""
        try:
            
            os.makedirs('data', exist_ok=True)
            
            self.conn = sqlite3.connect('data/pet_adoption.db')
            
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            self._create_tables()
            logging.info("Successfully connected to the database")
        except Exception as e:
            logging.error(f"Error connecting to database: {str(e)}")
            raise

    def _create_tables(self):
        """Create necessary tables if they don't exist"""
        try:
            # Create users table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    name TEXT,
                    phone TEXT,
                    email TEXT,
                    address TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS interviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    animal_id TEXT,
                    status TEXT,
                    answers TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)

            self.conn.commit()
            logging.info("Database tables created successfully")
        except Exception as e:
            logging.error(f"Error creating tables: {str(e)}")
            self.conn.rollback()
            raise

    def save_user(self, telegram_id: int, name: str = None, phone: str = None, 
                  email: str = None, address: str = None) -> int:
        """Save or update user information"""
        try:
            self.cursor.execute("""
                INSERT OR REPLACE INTO users (telegram_id, name, phone, email, address)
                VALUES (?, ?, ?, ?, ?)
            """, (telegram_id, name, phone, email, address))
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            logging.error(f"Error saving user: {str(e)}")
            self.conn.rollback()
            raise

    def save_interview(self, user_id: int, animal_id: str, answers: dict, 
                      status: str = 'pending') -> int:
        """Save interview information"""
        try:
            answers_json = json.dumps(answers)
            self.cursor.execute("""
                INSERT INTO interviews 
                (user_id, animal_id, answers, status)
                VALUES (?, ?, ?, ?)
            """, (user_id, animal_id, answers_json, status))
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            logging.error(f"Error saving interview: {str(e)}")
            self.conn.rollback()
            raise

    def get_user_interviews(self, telegram_id: int) -> list:
        """Get all interviews for a user"""
        try:
            self.cursor.execute("""
                SELECT i.* FROM interviews i
                JOIN users u ON u.id = i.user_id
                WHERE u.telegram_id = ?
                ORDER BY i.created_at DESC
            """, (telegram_id,))
            rows = self.cursor.fetchall()
            
            return [{**dict(row), 'answers': json.loads(row['answers'])} for row in rows]
        except Exception as e:
            logging.error(f"Error getting user interviews: {str(e)}")
            raise

    def __del__(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close() 