import pandas as pd
from db.database_manager import DatabaseManager
from services.vector_store import VectorStore
from services.ollama_client import OllamaClient
from models.course import Course
from utils.logger import logger

class CourseRecommendationEngine:
    def __init__(self):
        self.db = DatabaseManager()
        self.vector_store = VectorStore()
        self.llm = OllamaClient()
        self.courses = []
        self.load_courses_from_csv("data/coursea_data.csv")

    def load_courses_from_csv(self, csv_path: str):
        df = pd.read_csv(csv_path)
        df = df.rename(columns={
            'course_title': 'title',
            'course_organization': 'organization',
            'course_Certificate_type': 'category',
            'course_rating': 'rating',
            'course_difficulty': 'difficulty',
            'course_students_enrolled': 'students_enrolled'
        })

        courses = []
        for idx, row in df.iterrows():
            course = Course(
                id=str(idx),
                title=row['title'],
                description=row.get('organization', 'No description'),
                category=row.get('category', 'General'),
                difficulty=str(row.get('difficulty', 'mixed')).lower(),
                duration=40,  # default/fallback duration in hours,
                tags=[str(row.get('category', 'general')).lower()],
                rating=float(row.get('rating', 4.0)),
                price=99.99  
            )
            courses.append(course)

        self.courses = courses
        self.vector_store.add_courses(courses)
        logger.info(f"Loaded {len(courses)} courses from CSV and added to vector store.")

    def create_user_profile(self, user_id: str, name: str, initial_feedback: str) -> dict:
        preferences = self.llm.extract_preferences(initial_feedback)
        created = self.db.create_user(user_id, name, preferences)
        if created:
            return {'user_id': user_id, 'name': name, 'preferences': preferences, 'message': 'Profile created successfully!'}
        else:
            return {'error': 'User already exists'}

    def get_user_preferences(self, user_id: str) -> dict:
        user = self.db.get_user(user_id)
        if user and 'preferences' in user:
            return user['preferences']
        # Return some default preferences if none saved
        return {
            "preferred_categories": ["general"],
            "preferred_difficulty": "intermediate",
            "learning_style": "hands-on",
            "preferred_duration": "medium",
            "budget_preference": "medium",
            "goals": ["skill development"]
        }
    def get_personalized_recommendations(self, user_id: str, query: str = "", num_recommendations: int = 5) -> dict:
        user = self.db.get_user(user_id)
        if not user:
            return {'error': 'User not found'}

        interactions = self.db.get_user_interactions(user_id)

        if not query:
            query = f"Recommend courses based on my interests: {', '.join(user['preferences'].get('preferred_categories', []))}"

        similar_courses = self.vector_store.search_similar_courses(query, user['preferences'], n_results=num_recommendations*3)

        filtered = self.filter_recommendations(similar_courses, user['preferences'], interactions)
        recommendations = []
        for course in filtered[:num_recommendations]:
            explanation = self.generate_recommendation_explanation(course, user['preferences'], interactions)
            recommendations.append({**course, 'explanation': explanation})

        return {'user_id': user_id, 'recommendations': recommendations, 'total_found': len(filtered)}

    def filter_recommendations(self, courses: list[dict], preferences: dict, interactions: list[dict]) -> list[dict]:
        interacted_course_ids = {i['course_id'] for i in interactions}
        filtered = [c for c in courses if c['course_id'] not in interacted_course_ids]

        for course in filtered:
            score = course['similarity_score']
            if course['category'] in preferences.get('preferred_categories', []):
                score += 0.2
            if course['difficulty'] == preferences.get('preferred_difficulty'):
                score += 0.1
            duration_pref = preferences.get('preferred_duration', 'medium')
            if duration_pref == 'short' and course['duration'] <= 30:
                score += 0.1
            elif duration_pref == 'medium' and 30 < course['duration'] <= 60:
                score += 0.1
            elif duration_pref == 'long' and course['duration'] > 60:
                score += 0.1
            course['final_score'] = score

        return sorted(filtered, key=lambda x: x['final_score'], reverse=True)

    def generate_recommendation_explanation(self, course: dict, preferences: dict, interactions: list[dict]) -> str:
        prompt = f"""
    You are an AI course advisor. A user is looking for personalized course recommendations based on their learning preferences.

    User preferences:
    - Categories: {', '.join(preferences.get('preferred_categories', []))}
    - Difficulty: {preferences.get('preferred_difficulty')}
    - Duration preference: {preferences.get('preferred_duration')}
    - Learning style: {preferences.get('learning_style')}
    - Goals: {', '.join(preferences.get('goals', []))}

    Recommended course details:
    - Title: {course['title']}
    - Category: {course['category']}
    - Difficulty: {course['difficulty']}
    - Rating: {course['rating']}
    - Description: {course.get('description', 'N/A')}
    - Duration: {course['duration']} hours

    Please generate a short two line only, friendly explanation for why this course is recommended to the user.
    """

        try:
            response = self.llm.generate_response(prompt)
            return response.strip()
        except Exception as e:
            logger.warning(f"LLM explanation generation failed: {e}")
            return "Recommended based on your preferences."


    def process_user_feedback(self, user_id: str, course_id: str, rating: int, feedback: str) -> dict:
        self.db.add_interaction(user_id, course_id, "feedback", rating, feedback)

        if rating >= 4:
            user = self.db.get_user(user_id)
            if user:
                course = next((c for c in self.courses if c.id == course_id), None)
                if course:
                    preferences = user['preferences']
                    if 'preferred_categories' not in preferences:
                        preferences['preferred_categories'] = []
                    if course.category not in preferences['preferred_categories']:
                        preferences['preferred_categories'].append(course.category)
                    if rating == 5 and course.difficulty != preferences.get('preferred_difficulty'):
                        preferences['preferred_difficulty'] = course.difficulty
                    self.db.update_user_preferences(user_id, preferences)
        return {'message': 'Feedback processed successfully', 'updated_preferences': rating >= 4}
