import sqlite3
import json
import uuid
from typing import Dict, Optional, List
from utils.logger import logger

class DatabaseManager:
    """Handles SQLite database operations for user profiles and interactions"""
    
    def __init__(self, db_path: str = "course_recommender.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                name TEXT,
                preferences TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # User interactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                course_id TEXT,
                interaction_type TEXT,
                rating INTEGER,
                feedback TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        # Course completions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS completions (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                course_id TEXT,
                completion_percentage REAL,
                completion_date TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def create_user(self, user_id: str, name: str, preferences: Dict) -> bool:
        """Create a new user profile"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO users (user_id, name, preferences)
                VALUES (?, ?, ?)
            """, (user_id, name, json.dumps(preferences)))
            conn.commit()
            logger.info(f"Created user: {user_id}")
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"User {user_id} already exists")
            return False
        finally:
            conn.close()
    
    def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user profile"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'user_id': row[0],
                'name': row[1],
                'preferences': json.loads(row[2]) if row[2] else {},
                'created_at': row[3],
                'updated_at': row[4]
            }
        return None
    
    def update_user_preferences(self, user_id: str, preferences: Dict):
        """Update user preferences"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE users 
            SET preferences = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """, (json.dumps(preferences), user_id))
        
        conn.commit()
        conn.close()
    
    def add_interaction(self, user_id: str, course_id: str, interaction_type: str, 
                       rating: Optional[int] = None, feedback: Optional[str] = None):
        """Add user interaction"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        interaction_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO interactions (id, user_id, course_id, interaction_type, rating, feedback)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (interaction_id, user_id, course_id, interaction_type, rating, feedback))
        
        conn.commit()
        conn.close()
        logger.info(f"Added interaction: {interaction_type} for user {user_id}")
    
    def get_user_interactions(self, user_id: str) -> List[Dict]:
        """Get all interactions for a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT course_id, interaction_type, rating, feedback, timestamp
            FROM interactions 
            WHERE user_id = ?
            ORDER BY timestamp DESC
        """, (user_id,))
        
        interactions = []
        for row in cursor.fetchall():
            interactions.append({
                'course_id': row[0],
                'interaction_type': row[1],
                'rating': row[2],
                'feedback': row[3],
                'timestamp': row[4]
            })
        
        conn.close()
        return interactions