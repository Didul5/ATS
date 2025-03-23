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
import glob
import requests

# Configure the API
genai.configure(api_key='AIzaSyAaKJbBfqXFwlUBTW3KG9Hcto48GTjN3Qg')

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

if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = {}

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

def input_pdf_setup(pdf_content):
    """Convert PDF content to the format required by Gemini API"""
    # Provide the path to the poppler bin directory
    poppler_path = r'C:\Users\bhavi\OneDrive\Desktop\poppler\poppler-24.08.0\Library\bin'  # Adjust this path
    
    # Convert the PDF to image
    images = pdf2image.convert_from_bytes(pdf_content, poppler_path=poppler_path)
    
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

def scan_folder_for_resumes(folder_path):
    """Scan a folder for PDF files and return their paths"""
    # Make sure the folder path exists
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"The folder path {folder_path} does not exist")
    
    # Get all PDF files in the folder
    pdf_files = glob.glob(os.path.join(folder_path, "*.pdf"))
    
    # Sort alphabetically to process them in a consistent order
    pdf_files.sort()
    
    return pdf_files

def extract_candidate_name(pdf_path):
    """Extract the candidate name from the PDF filename"""
    # Get just the filename without directory and extension
    filename = os.path.basename(pdf_path)
    name = os.path.splitext(filename)[0]
    
    # Replace underscores with spaces for better readability
    name = name.replace("_", " ")
    
    return name

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
        return "Hello! I'm your AI assistant for HireSphere. I can help you add skills and hobbies that might not be in your resume. Would you like to tell me about your skills or hobbies?"
    
    # Process the input to determine if it's a skill, hobby, or HireSphere-related question
    if is_skill(user_input):
        st.session_state.additional_skills += f" {user_input}"
        return f"Great! I've added these skills to your profile: {user_input}\n\nDo you have any other skills or perhaps some hobbies you'd like to share?"
    
    elif is_hobby(user_input):
        st.session_state.hobbies += f" {user_input}"
        return f"Wonderful! I've added these hobbies/interests to your profile: {user_input}\n\nAny other hobbies or skills you'd like to mention?"
    
    # HireSphere-related questions
    elif any(keyword in user_input.lower() for keyword in ["hiresphere", "how does hiresphere work", "what is hiresphere", "about hiresphere"]):
        return "HireSphere is an advanced ATS (Applicant Tracking System) that uses AI to analyze resumes against job descriptions. You can use it to analyze a single resume or process multiple resumes in bulk. It can provide basic analysis, improvement suggestions, or calculate a match percentage between your resume and a job description."
    
    elif any(keyword in user_input.lower() for keyword in ["analyze resume", "resume analysis", "how to analyze"]):
        return "To analyze your resume with HireSphere, go to the 'Single Resume Analysis' tab, upload your resume (PDF format), paste the job description, and click one of the analysis buttons. For multiple resumes, use the 'Bulk Resume Analysis' tab and provide a folder path containing PDF resumes."
    
    elif any(keyword in user_input.lower() for keyword in ["match percentage", "how match works", "calculate match"]):
        return "HireSphere calculates match percentage by comparing keywords and qualifications in your resume against those in the job description. Higher percentages indicate better alignment with the job requirements. The system also identifies missing keywords to help you improve your resume."
    
    # Common questions handling
    elif "help" in user_input.lower():
        return "I can help you add skills and hobbies to your profile that might not be in your resume. Just tell me about your skills or interests, and I'll categorize and save them for later use in your resume analysis. You can also ask me about how HireSphere works."
    
    elif any(word in user_input.lower() for word in ["hello", "hi", "hey"]):
        return "Hello there! How can I help you today? Would you like to tell me about your skills or hobbies?"
    
    elif "thank" in user_input.lower():
        return "You're welcome! Is there anything else I can help you with? Perhaps you'd like to add more skills or hobbies, or learn more about HireSphere?"
    
    elif any(word in user_input.lower() for word in ["bye", "goodbye", "exit"]):
        return "It was nice chatting with you! Your skills and hobbies have been saved. Good luck with your job application!"
    
    # Check if it seems like they're trying to add information but we're not sure what type
    elif len(user_input.split()) > 3:  # If it's a longer message, ask for clarification
        return f"I'm not sure if you're telling me about skills or hobbies. Could you clarify if '{user_input}' is a skill or a hobby/interest? Remember, I'm here to help you add skills and hobbies to your profile, or answer questions about HireSphere."
    
    # Default response
    else:
        return "I'm here to help you add skills and hobbies to your profile, or answer questions about HireSphere. Could you tell me more about your professional skills or personal interests?"

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

# Function to extract match percentage from the response
def extract_match_percentage(response_text):
    # Look for percentage patterns in the response
    percentage_pattern = r'(\d{1,3}(?:\.\d+)?)%'
    match = re.search(percentage_pattern, response_text[:200])  # Look only in the first part of the response
    
    if match:
        return float(match.group(1))
    else:
        # Fallback: try to find phrases like "match score: 85"
        score_pattern = r'match(?:\s+score)?(?:\s*(?:is|:))?\s*(\d{1,3}(?:\.\d+)?)'
        match = re.search(score_pattern, response_text.lower()[:200])
        
        if match:
            return float(match.group(1))
    
    # If no percentage found, return None
    return None

# Function to process multiple resumes from a folder
def process_resumes_from_folder(folder_path, job_description, analysis_type):
    """Process multiple resumes from a folder and analyze them against a job description"""
    try:
        # Get all PDF files in the specified folder
        pdf_files = scan_folder_for_resumes(folder_path)
        
        if not pdf_files:
            return "No PDF files found in the specified folder."
        
        # Reset analysis results
        st.session_state.analysis_results = {}
        
        # Select the appropriate prompt based on analysis type
        if analysis_type == "basic":
            prompt = input_prompt1
        elif analysis_type == "improvement":
            prompt = input_prompt2
        else:  # "match"
            prompt = input_prompt3
        
        # Process each resume
        for idx, pdf_path in enumerate(pdf_files):
            # Provide progress update
            st.write(f"Processing file {idx+1}/{len(pdf_files)}: {os.path.basename(pdf_path)}...")
            
            try:
                # Read the PDF file
                with open(pdf_path, 'rb') as pdf_file:
                    pdf_content = input_pdf_setup(pdf_file.read())
                
                # Extract candidate name from filename
                candidate_name = extract_candidate_name(pdf_path)
                
                # Get the analysis
                response = get_gemini_response(
                    prompt, 
                    pdf_content, 
                    job_description,
                    st.session_state.additional_skills,
                    st.session_state.hobbies
                )
                
                # Check if this is a match analysis and extract percentage
                match_percentage = None
                if analysis_type == "match":
                    match_percentage = extract_match_percentage(response)
                
                # Store the results
                st.session_state.analysis_results[candidate_name] = {
                    "response": response,
                    "match_percentage": match_percentage
                }
                
            except Exception as e:
                # Log the error but continue with other files
                st.error(f"Error processing {os.path.basename(pdf_path)}: {str(e)}")
                continue
        
        # Return success message
        return f"Successfully analyzed {len(pdf_files)} resumes."
        
    except Exception as e:
        return f"An error occurred: {str(e)}"

# Function to set background image
def set_background_image():
    # Define the CSS for the background image
    background_css = """
    <style>
    .stApp {
        background-image: url("https://images.unsplash.com/photo-1486312338219-ce68d2c6f44d?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=2072&q=80");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }
    
    /* Add an overlay to make content more readable */
    .stApp::before {
        content: "";
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(255, 255, 255, 0.7); /* White overlay with 70% opacity */
        z-index: -1;
    }
    </style>
    """
    st.markdown(background_css, unsafe_allow_html=True)

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
        border: 1px solid rgba(230, 230, 230, 0.5);
    }
    
    .card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 20px rgba(0, 0, 0, 0.15);
    }
    
    .title-container {
        background: linear-gradient(90deg, #4b6cb7 0%, #182848 100%);
        padding: 25px;
        border-radius: 15px;
        color: white;
        margin-bottom: 30px;
        text-align: center;
        box-shadow: 0 10px 20px rgba(27, 40, 72, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.1);
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
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .user-message {
        background-color: rgba(227, 242, 253, 0.9);
        margin-left: 20%;
        border-top-right-radius: 0;
        border-left: 3px solid #4b6cb7;
    }
    
    .bot-message {
        background-color: rgba(255, 255, 255, 0.9);
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
        box-shadow: 0 4px 6px rgba(75, 108, 183, 0.2);
    }
    
    .custom-button:hover {
        background-color: #182848;
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(27, 40, 72, 0.3);
    }
    
    .result-container {
        background-color: rgba(255, 255, 255, 0.92);
        backdrop-filter: blur(15px);
        -webkit-backdrop-filter: blur(15px);
        border-radius: 15px;
        padding: 25px;
        margin-top: 30px;
        box-shadow: 0 8px 15px rgba(0, 0, 0, 0.1);
        font-family: 'Poppins', sans-serif;
        border: 1px solid rgba(230, 230, 230, 0.7);
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

    /* Candidate card styling */
    .candidate-card {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        margin-bottom: 15px;
        overflow: hidden;
    }
    
    .candidate-header {
        background-color: #f0f2f5;
        padding: 15px;
        border-bottom: 1px solid #e0e0e0;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .candidate-name {
        font-weight: bold;
        color: #4b6cb7;
        font-size: 1.2em;
    }
    
    .match-badge {
        background-color: #4CAF50;
        color: white;
        padding: 5px 10px;
        border-radius: 15px;
        font-size: 0.9em;
        font-weight: bold;
    }
    
    .low-match {
        background-color: #f44336;
    }
    
    .medium-match {
        background-color: #FF9800;
    }
    
    .high-match {
        background-color: #4CAF50;
    }
    
    .candidate-content {
        padding: 15px;
    }
    
    /* Resume sorting controls */
    .sorting-controls {
        display: flex;
        align-items: center;
        margin-bottom: 20px;
        padding: 10px;
        background-color: #f5f7fa;
        border-radius: 8px;
    }
    
    .sort-label {
        margin-right: 15px;
        font-weight: 500;
        font-family: 'Montserrat', sans-serif;
    }
    </style>
    """
    st.markdown(background_css, unsafe_allow_html=True)

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

# Streamlit App
def main():
    set_background_image()
    set_custom_styling()
    
    # Title with gradient background and improved font
    st.markdown('<div class="title-container"><h1>HireSphere</h1><p>Advanced ATS System with AI-Powered Resume Analysis</p></div>', unsafe_allow_html=True)
    
    # Create tabs for different functionalities
    tab1, tab2, tab3 = st.tabs(["Single Resume Analysis", "Bulk Resume Analysis", "Skills & Hobbies Chatbot"])
    
    # Tab 1: Single Resume Analysis (original functionality)
    with tab1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Upload Resume & Job Description")
        
        # Job description input
        input_text = st.text_area("Enter the Job Description:", key="input_single", height=150)
        
        # Resume upload
        uploaded_file = st.file_uploader("Upload your resume (PDF)...", type=["pdf"], key="single_file")
        
        if uploaded_file is not None:
            success_message = st.success("✅ Resume uploaded successfully!")
            
        # Buttons for analysis with custom styling and equal spacing
        st.markdown('<div class="equal-buttons">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        
        with col1:
            submit1 = st.button("📋 Analyze Resume", use_container_width=True)
        
        with col2:
            submit2 = st.button("🚀 Improvement Suggestions", use_container_width=True)
        
        with col3:
            submit3 = st.button("🎯 Calculate Match %", use_container_width=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Process button clicks for single resume
        if (submit1 or submit2 or submit3) and uploaded_file is not None and input_text:
            with st.spinner("Analyzing your resume... Please wait"):
                try:
                    pdf_content = input_pdf_setup(uploaded_file.read())
                    time.sleep(1)  # Adding slight delay for better UX
                    
                    # Determine which button was clicked and get appropriate response
                    if submit1:
                        prompt = input_prompt1
                        subheader = "Resume Analysis"
                    elif submit2:
                        prompt = input_prompt2
                        subheader = "Improvement Suggestions"
                    elif submit3:
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
                    
                    # Display the result
                    st.markdown('<div class="result-container">', unsafe_allow_html=True)
                    st.subheader(subheader)
                    st.markdown(response)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    except Exception as e:
                        st.error(f"An error occurred: {str(e)}")
            elif (submit1 or submit2 or submit3):
                            if not uploaded_file:
                                st.warning("Please upload your resume first.")
                            if not input_text:
                                st.warning("Please enter the job description.")

                
    # Tab 3: Skills & Hobbies Chatbot
    with tab3:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Skills & Hobbies Chatbot")
        
        # Display current skills and hobbies
        if st.session_state.additional_skills or st.session_state.hobbies:
            st.markdown("### Your Profile")
            
            if st.session_state.additional_skills:
                st.markdown('<div class="profile-section">', unsafe_allow_html=True)
                st.markdown("Skills: " + st.session_state.additional_skills)
                st.markdown('</div>', unsafe_allow_html=True)
            
            if st.session_state.hobbies:
                st.markdown('<div class="profile-section">', unsafe_allow_html=True)
                st.markdown("Hobbies & Interests: " + st.session_state.hobbies)
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Add a button to clear the profile
            if st.button("Clear Profile", key="clear_profile"):
                clear_skills()
                st.experimental_rerun()
        
        # Chat interface
        st.markdown("### Chat with the AI Assistant")
        st.markdown("Tell me about your skills and hobbies, and I'll add them to your profile for resume analysis.")
        
        # Display chat history
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                st.markdown(f'<div class="chat-message user-message">{message["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-message bot-message">{message["content"]}</div>', unsafe_allow_html=True)
        
        # Chat input
        st.text_input("Type a message...", key="user_message", on_change=on_send_message)
        
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
                    
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
        elif (submit1 or submit2 or submit3):
            if not uploaded_file:
                st.warning("Please upload your resume first.")
            if not input_text:
                st.warning("Please enter the job description.")
    
    # Tab 2: Bulk Resume Analysis (new functionality)
    with tab2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Bulk Resume Analysis")
        
        # Input for the folder path containing resumes
        folder_path = st.text_input("Enter the folder path containing resumes (e.g., C:/Resumes):", key="folder_path")
        
        # Option to browse for folder instead
        folder_browser_col1, folder_browser_col2 = st.columns([3, 1])
        with folder_browser_col1:
            st.markdown("Or select a folder from file browser:")
        with folder_browser_col2:
            if st.button("Browse Folders"):
                # Use a temporary solution to get the folder path
                # This will require the user to copy-paste the path
                st.info("Please use your file explorer to navigate to the folder with resumes, then copy-paste the path above.")
        
        # Job description input
        job_description = st.text_area("Enter the Job Description:", key="input_bulk", height=150)
        
        # Analysis type selection
        analysis_type = st.radio(
            "Select the type of analysis:",
            ["basic", "improvement", "match"],
            format_func=lambda x: {
                "basic": "Basic Analysis", 
                "improvement": "Improvement Suggestions", 
                "match": "Match Percentage"
            }[x],
            horizontal=True
        )
        
        # Button to start bulk analysis
        start_bulk_analysis = st.button("Start Bulk Analysis", use_container_width=True, key="start_bulk")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Process bulk analysis
        if start_bulk_analysis and folder_path and job_description:
            with st.spinner("Analyzing resumes in the folder... This may take some time depending on the number of files."):
                result_message = process_resumes_from_folder(folder_path, job_description, analysis_type)
                st.success(result_message)
                
                # Display results if any
                if st.session_state.analysis_results:
                    st.markdown('<div class="result-container">', unsafe_allow_html=True)
                    st.subheader("Analysis Results")
                    
                    # Prepare combined results text for download button
                    combined_results = ""
                    
                    # Sort candidates based on analysis type
                    if analysis_type == "match":
                        # Sort candidates by match percentage
                        sorted_candidates = sorted(
                            st.session_state.analysis_results.items(),
                            key=lambda x: x[1]["match_percentage"] if x[1]["match_percentage"] is not None else 0,
                            reverse=True
                        )
                        
                        st.markdown('<div class="sorting-controls">', unsafe_allow_html=True)
                        st.markdown('<span class="sort-label">Candidates sorted by match percentage (highest first)</span>', unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                    else:
                        # Sort alphabetically by name
                        sorted_candidates = sorted(st.session_state.analysis_results.items())
                    
                    # Add results to the combined text for download
                    for name, res in sorted_candidates:
                        match_str = f" - Match: {res['match_percentage']:.1f}%" if res['match_percentage'] is not None else ""
                        combined_results += f"## {name}{match_str}\n\n{res['response']}\n\n{'='*80}\n\n"
                    
                    # Download button for all results
                    if len(sorted_candidates) > 0:
                        st.download_button(
                            label="Download All Results",
                            data=combined_results,
                            file_name=f"bulk_resume_analysis_{analysis_type}.txt",
                            mime="text/plain"
                        )
                    
                    # Only display individual results for match analysis
                    if analysis_type == "match":
                        for candidate_name, result in sorted_candidates:
                            # Determine match class for color coding
                            match_class = ""
                            match_display = ""
                            
                            if result["match_percentage"] is not None:
                                percentage = result["match_percentage"]
                                if percentage < 50:
                                    match_class = "low-match"
                                elif percentage < 75:
                                    match_class = "medium-match"
                                else:
                                    match_class = "high-match"
                                match_display = f'<span class="match-badge {match_class}">{percentage:.1f}%</span>'
                            
                            # Create candidate card with properly closed HTML tags
                            st.markdown(f'''
                            <div class="candidate-card">
                                <div class="candidate-header">
                                    <span class="candidate-name">{candidate_name}</span>
                                    {match_display}
                                </div>
                                <div class="candidate-content">
                                    {result["response"]}
                                </div>
                            </div>
                            ''', unsafe_allow_html=True)
                    else:
                        # For basic and improvement, just show a message
                        st.info("Analysis completed. Download the results using the button above.")
                    
                    st.markdown('</div>', unsafe_allow_html=True)
