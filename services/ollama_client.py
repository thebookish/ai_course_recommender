import json
import requests
from utils.logger import logger


class OllamaClient:
    """Handles communication with Ollama LLM"""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "tinyllama"):
        self.base_url = base_url
        self.model = model

    def generate_response(self, prompt: str) -> str:
        """Generate response from Ollama"""
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                }
            )
            response.raise_for_status()
            return response.json()["response"]
        except Exception as e:
            logger.error(f"Error calling Ollama: {e}")
            return "Sorry, I couldn't generate a response at this time."

    def extract_preferences(self, user_feedback: str) -> dict:
        """Extract learning preferences from user feedback using LLM"""
        prompt = f"""
Analyze the following user feedback about their learning experience and extract structured learning preferences. 

Feedback: "{user_feedback}"

Return ONLY a JSON object in this format:
{{
    "preferred_categories": ["category1", "category2"],
    "preferred_difficulty": "beginner/intermediate/advanced",
    "learning_style": "visual/auditory/hands-on/theoretical",
    "preferred_duration": "short/medium/long",
    "budget_preference": "free/low/medium/high",
    "goals": ["goal1", "goal2"]
}}
        """
        response = self.generate_response(prompt)

        try:
            # Extract JSON block from LLM response
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end != -1:
                return json.loads(response[start:end])
        except Exception as e:
            logger.warning(f"Failed to parse JSON from LLM response: {e}")

        # Fallback if LLM fails
        return {
            "preferred_categories": ["general"],
            "preferred_difficulty": "intermediate",
            "learning_style": "hands-on",
            "preferred_duration": "medium",
            "budget_preference": "medium",
            "goals": ["skill development"]
        }
    def generate_wp_response(self, prompt: str) -> str:
        """
        Generate a response using the Ollama API, ensuring that the reply stays within 
        the context of courses, learning, or skill development—even when unrelated questions are asked.
        """
        try:
            # Add a wrapper prompt to steer the model's response
            wrapped_prompt = (
                f"The user asked: \"{prompt}\"\n\n"
                "As an AI learning assistant, your job is to always respond with something helpful, "
                "but gently tie it back to education, learning paths, or skill-building courses where appropriate.\n"
                "If the user's query is not directly course-related, give a brief answer and then relate it "
                "to how learning something relevant can help them.\n\n"
                "Your response:"
            )

            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": wrapped_prompt,
                    "stream": False
                }
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "Sorry, no response generated.")
        
        except requests.RequestException as e:
            logger.error(f"Request error calling Ollama API: {e}")
            return "Sorry, I couldn't generate a response at this time."
        except Exception as e:
            logger.error(f"Unexpected error in generate_wp_response: {e}")
            return "Sorry, something went wrong generating the response."

            
