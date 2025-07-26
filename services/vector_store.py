import chromadb
from sentence_transformers import SentenceTransformer
from models.course import Course
from utils.logger import logger
class VectorStore:
    """Handles vector embeddings and similarity search"""
    
    def __init__(self, collection_name: str = "courses"):
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.collection_name = collection_name
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
    
    def add_courses(self, courses: list[Course]):
        """Add course embeddings to vector store"""
        documents = []
        metadatas = []
        ids = []
        
        for course in courses:
            # Create rich text representation for embedding
            doc_text = f"""
            Title: {course.title}
            Description: {course.description}
            Category: {course.category}
            Difficulty: {course.difficulty}
            Tags: {', '.join(course.tags)}
            Duration: {course.duration} hours
            """
            
            documents.append(doc_text.strip())
            metadatas.append({
                'title': course.title,
                'category': course.category,
                'difficulty': course.difficulty,
                'duration': course.duration,
                'rating': course.rating,
                'price': course.price,
                'tags': ','.join(course.tags)
            })
            ids.append(course.id)
        
        # Generate embeddings
        embeddings = self.encoder.encode(documents).tolist()
        
        self.collection.add(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        logger.info(f"Added {len(courses)} courses to vector store")
    
    def search_similar_courses(self, query: str, user_preferences: dict, 
                             n_results: int = 10) -> list[dict]:
        """Search for similar courses based on query and user preferences"""
        
        # Enhance query with user preferences
        enhanced_query = f"""
        {query}
        Preferred categories: {', '.join(user_preferences.get('preferred_categories', []))}
        Preferred difficulty: {user_preferences.get('preferred_difficulty', 'any')}
        Learning style: {user_preferences.get('learning_style', 'any')}
        """
        
        results = self.collection.query(
            query_texts=[enhanced_query],
            n_results=n_results
        )
        
        courses = []
        for i, course_id in enumerate(results['ids'][0]):
            metadata = results['metadatas'][0][i]
            distance = results['distances'][0][i]
            
            courses.append({
                'course_id': course_id,
                'title': metadata['title'],
                'category': metadata['category'],
                'difficulty': metadata['difficulty'],
                'duration': metadata['duration'],
                'rating': metadata['rating'],
                'price': metadata['price'],
                'tags': metadata['tags'].split(','),
                'similarity_score': 1 - distance  # Convert distance to similarity
            })
        
        return courses
