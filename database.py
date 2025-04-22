import os
import logging
import psycopg2
from psycopg2 import sql
from datetime import datetime
from typing import Dict, List, Optional, Any
from database_interface import (
    DatabaseInterface, UserInfo, InterviewInfo,
    FileInfo, InterviewResult
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class PostgreSQLDatabase(DatabaseInterface):
    def __init__(self, db_config: Dict[str, str]):
        self.conn = None
        self.db_config = db_config
        self.connect()

    def connect(self) -> None:
        """Establish connection to PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(
                dbname=self.db_config['DB_NAME'],
                user=self.db_config['DB_USER'],
                password=self.db_config['DB_PASSWORD'],
                host=self.db_config['DB_HOST'],
                port=self.db_config['DB_PORT']
            )
            self.create_tables()
            logger.info("Successfully connected to database")
        except Exception as e:
            logger.error(f"Error connecting to database: {str(e)}")
            raise

    def create_tables(self) -> None:
        """Create necessary tables if they don't exist"""
        try:
            with self.conn.cursor() as cur:
                
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS interviewees (
                        id SERIAL PRIMARY KEY,
                        telegram_id BIGINT UNIQUE NOT NULL,
                        username VARCHAR(255),
                        first_name VARCHAR(255),
                        last_name VARCHAR(255),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS interviews (
                        id SERIAL PRIMARY KEY,
                        interviewee_id INTEGER REFERENCES interviewees(id),
                        animal_type VARCHAR(50) NOT NULL,
                        animal_id INTEGER,
                        status VARCHAR(50) DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        completed_at TIMESTAMP
                    )
                """)

                
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS answers (
                        id SERIAL PRIMARY KEY,
                        interview_id INTEGER REFERENCES interviews(id),
                        question TEXT NOT NULL,
                        answer TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS files (
                        id SERIAL PRIMARY KEY,
                        interview_id INTEGER REFERENCES interviews(id),
                        file_type VARCHAR(50) NOT NULL,
                        file_path TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                self.conn.commit()
                logger.info("Tables created successfully")
        except Exception as e:
            logger.error(f"Error creating tables: {str(e)}")
            raise

    def save_interview(self, user_info: UserInfo, animal_type: str, 
                      animal_id: Optional[int], answers: Dict[str, str], 
                      pdf_path: str, image_paths: List[str]) -> int:
        """Save a complete interview to the database"""
        try:
            with self.conn.cursor() as cur:
                
                cur.execute("""
                    INSERT INTO interviewees (telegram_id, username, first_name, last_name)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (telegram_id) DO UPDATE
                    SET username = EXCLUDED.username,
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name
                    RETURNING id
                """, (user_info['id'], user_info['username'], 
                     user_info['first_name'], user_info['last_name']))
                interviewee_id = cur.fetchone()[0]

                
                cur.execute("""
                    INSERT INTO interviews (interviewee_id, animal_type, animal_id, completed_at)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                """, (interviewee_id, animal_type, animal_id, datetime.now()))
                interview_id = cur.fetchone()[0]

                
                for question, answer in answers.items():
                    cur.execute("""
                        INSERT INTO answers (interview_id, question, answer)
                        VALUES (%s, %s, %s)
                    """, (interview_id, question, answer))

                
                cur.execute("""
                    INSERT INTO files (interview_id, file_type, file_path)
                    VALUES (%s, %s, %s)
                """, (interview_id, 'pdf', pdf_path))

                # Save image files
                for image_path in image_paths:
                    cur.execute("""
                        INSERT INTO files (interview_id, file_type, file_path)
                        VALUES (%s, %s, %s)
                    """, (interview_id, 'image', image_path))

                self.conn.commit()
                logger.info(f"Interview {interview_id} saved successfully")
                return interview_id
        except Exception as e:
            logger.error(f"Error saving interview: {str(e)}")
            raise

    def get_interview(self, interview_id: int) -> Optional[InterviewResult]:
        """Retrieve a complete interview by ID"""
        try:
            with self.conn.cursor() as cur:
                
                cur.execute("""
                    SELECT i.*, it.telegram_id, it.username, it.first_name, it.last_name
                    FROM interviews i
                    JOIN interviewees it ON i.interviewee_id = it.id
                    WHERE i.id = %s
                """, (interview_id,))
                interview_data = cur.fetchone()

                if not interview_data:
                    return None

                
                interview_info: InterviewInfo = {
                    'id': interview_data[0],
                    'interviewee_id': interview_data[1],
                    'animal_type': interview_data[2],
                    'animal_id': interview_data[3],
                    'status': interview_data[4],
                    'created_at': interview_data[5],
                    'completed_at': interview_data[6]
                }

                
                cur.execute("""
                    SELECT question, answer
                    FROM answers
                    WHERE interview_id = %s
                """, (interview_id,))
                answers = dict(cur.fetchall())

                
                cur.execute("""
                    SELECT id, interview_id, file_type, file_path, created_at
                    FROM files
                    WHERE interview_id = %s
                """, (interview_id,))
                files_data = cur.fetchall()

                
                files: List[FileInfo] = [
                    {
                        'id': file_data[0],
                        'interview_id': file_data[1],
                        'file_type': file_data[2],
                        'file_path': file_data[3],
                        'created_at': file_data[4]
                    }
                    for file_data in files_data
                ]

                return {
                    'interview': interview_info,
                    'answers': answers,
                    'files': files
                }
        except Exception as e:
            logger.error(f"Error retrieving interview: {str(e)}")
            raise

    def get_interviews_by_user(self, telegram_id: int) -> List[InterviewInfo]:
        """Retrieve all interviews for a specific user"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT i.*
                    FROM interviews i
                    JOIN interviewees it ON i.interviewee_id = it.id
                    WHERE it.telegram_id = %s
                    ORDER BY i.created_at DESC
                """, (telegram_id,))
                interviews_data = cur.fetchall()

                
                return [
                    {
                        'id': interview_data[0],
                        'interviewee_id': interview_data[1],
                        'animal_type': interview_data[2],
                        'animal_id': interview_data[3],
                        'status': interview_data[4],
                        'created_at': interview_data[5],
                        'completed_at': interview_data[6]
                    }
                    for interview_data in interviews_data
                ]
        except Exception as e:
            logger.error(f"Error retrieving user interviews: {str(e)}")
            raise

    def close(self) -> None:
        """Close the database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed") 