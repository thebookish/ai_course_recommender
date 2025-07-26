import os,sys
import shutil
import pytest
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from services.vector_store import VectorStore
from models.course import Course

# ✅ Sanity check to make sure pytest collects this file
def test_sanity():
    assert 1 + 1 == 2

# ✅ Fixture to create a temporary ChromaDB instance
@pytest.fixture(scope="function")
def temp_vector_store():
    temp_path = "./test_chroma_db"
    
    # Clean old test DB
    if os.path.exists(temp_path):
        shutil.rmtree(temp_path)

    store = VectorStore(collection_name="test_courses")
    
    # Override with isolated temp path
    store.client = store.client.__class__(path=temp_path)
    store.collection = store.client.get_or_create_collection(name="test_courses")
    
    yield store

    # Teardown after each test
    if os.path.exists(temp_path):
        shutil.rmtree(temp_path)

# ✅ Sample test data
@pytest.fixture
def sample_courses():
    return [
        Course(
            id="1",
            title="Intro to Python",
            description="Learn Python from scratch.",
            category="Programming",
            difficulty="Beginner",
            tags=["python", "beginner", "coding"],
            duration=5,
            rating=4.5,
            price=0.0
        ),
        Course(
            id="2",
            title="Advanced Machine Learning",
            description="Deep dive into ML concepts.",
            category="Data Science",
            difficulty="Advanced",
            tags=["ml", "data", "ai"],
            duration=10,
            rating=4.8,
            price=49.99
        )
    ]

# ✅ Test: Adding courses to vector store
def test_add_courses(temp_vector_store, sample_courses):
    temp_vector_store.add_courses(sample_courses)
    
    results = temp_vector_store.collection.peek()
    
    assert len(results["documents"]) == 2, "Expected 2 documents in the vector store"
    assert results["ids"] == ["1", "2"], "Expected course IDs to match"

# ✅ Test: Searching similar courses
def test_search_similar_courses(temp_vector_store, sample_courses):
    temp_vector_store.add_courses(sample_courses)
    
    query = "I want to learn Python"
    user_preferences = {
        "preferred_categories": ["Programming"],
        "preferred_difficulty": "Beginner",
        "learning_style": "hands-on"
    }

    results = temp_vector_store.search_similar_courses(query, user_preferences, n_results=2)
    
    assert isinstance(results, list), "Result should be a list"
    assert len(results) > 0, "Expected at least one search result"

    for course in results:
        assert "course_id" in course
        assert "title" in course
        assert "similarity_score" in course
        assert 0 <= course["similarity_score"] <= 1, "Similarity score should be in [0, 1]"
