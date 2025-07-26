from flask import Flask, request
import sys, os
import threading
import random

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from services.ollama_client import OllamaClient
from engine.recommendation_engine import CourseRecommendationEngine
from utils.twilio_client import send_whatsapp_message
from db.database_manager import DatabaseManager
from utils.youtube_search import YouTubeSearch
from dotenv import load_dotenv

app = Flask(__name__)
engine = CourseRecommendationEngine()
db = DatabaseManager()
load_dotenv()
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
youtube_client = YouTubeSearch(YOUTUBE_API_KEY)
pending_onboarding = {}

def process_recommendation(user_id, query):
    user = db.get_user(user_id)
    if not user:
        send_whatsapp_message(user_id, "❌ Error: User not found. Please type 'start' to begin.")
        return

    engine.create_user_profile(user_id, user['name'], user['preferences'])
    recs = engine.get_personalized_recommendations(user_id, query, 3)

    if "error" in recs:
        send_whatsapp_message(user_id, "❌ Error: " + recs["error"])
    else:
        text = "📚 Top Course Recommendations:\n\n"
        for i, course in enumerate(recs["recommendations"], 1):
            text += f"{i}. *{course['title']}* ({course['difficulty'].capitalize()})\n"
            text += f"{course['explanation']}\n"         
 
            # Add YouTube search and link
            search_query = f"{course['title']} introduction"
            yt_link = youtube_client.search_video(search_query)
            if yt_link:
                text += f"🎥 Watch: https://www.youtube.com/watch?v={yt_link}\n"

            text += "---\n"
        send_whatsapp_message(user_id, text)

@app.route("/whatsapp", methods=['POST'])
def whatsapp_reply():
    msg = request.form.get('Body').strip()
    user_id = request.form.get('From').replace("whatsapp:", "")
    msg_lower = msg.lower()

    user = db.get_user(user_id)

    if msg_lower == "start":
        pending_onboarding[user_id] = {"step": 1, "data": {}}
        send_whatsapp_message(user_id, "👋 Welcome! What's your name?")
        return "OK"

    elif user_id in pending_onboarding:
        step = pending_onboarding[user_id]["step"]
        data = pending_onboarding[user_id]["data"]

        if step == 1:
            data["name"] = msg
            pending_onboarding[user_id]["step"] += 1
            send_whatsapp_message(user_id, "🎯 What's your learning goal? (e.g., get a job, explore AI)")
            return "OK"

        elif step == 2:
            data["goal"] = msg
            pending_onboarding[user_id]["step"] += 1
            send_whatsapp_message(user_id, "📚 What topics are you interested in?")
            return "OK"

        elif step == 3:
            data["interests"] = msg
            pending_onboarding[user_id]["step"] += 1
            send_whatsapp_message(user_id, "📈 Your skill level? (beginner/intermediate/advanced)")
            return "OK"

        elif step == 4:
            data["level"] = msg
            pending_onboarding[user_id]["step"] += 1
            send_whatsapp_message(user_id, "⏱️ Weekly time commitment? (e.g., 5 hours)")
            return "OK"

        elif step == 5:
            data["time"] = msg
            preferences = {
                "goal": data.get("goal", ""),
                "interest": data.get("interests", ""),
                "preferred_difficulty": data.get("level", "").lower(),
                "time_commitment": data.get("time", "")
            }

            db.create_user(user_id, data["name"], preferences)

            summary_text = (
                f"📝 Here's what you shared:\n"
                f"- 👤 Name: {data['name']}\n"
                f"- 🎯 Goal: {preferences['goal']}\n"
                f"- 📚 Interests: {preferences['interest']}\n"
                f"- 📈 Skill Level: {preferences['preferred_difficulty']}\n"
                f"- ⏱️ Time Commitment: {preferences['time_commitment']}\n"
            )
            send_whatsapp_message(user_id, summary_text)

            send_whatsapp_message(
                user_id,
                f"✅ Thanks {data['name']}! Your preferences have been saved.\n"
                "Generating your personalized course recommendations now... ⏳"
            )

            onboarding_query = f"{preferences['goal']} with focus on {preferences['interest']}"
            db.add_interaction(user_id, "onboarding_query", "query", feedback=onboarding_query)
            threading.Thread(target=process_recommendation, args=(user_id, onboarding_query)).start()

            del pending_onboarding[user_id]
            return "OK"


    if not user:
        send_whatsapp_message(user_id, "👋 Please type `start` to begin onboarding.")
        return "OK"

    # Commands
    if msg_lower.startswith("learn "):
        query = msg[6:].strip()
        if not query:
            send_whatsapp_message(user_id, "⚠️ Please specify what you want to learn. Example: learn python for beginners")
        else:
            send_whatsapp_message(user_id, "⏳ Generating your personalized recommendations, please wait...")
            db.add_interaction(user_id, "manual_query", "query", feedback=query)
            threading.Thread(target=process_recommendation, args=(user_id, query)).start()
        return "OK"

    elif msg_lower == "recommend again":
        interactions = db.get_user_interactions(user_id)
        last_query = next((i["feedback"] for i in interactions if i["interaction_type"] == "query"), None)
        if last_query:
            send_whatsapp_message(user_id, f"🔁 Recommending courses for your last goal: *{last_query}*")
            send_whatsapp_message(user_id, "⏳ Please wait while we generate recommendations...")
            threading.Thread(target=process_recommendation, args=(user_id, last_query)).start()
        else:
            send_whatsapp_message(user_id, "❗ You haven't asked for any course recommendations yet. Try: learn <topic>")

    elif msg_lower == "history":
        interactions = db.get_user_interactions(user_id)
        goals = [i["feedback"] for i in interactions if i["interaction_type"] == "query"]
        if goals:
            history = "🕘 Your Previous Learning Goals:\n" + "\n".join(f"{i+1}. {goal}" for i, goal in enumerate(goals))
            send_whatsapp_message(user_id, history)
        else:
            send_whatsapp_message(user_id, "🔎 No learning history found yet.")

    elif msg_lower.startswith("feedback"):
        parts = msg.split(" ", 2)
        if len(parts) >= 3:
            course_id = parts[1]
            fb_text = parts[2]
            db.add_interaction(user_id, course_id, "feedback", feedback=fb_text)
            engine.process_user_feedback(user_id, course_id, 5, fb_text)
            send_whatsapp_message(user_id, "✅ Thank you! Feedback submitted.")
        else:
            send_whatsapp_message(user_id, "⚠️ Format: feedback <course_id> <your feedback>")

    elif msg_lower == "help":
        help_msg = (
            "👋 Here's what I can do:\n"
            "- `start`: Get started\n"
            "- `learn <your goal>`: Get course recommendations\n"
            "- `recommend again`: Reuse your last learning goal\n"
            "- `history`: View your learning goals\n"
            "- `feedback <course_id> <your feedback>`: Submit feedback\n\n"
            "🧠 Let's start with your preferences.\n"
            "Type: `preference data science, beginner`"
        )
        send_whatsapp_message(user_id, help_msg)

    elif msg_lower.startswith("preference"):
        prefs = msg[len("preference"):].strip()
        if prefs:
            user["preferences"]["custom"] = prefs
            db.update_user_preferences(user_id, user["preferences"])
            send_whatsapp_message(user_id, f"✅ Preferences saved: {prefs}\nFetching top course recommendations...")

            # Auto-generate recommendations based on new preferences
            engine.create_user_profile(user_id, user["name"], user["preferences"])
            recs = engine.get_personalized_recommendations(user_id, prefs, 3)

            if "error" in recs:
                send_whatsapp_message(user_id, "❌ Error: " + recs["error"])
            else:
                text = "📚 Top Course Recommendations:\n\n"
                for i, course in enumerate(recs["recommendations"], 1):
                    text += f"{i}. {course['title']} ({course['difficulty']})\n{course['explanation']}\n---\n"
                send_whatsapp_message(user_id, text)

        else:
            send_whatsapp_message(user_id, "⚠️ Please include your preferences. Example: `preference web dev, intermediate`")

    elif "my preference" in msg_lower:
        prefs = user.get("preferences", {})
        if prefs:
            pref_text = "\n".join([f"- {k}: {v}" for k, v in prefs.items()])
            send_whatsapp_message(user_id, f"📌 Your current preferences:\n{pref_text}")
        else:
            send_whatsapp_message(user_id, "ℹ️ You haven't set any preferences yet. Type: `preference python, beginner`")

    elif "who are you" in msg_lower:
        send_whatsapp_message(user_id, "🤖 I'm your AI learning buddy! I recommend personalized courses based on your goals. Type `help` to see more.")

    elif any(keyword in msg_lower for keyword in ["thank", "cool", "awesome", "great", "wow"]):
        send_whatsapp_message(user_id, random.choice([
            "😊 You're welcome!",
            "🚀 Glad you liked it!",
            "Always here to help!",
            "Let's keep learning! 💡"
        ]))

    else:
        # Call fallback generative response
        wp_engine = OllamaClient()

        fallback_prompt = (
            f"The user asked: \"{msg}\"\n\n"
            "Please provide a helpful and informative reply. Then, try to gently guide the user back to learning, "
            "courses, or skill development. If possible, suggest a topic to explore.\n"
        )

        ai_reply = wp_engine.generate_wp_response(fallback_prompt)
        send_whatsapp_message(user_id, ai_reply)

    return "OK"

if __name__ == "__main__":
    app.run(debug=True, port=5000)
