from dotenv import load_dotenv
load_dotenv()
import base64
import streamlit as st
import os
import io
from PIL import Image
import pdf2image
import google.generativeai as genai
import time
import re

# Configure the API
genai.configure(api_key='AIzaSyCPsq7CI-END1Yxz1SxOaDdUvkVao64fRA')

# Set up session state for chat history
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
    
if 'additional_skills' not in st.session_state:
    st.session_state.additional_skills = ""

if 'hobbies' not in st.session_state:
    st.session_state.hobbies = ""

if 'button_clicked' not in st.session_state:
    st.session_state.button_clicked = False

if 'conversation_stage' not in st.session_state:
    st.session_state.conversation_stage = "greeting"

# New session state for chatbot visibility
if 'show_chatbot' not in st.session_state:
    st.session_state.show_chatbot = False

def get_gemini_response(input_prompt, pdf_content, job_description, additional_skills="", hobbies=""):
    # Use the updated model name
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # Create a combined prompt that includes additional skills and hobbies if provided
    combined_prompt = f"{input_prompt}\n\n"
    
    if additional_skills:
        combined_prompt += f"Additional skills provided by the candidate: {additional_skills}\n\n"
    
    if hobbies:
        combined_prompt += f"Hobbies and interests provided by the candidate: {hobbies}\n\n"
    
    combined_prompt += f"Job Description: {job_description}"
    
    response = model.generate_content([combined_prompt, pdf_content[0]])
    return response.text

def input_pdf_setup(uploaded_file):
    if uploaded_file is not None:
        # Provide the path to the poppler bin directory
        poppler_path = r'C:\Users\bhavi\OneDrive\Desktop\poppler\poppler-24.08.0\Library\bin'  # Adjust this path

        # Convert the PDF to image
        images = pdf2image.convert_from_bytes(uploaded_file.read(), poppler_path=poppler_path)
        
        first_page = images[0]
        
        # Convert to bytes
        img_byte_arr = io.BytesIO()
        first_page.save(img_byte_arr, format='JPEG')
        img_byte_arr = img_byte_arr.getvalue()
        
        pdf_parts = [
            {
                "mime_type": "image/jpeg",
                "data": base64.b64encode(img_byte_arr).decode()  # encode to base64
            }
        ]
        return pdf_parts
    else:
        raise FileNotFoundError("No file uploaded")

def add_chat_message(role, content):
    st.session_state.chat_history.append({"role": role, "content": content})

def is_skill(text):
    # Common skill-related keywords
    skill_keywords = [
        "proficient", "experience", "knowledge", "certified", "trained", 
        "developed", "programming", "language", "software", "tool", "framework",
        "analysis", "design", "implementation", "management", "leadership",
        "communication", "teamwork", "problem-solving", "critical thinking",
        "coding", "development", "expertise", "competent", "skilled"
    ]
    
    # Check if any skill keywords appear in the text
    for keyword in skill_keywords:
        if keyword.lower() in text.lower():
            return True
    
    # Check for programming languages, tools, or frameworks
    tech_pattern = r'\b(python|java|javascript|c\+\+|sql|react|node|aws|azure|docker|kubernetes|excel|word|powerpoint|photoshop|illustrator|figma)\b'
    if re.search(tech_pattern, text.lower()):
        return True
    
    return False

def is_hobby(text):
    # Common hobby-related keywords
    hobby_keywords = [
        "hobby", "interest", "enjoy", "passion", "leisure", "recreational",
        "playing", "reading", "watching", "collecting", "traveling", "hiking",
        "music", "sports", "games", "art", "cooking", "gardening", "photography",
        "love to", "like to", "free time", "weekend", "fun"
    ]
    
    # Check if any hobby keywords appear in the text
    for keyword in hobby_keywords:
        if keyword.lower() in text.lower():
            return True
    
    return False

def process_user_input(user_input):
    # Check conversation stage and respond accordingly
    if st.session_state.conversation_stage == "greeting":
        # First interaction - greet the user
        st.session_state.conversation_stage = "gathering_info"
        return "Hello! I'm your AI assistant. I can help you add skills and hobbies that might not be in your resume. Would you like to tell me about your skills or hobbies?"
    
    # Process the input to determine if it's a skill, hobby, or general conversation
    if is_skill(user_input):
        st.session_state.additional_skills += f" {user_input}"
        return f"Great! I've added these skills to your profile: {user_input}\n\nDo you have any other skills or perhaps some hobbies you'd like to share?"
    
    elif is_hobby(user_input):
        st.session_state.hobbies += f" {user_input}"
        return f"Wonderful! I've added these hobbies/interests to your profile: {user_input}\n\nAny other hobbies or skills you'd like to mention?"
    
    # General conversation
    else:
        # Common questions handling
        if "help" in user_input.lower():
            return "I can help you add skills and hobbies to your profile that might not be in your resume. Just tell me about your skills or interests, and I'll categorize and save them for later use in your resume analysis."
        
        elif any(word in user_input.lower() for word in ["hello", "hi", "hey"]):
            return "Hello there! How can I help you today? Would you like to tell me about your skills or hobbies?"
        
        elif "thank" in user_input.lower():
            return "You're welcome! Is there anything else I can help you with?"
        
        elif any(word in user_input.lower() for word in ["bye", "goodbye", "exit"]):
            return "It was nice chatting with you! Your skills and hobbies have been saved. Good luck with your job application!"
        
        # Check if it seems like they're trying to add information but we're not sure what type
        elif len(user_input.split()) > 3:  # If it's a longer message, ask for clarification
            return f"I'm not sure if you're telling me about skills or hobbies. Could you clarify if '{user_input}' is a skill or a hobby/interest?"
        
        # Default response
        else:
            return "I'm here to help you add skills and hobbies to your profile. Could you tell me more about your professional skills or personal interests?"

# Function to handle sending messages in chat
def on_send_message():
    user_input = st.session_state.user_message
    if user_input:
        # Add user message to chat
        add_chat_message("user", user_input)
        
        # Process the message and get a response
        bot_response = process_user_input(user_input)
        
        # Add bot response to chat
        add_chat_message("bot", bot_response)
        
        # Clear the input
        st.session_state.user_message = ""

# Function to clear skills and hobbies
def clear_skills():
    st.session_state.additional_skills = ""
    st.session_state.hobbies = ""

# Toggle chatbot visibility
def toggle_chatbot():
    st.session_state.show_chatbot = not st.session_state.show_chatbot

# Function to get base64 encoded local video
def get_base64_video(video_path):
    try:
        with open(video_path, "rb") as video_file:
            video_bytes = video_file.read()
            base64_video = base64.b64encode(video_bytes).decode()
            return base64_video
    except Exception as e:
        st.error(f"Error loading video: {e}")
        return None

# Function to add background video using local file
def set_background_video(video_path=None):
    if video_path is None:
        video_path = r"C:\Users\bhavi\OneDrive\Desktop\5971459-uhd_4096_2160_25fps.mp4"  # Default video
    
    try:
        # Get base64 encoded video
        encoded_video = get_base64_video(video_path)
        
        if encoded_video:
            # Create a video element in the background with CSS
            video_html = f"""
            <style>
            #video-bg {{
                position: fixed;
                right: 0;
                bottom: 0;
                min-width: 100%;
                min-height: 100%;
                width: 100%;
                height: 100%;
                object-fit: cover;
                z-index: -1;
                opacity: 0.35;  /* Increased from 0.15 to 0.35 for less transparency */
                pointer-events: none;
            }}
            
            .stApp {{
                background: transparent;
            }}
            </style>
            
            <video autoplay loop muted playsinline id="video-bg">
                <source src="data:video/mp4;base64,{encoded_video}" type="video/mp4">
            </video>
            """
            st.markdown(video_html, unsafe_allow_html=True)
        else:
            # Fallback to gradient background if video loading fails
            fallback_css = """
            <style>
            .stApp {
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            }
            </style>
            """
            st.markdown(fallback_css, unsafe_allow_html=True)
            
    except Exception as e:
        st.error(f"Error setting background video: {e}")
        # Fallback to gradient background
        fallback_css = """
        <style>
        .stApp {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        }
        </style>
        """
        st.markdown(fallback_css, unsafe_allow_html=True)

# Custom CSS for background and styling
def set_custom_styling():
    background_css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;700&family=Poppins:wght@300;400;500;700&display=swap');
    
    .card {
        background-color: rgba(255, 255, 255, 0.85);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 8px 15px rgba(0, 0, 0, 0.1);
        transition: transform 0.3s ease;
    }
    
    .card:hover {
        transform: translateY(-5px);
    }
    
    .title-container {
        background: linear-gradient(90deg, #4b6cb7 0%, #182848 100%);
        padding: 25px;
        border-radius: 15px;
        color: white;
        margin-bottom: 30px;
        text-align: center;
        box-shadow: 0 10px 20px rgba(27, 40, 72, 0.2);
        width: 100vw;
        margin-left: calc(-50vw + 50%);
        box-sizing: border-box;
    }
    
    .title-container h1 {
        font-family: 'Montserrat', sans-serif;
        font-weight: 700;
        letter-spacing: 2px;
        text-transform: uppercase;
        margin: 0;
        padding: 0;
        font-size: 3em;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
    }
    
    .title-container p {
        font-family: 'Poppins', sans-serif;
        margin-top: 10px;
        font-size: 1.2em;
        opacity: 0.9;
    }
    
    .chat-message {
        padding: 15px;
        border-radius: 15px;
        margin-bottom: 15px;
        display: flex;
        flex-direction: column;
        font-family: 'Poppins', sans-serif;
        animation: fadeIn 0.5s;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .user-message {
        background-color: #E3F2FD;
        margin-left: 20%;
        border-top-right-radius: 0;
        border-left: 3px solid #4b6cb7;
    }
    
    .bot-message {
        background-color: white;
        margin-right: 20%;
        border-top-left-radius: 0;
        border-right: 3px solid #4b6cb7;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
    }
    
    .button-container {
        display: flex;
        justify-content: space-between;
        gap: 20px;
        margin: 20px 0;
    }
    
    .custom-button {
        background-color: #4b6cb7;
        color: white;
        padding: 12px 24px;
        border-radius: 8px;
        border: none;
        cursor: pointer;
        transition: all 0.3s;
        font-family: 'Poppins', sans-serif;
        font-weight: 500;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        font-size: 14px;
    }
    
    .custom-button:hover {
        background-color: #182848;
        transform: translateY(-2px);
        box-shadow: 0 5px 10px rgba(27, 40, 72, 0.2);
    }
    
    .result-container {
        background-color: rgba(255, 255, 255, 0.9);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 25px;
        margin-top: 30px;
        box-shadow: 0 8px 15px rgba(0, 0, 0, 0.1);
        font-family: 'Poppins', sans-serif;
    }
    
    .result-container h3 {
        color: #4b6cb7;
        border-bottom: 2px solid #4b6cb7;
        padding-bottom: 10px;
        margin-bottom: 20px;
    }
    
    .stTextInput > div > div > input {
        background-color: white;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        padding: 12px 15px;
        font-family: 'Poppins', sans-serif;
        transition: all 0.3s;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #4b6cb7;
        box-shadow: 0 0 0 2px rgba(75, 108, 183, 0.2);
    }
    
    .stTab {
        font-family: 'Montserrat', sans-serif;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }

    .stTabs [data-baseweb="tab"] {
        background-color: #f5f7fa;
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        font-family: 'Montserrat', sans-serif;
    }

    .stTabs [aria-selected="true"] {
        background-color: #4b6cb7 !important;
        color: white !important;
    }
    
    /* Skills and hobbies display */
    .profile-section {
        background-color: #f8f9fa;
        border-left: 4px solid #4b6cb7;
        padding: 15px;
        margin: 10px 0;
        border-radius: 0 8px 8px 0;
    }
    
    /* Button alignment fix */
    .equal-buttons {
        display: flex;
        justify-content: space-between;
        gap: 10px;
    }
    
    .equal-buttons > div {
        flex: 1;
    }
    
    /* Chatbot button styling */
    .chat-button {
        position: fixed;
        bottom: 30px;
        right: 30px;
        width: 60px;
        height: 60px;
        border-radius: 50%;
        background-color: #4b6cb7;
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        z-index: 1000;
        transition: all 0.3s ease;
    }
    
    .chat-button:hover {
        transform: scale(1.1);
        background-color: #182848;
    }
    
    .chat-button i {
        font-size: 24px;
    }
    
    /* Chat container styling */
    .chat-container {
        position: fixed;
        bottom: 30px;
        right: 30px;
        width: 50vw;
        height: 80vh;
        background-color: rgba(255, 255, 255, 0.95);
        border-radius: 15px;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
        z-index: 1000;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        animation: slideIn 0.3s ease-in-out;
    }
    
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    .chat-header {
        background: linear-gradient(90deg, #4b6cb7 0%, #182848 100%);
        padding: 15px;
        color: white;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .chat-header h3 {
        margin: 0;
        font-family: 'Montserrat', sans-serif;
    }
    
    .close-chat {
        background: none;
        border: none;
        color: white;
        font-size: 20px;
        cursor: pointer;
    }
    
    .chat-messages {
        flex: 1;
        overflow-y: auto;
        padding: 20px;
    }
    
    .chat-input {
        padding: 15px;
        border-top: 1px solid #e0e0e0;
        display: flex;
    }
    
    .chat-input input {
        flex: 1;
        padding: 10px;
        border: 1px solid #e0e0e0;
        border-radius: 5px;
        margin-right: 10px;
    }
    
    .send-button {
        background-color: #4b6cb7;
        color: white;
        border: none;
        border-radius: 5px;
        padding: 10px 15px;
        cursor: pointer;
    }
    
    /* Split screen when chat is active */
    .split-container {
        display: flex;
        width: 100%;
    }
    
    .main-content {
        flex: 1;
        padding-right: 10px;
        transition: all 0.3s ease;
    }
    
    .main-content.with-chat {
        flex: 0.5;
    }
    
    .no-scroll {
        overflow: hidden;
    }
    </style>
    
    <!-- Font Awesome Icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    """
    st.markdown(background_css, unsafe_allow_html=True)

    # Your existing CSS code...
    
    # Add this JavaScript for automatic scrolling to results
    auto_scroll_js = """
    <script>
    // Function to scroll to results when they appear
    function setupResultsScrolling() {
        // Watch for changes to detect when results appear
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.addedNodes.length) {
                    // Check if any added nodes contain the result container
                    const resultContainer = document.querySelector('.result-container');
                    if (resultContainer) {
                        // Scroll to the result container
                        resultContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
                }
            });
        });
        
        // Start observing the document body for changes
        observer.observe(document.body, { childList: true, subtree: true });
    }
    
    // Call the setup function when the page is loaded
    document.addEventListener('DOMContentLoaded', setupResultsScrolling);
    
    // Also try to set it up now in case the page is already loaded
    setupResultsScrolling();
    </script>
    """
    
    st.markdown(auto_scroll_js, unsafe_allow_html=True)

# Modify the toggle_chatbot function and event listener to ensure proper communication
# Modified toggle_chatbot function without experimental_rerun
def toggle_chatbot():
    st.session_state.show_chatbot = not st.session_state.show_chatbot
    # We'll use a different approach instead of experimental_rerun

# Modify the add_chat_button function
def add_chat_button():
    chat_button_html = """
    <div class="chat-button" id="chatToggleBtn">
        <i class="fas fa-comments"></i>
    </div>
    
    <script>
    // Wait for the DOM to be fully loaded
    document.addEventListener('DOMContentLoaded', function() {
        const chatBtn = document.getElementById('chatToggleBtn');
        if (chatBtn) {
            chatBtn.addEventListener('click', function() {
                // Send message to Streamlit
                window.parent.postMessage({type: 'toggleChatbot'}, '*');
            });
        }
    });
    </script>
    """
    st.markdown(chat_button_html, unsafe_allow_html=True)
    
    # Hidden button to be clicked by JS
    if st.button("Toggle Chatbot", key="toggle_chatbot_hidden", on_click=toggle_chatbot):
        pass

# In your main function, replace the existing message listener with this improved version
def main():
    # Add the improved listener for chat button clicks
    st.markdown("""
    <script>
    // Create a function to handle the postMessage event
    window.addEventListener('message', function(e) {
        if (e.data && e.data.type === 'toggleChatbot') {
            // Find and click the hidden button
            setTimeout(function() {
                const buttons = document.querySelectorAll('button');
                for (let i = 0; i < buttons.length; i++) {
                    if (buttons[i].innerText === 'Toggle Chatbot') {
                        buttons[i].click();
                        break;
                    }
                }
            }, 100); // Small delay to ensure DOM is ready
        }
    });
    </script>
    """, unsafe_allow_html=True)
    
    # Set different background videos based on button clicks
    if 'current_video' not in st.session_state:
        st.session_state.current_video = r"C:\Users\bhavi\OneDrive\Desktop\5971459-uhd_4096_2160_25fps.mp4"
    
    set_background_video(st.session_state.current_video)
    set_custom_styling()
    
    # Title with gradient background and improved font - full width
    st.markdown('<div class="title-container"><h1>HireSphere</h1><p>Advanced ATS System with AI-Powered Resume Analysis</p></div>', unsafe_allow_html=True)
    
    # Split screen layout when chatbot is active
    if st.session_state.show_chatbot:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            main_content()
        
        with col2:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Skills & Hobbies Chatbot")
            chatbot_container()
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        main_content()
        # Add the chat button
        add_chat_button()

# Updated on_send_message function without experimental_rerun
def on_send_message():
    user_input = st.session_state.user_message
    if user_input:
        # Add user message to chat
        add_chat_message("user", user_input)
        
        # Process the message and get a response
        bot_response = process_user_input(user_input)
        
        # Add bot response to chat
        add_chat_message("bot", bot_response)
        
        # Clear the input
        st.session_state.user_message = ""
        
        # We won't use experimental_rerun - Streamlit will automatically rerun

# Improve chatbot_container with auto-scroll JavaScript
def chatbot_container():
    if st.session_state.show_chatbot:
        # Display greeting message if first visit
        if len(st.session_state.chat_history) == 0:
            welcome_msg = "Hello! I'm your AI assistant. I can help you add skills and hobbies that might not be in your resume. Would you like to tell me about your skills or hobbies?"
            add_chat_message("bot", welcome_msg)
            st.session_state.conversation_stage = "gathering_info"
        
        # Add JavaScript for auto-scrolling chat
        st.markdown("""
        <script>
        // Function to scroll chat to bottom
        function scrollChatToBottom() {
            const chatMessages = document.querySelectorAll('.chat-message');
            if (chatMessages.length > 0) {
                chatMessages[chatMessages.length - 1].scrollIntoView({ behavior: 'smooth' });
            }
        }
        
        // Set up a MutationObserver to detect when new chat messages are added
        const observer = new MutationObserver(function(mutations) {
            scrollChatToBottom();
        });
        
        // Start observing the document with the configured parameters
        observer.observe(document.body, { childList: true, subtree: true });
        
        // Also try to scroll initially
        setTimeout(scrollChatToBottom, 500);
        </script>
        """, unsafe_allow_html=True)
        
        # Display chat history
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                st.markdown(f'<div class="chat-message user-message"><p>{message["content"]}</p></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-message bot-message"><p>{message["content"]}</p></div>', unsafe_allow_html=True)
        
        # Input for new message with callback
        st.text_input(
            "Chat with me about your skills and hobbies:", 
            key="user_message", 
            on_change=on_send_message
        )
        
        # Display current additional skills and hobbies
        # Rest of your existing code...

def main_content():
    # Main content (Resume Analysis)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Upload Resume & Job Description")
    
    # Job description input
    input_text = st.text_area("Enter the Job Description:", key="input", height=150)
    
    # Resume upload
    uploaded_file = st.file_uploader("Upload your resume (PDF)...", type=["pdf"])
    
    if uploaded_file is not None:
        success_message = st.success("✅ Resume uploaded successfully!")
        
    # Initialize button states if not exists
    if 'submit1_clicked' not in st.session_state:
        st.session_state.submit1_clicked = False
    if 'submit2_clicked' not in st.session_state:
        st.session_state.submit2_clicked = False
    if 'submit3_clicked' not in st.session_state:
        st.session_state.submit3_clicked = False
    
    # Buttons with callbacks
    st.markdown('<div class="equal-buttons">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📋 Analyze Resume", use_container_width=True, key="analyze_btn"):
            st.session_state.submit1_clicked = True
            st.session_state.submit2_clicked = False
            st.session_state.submit3_clicked = False
    
    with col2:
        if st.button("🚀 Improvement Suggestions", use_container_width=True, key="improve_btn"):
            st.session_state.submit1_clicked = False
            st.session_state.submit2_clicked = True
            st.session_state.submit3_clicked = False
    
    with col3:
        if st.button("🎯 Calculate Match %", use_container_width=True, key="match_btn"):
            st.session_state.submit1_clicked = False
            st.session_state.submit2_clicked = False
            st.session_state.submit3_clicked = True
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Define prompts for different analyses
    input_prompt1 = """
    You are an experienced Technical Human Resource Manager, your task is to review the provided resume against the job description.
    Please share your professional evaluation on whether the candidate's profile aligns with the role.
    Highlight the strengths and weaknesses of the applicant in relation to the specified job requirements.
    Structure your response in clear sections with headings.
    """
    
    input_prompt2 = """
    You are an expert career coach. Your task is to review the resume and provide detailed recommendations on how the candidate can improve their skills
    and qualifications to better match the job description provided.
    Structure your response with clear headings and bullet points for action items.
    """
    
    input_prompt3 = """
    You are a skilled ATS (Applicant Tracking System) scanner with a deep understanding of data science and ATS functionality,
    your task is to evaluate the resume against the provided job description. 
    Begin your response with a clear percentage match score. 
    Then list all keywords from the job description that are missing in the resume.
    End with your final thoughts on the candidate's suitability for the role.
    Structure your output in clearly labeled sections.
    """
    
# Process button clicks using session state
    if (st.session_state.submit1_clicked or st.session_state.submit2_clicked or st.session_state.submit3_clicked) and uploaded_file is not None and input_text:
        # Change background video
        st.session_state.current_video = r"C:\Users\bhavi\OneDrive\Desktop\12778075_3840_2160_30fps.mp4"
        set_background_video(st.session_state.current_video)
        
        with st.spinner("Analyzing your resume... Please wait"):
            try:
                pdf_content = input_pdf_setup(uploaded_file)
                time.sleep(1)  # Adding slight delay for better UX
                
                # Determine which button was clicked
                if st.session_state.submit1_clicked:
                    prompt = input_prompt1
                    subheader = "Resume Analysis"
                elif st.session_state.submit2_clicked:
                    prompt = input_prompt2
                    subheader = "Improvement Suggestions"
                elif st.session_state.submit3_clicked:
                    prompt = input_prompt3
                    subheader = "Match Percentage Analysis"
                
                # Get the response with additional skills and hobbies
                response = get_gemini_response(
                    prompt, 
                    pdf_content, 
                    input_text, 
                    st.session_state.additional_skills,
                    st.session_state.hobbies
                )
                
                # Display the result in a unique container for scrolling
                result_container = st.container()
                with result_container:
                    st.markdown('<div class="result-container" id="result-section">', unsafe_allow_html=True)
                    st.subheader(subheader)
                    st.markdown(response)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Add JavaScript to scroll to this specific result
                    st.markdown("""
                    <script>
                    document.getElementById('result-section').scrollIntoView({ behavior: 'smooth' });
                    </script>
                    """, unsafe_allow_html=True)
                
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                
    elif (st.session_state.submit1_clicked or st.session_state.submit2_clicked or st.session_state.submit3_clicked):
        if not uploaded_file:
            st.warning("Please upload your resume first.")
        if not input_text:
            st.warning("Please enter the job description.")

if _name_ == "_main":  # Change from "_main" to "_main_"
    main()
