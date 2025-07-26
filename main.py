import streamlit as st
from engine.recommendation_engine import CourseRecommendationEngine
import uuid
from utils.twilio_client import send_whatsapp_message
from utils.youtube_search import YouTubeSearch
import os
from dotenv import load_dotenv

load_dotenv()
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
youtube_client = YouTubeSearch(YOUTUBE_API_KEY)
st.set_page_config(page_title="🎓 AI Course Recommender", layout="wide", initial_sidebar_state="expanded")

engine = CourseRecommendationEngine()

# --- Sidebar: User Profile Management ---
st.sidebar.title("👤 User Profile")

# Initialize session state keys if missing
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "user_name" not in st.session_state:
    st.session_state.user_name = None

with st.sidebar.form("profile_form", clear_on_submit=False):
    user_id_input = st.text_input("User ID (unique)", value=st.session_state.user_id or "")
    name_input = st.text_input("Name", value=st.session_state.user_name or "")
    create_btn = st.form_submit_button("Create Profile")
    load_btn = st.form_submit_button("Load Profile")

if create_btn:
    if not user_id_input.strip() or not name_input.strip():
        st.sidebar.error("Please enter both User ID and Name.")
    else:
        result = engine.create_user_profile(user_id_input.strip(), name_input.strip(), initial_feedback="")
        if "error" in result:
            st.sidebar.error(result["error"])
        else:
            st.sidebar.success(f"Profile created for {name_input.strip()}. You can now get recommendations!")
            st.session_state.user_id = user_id_input.strip()
            st.session_state.user_name = name_input.strip()

if load_btn:
    if not user_id_input.strip():
        st.sidebar.error("Please enter User ID to load profile.")
    else:
        user = engine.db.get_user(user_id_input.strip())
        if user:
            st.session_state.user_id = user_id_input.strip()
            st.session_state.user_name = user['name']
            st.sidebar.success(f"Welcome back, {user['name']}!")
        else:
            st.sidebar.error("User not found. Please create a profile.")

if st.session_state.user_id:
    if st.sidebar.button("Logout"):
        st.session_state.user_id = None
        st.session_state.user_name = None
       

# --- Main content ---
st.title("🎓 AI Course Recommender System")

if not st.session_state.user_id:
    st.info("Please create a profile or load an existing profile using the sidebar.")
else:
    st.markdown(f"### Welcome, **{st.session_state.user_name}**!")

    # Preferences form
    with st.form("preferences_form"):
        st.subheader("Tell us about your learning preferences")
        learning_prefs = st.text_area("Describe your learning preferences to get tailored recommendations", height=120)
        submitted = st.form_submit_button("Update Preferences and Get Recommendations")

    if submitted:
        if not learning_prefs.strip():
            st.warning("Please enter your learning preferences to proceed.")
        else:
            with st.spinner("Updating preferences and generating recommendations..."):
                new_prefs = engine.llm.extract_preferences(learning_prefs)
                engine.db.update_user_preferences(st.session_state.user_id, new_prefs)
                st.success("Preferences updated successfully!")
                
                recs = engine.get_personalized_recommendations(st.session_state.user_id, learning_prefs, num_recommendations=5)
                st.session_state.recommendations = recs.get("recommendations", [])

    # Button to load recommendations based on previous interactions (no query input)
    if st.button("Load Recommendations Based on Previous Interactions"):
        with st.spinner("Loading recommendations from your history..."):
            recs = engine.get_personalized_recommendations(st.session_state.user_id, query="", num_recommendations=5)
            if "error" in recs:
                st.error(recs["error"])
            else:
                st.session_state.recommendations = recs.get("recommendations", [])
                st.success("Loaded recommendations based on your past interactions!")

    # Show recommendations if available
    recommendations = st.session_state.get("recommendations", [])

    if recommendations:
        st.header("Recommended Courses For You")
        for i, course in enumerate(recommendations, 1):
            with st.expander(f"{i}. {course['title']}"):
                cols = st.columns([5, 2, 2])
                cols[0].markdown(f"**Category:** `{course['category']}`")
                cols[1].markdown(f"**Difficulty:** `{course['difficulty'].capitalize()}`")

                st.markdown(f"**Explanation:** {course['explanation']}")
                st.markdown(f"**Similarity Score:** {course['similarity_score']:.2f}")

                # YouTube Video Embed
                search_query = f"{course['title']} introduction"
                video_id = youtube_client.search_video(search_query)
                if video_id:
                    st.markdown("**🎥 YouTube Source:**")
                    st.video(f"https://www.youtube.com/embed/{video_id}")
                else:
                    st.warning("No video found for this course.")

                    # WhatsApp Option
        st.divider()
        st.subheader("📲 Send Recommendations via WhatsApp")
        phone_input = st.text_input("Enter WhatsApp Number (e.g., +44XXXXXXXXX)")
        if st.button("📤 Send to WhatsApp") and phone_input:
            with st.spinner("Sending via WhatsApp..."):
                try:
                    msg = f"📚 *Your Course Recommendations:*\n\n"
                    for i, course in enumerate(recommendations, 1):
                        msg += f"{i}. *{course['title']}* ({course['difficulty'].capitalize()})\n"
                        msg += f"{course['explanation']}\n"

                        # Add YouTube search and link
                        search_query = f"{course['title']} introduction"
                        video_id = youtube_client.search_video(search_query)
                        if video_id:
                            msg += f"🎥 Watch: https://www.youtube.com/watch?v={video_id}\n"

                        msg += "---\n"

                    send_whatsapp_message(phone_input.strip(), msg)
                    st.success("✅ Sent to WhatsApp!")
                except Exception as e:
                    st.error(f"❌ Error sending message: {e}")


    st.header("Submit Feedback on a Course")
    with st.form("feedback_form"):
        course_id_fb = st.text_input("Course ID to give feedback")
        rating_fb = st.slider("Rating (1-5)", 1, 5, 4)
        feedback_fb = st.text_area("Your feedback")
        submit_fb_btn = st.form_submit_button("Submit Feedback")

    if submit_fb_btn:
        if not course_id_fb.strip():
            st.error("Please enter a valid course ID.")
        else:
            with st.spinner("Submitting feedback..."):
                res = engine.process_user_feedback(st.session_state.user_id, course_id_fb.strip(), rating_fb, feedback_fb)
                st.success(res['message'])

