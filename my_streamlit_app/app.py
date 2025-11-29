# --- Zaroori Libraries Import Karein ---
from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import google.generativeai as genai
import json
import re
import os
from werkzeug.security import generate_password_hash, check_password_hash
# NAYA: Code execute karne ke liye zaroori libraries
import subprocess
import sys
import tempfile

# --- Flask App ka Basic Setup ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_very_secret_key_change_it_later'

# --- NAYA: Firebase Configuration ko App Mein Add Karein ---
# APNA FIREBASE CONFIGURATION YAHAN PASTE KAREIN
# Yeh aapko Firebase console se "Project settings" > "General" > "Your apps" > "SDK setup and configuration" mein milega.
firebase_config_dict = {
  "apiKey": "AIzaSyA842rvnA8SAWR4FZeHImitHtemQwqA4Rs",
  "authDomain": "swadesh-app-cf307.firebaseapp.com",
  "projectId": "swadesh-app-cf307",
  "storageBucket": "swadesh-app-cf307.firebaseapp.com",
  "messagingSenderId": "413687632539",
  "appId": "1:413687632539:web:a1ba299a35c3d6cdbf2c3e",
  "measurementId": "G-LG3THVWBX9"
}
# Isse config Flask app ke liye available ho jayega
app.config['FIREBASE_CONFIG_DICT'] = firebase_config_dict

USER_DATA_FILE = 'users.json'  # User ka data is file mein save hoga

# --- GEMINI API ka Setup ---
# Apni actual API key yahan daalein
GEMINI_API_KEY = "AIzaSyAqqVd1D9j4uK7TzGBCqbPHkxBEXYhYACI"
try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash') 
except Exception as e:
    print(f"Error initializing Gemini API: {e}")
    model = None

# --- User Data ko Load aur Save Karne Wale Functions ---
def load_users():
    """users.json file se data load karta hai."""
    if not os.path.exists(USER_DATA_FILE):
        return {}
    try:
        with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_users(users):
    """User data ko users.json file mein save karta hai."""
    with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=4)

# --- ============================= ---
# --- Sabhi Page Routes Yahan Hain ---
# --- ============================= ---

@app.route("/")
def home():
    """Landing Page (index.html) dikhata hai."""
    is_logged_in = 'username' in session
    username = session.get('username')
    return render_template("index.html", is_logged_in=is_logged_in, username=username)

# --- Authentication (Login/Signup) Routes ---

@app.route("/auth")
def auth_page():
    if 'username' in session:
        return redirect(url_for('profile_page'))
    return render_template("auth.html")

@app.route("/signup", methods=['POST'])
def signup():
    data = request.get_json()
    users = load_users()
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({"success": False, "message": "Username and password zaroori hain."}), 400
    if username in users:
        return jsonify({"success": False, "message": "Yeh username pehle se maujood hai."}), 409
    hashed_password = generate_password_hash(password)
    users[username] = {
        "email": data.get('email'), "school": data.get('school'),
        "branch": data.get('branch'), "password": hashed_password
    }
    save_users(users)
    return jsonify({"success": True, "message": "Account safaltapoorvak ban gaya!"})

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    users = load_users()
    username = data.get('username')
    password = data.get('password')
    user = users.get(username)
    if not user or not check_password_hash(user.get('password', ''), password):
        return jsonify({"success": False, "message": "Galat username ya password."}), 401
    session['username'] = username
    return jsonify({"success": True, "redirect_url": url_for('home')})

@app.route('/profile')
def profile_page():
    if 'username' not in session: return redirect(url_for('auth_page'))
    users = load_users()
    user_data = users.get(session['username'])
    if not user_data:
        session.pop('username', None)
        return redirect(url_for('auth_page'))
    return render_template('profile.html', user=user_data, username=session['username'])

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))

# --- Baaki Sabhi Pages ke Routes ---

@app.route("/timetable")
def timetable_page(): return render_template("timetable.html")
@app.route("/career-guide")
def career_guide_page(): return render_template("career.html")
@app.route("/course")
def course_page(): return render_template("course.html")
@app.route("/progress")
def Progress_page(): return render_template("result.html")
@app.route("/fungame")
def fungame_page(): return render_template("fungame.html")
@app.route("/Notes")
def Notes_page(): return render_template("notes.html")
@app.route("/quizgame")
def quizgame_page(): return render_template("quizgame.html")
@app.route("/Python")
def Python_page(): return render_template("python.html")



# --- ======================================== ---
# --- MENTAL HEALTH CHATBOT ka Code Start ---
# --- ======================================== ---
@app.route("/mental-health-support")
def mental_health_chatbot_page():
    """Mental health chatbot ka main page (mental_health_chatbot.html) dikhata hai."""
    if 'dost_chat_history' in session:
        session.pop('dost_chat_history')
    return render_template("mental_health_chatbot.html")
@app.route("/ask_dost", methods=['POST'])
def ask_dost():
    """Chatbot se baat karne ke liye AI ko call karta hai."""
    user_message = request.json.get('message')
    if 'dost_chat_history' not in session:
        session['dost_chat_history'] = []
    prompt = f"""
    Tumhara naam 'Dost' hai, aur tum ek caring mental health support chatbot ho.
    Tumhara kaam user se ek dost ki tarah baat karna hai, jaise WhatsApp par karte hain.
    Tumhe simple, aasan Hinglish mein baat karni hai aur emojis (jaise 😊, 🤗, 👍, 🙏, 🤔) ka istemaal karna hai.
    RULES:
    1.  MOOD DETECT KARO: User ke message se unka mood samjho (sad, anxious, stressed, happy, ya neutral).
    2.  DOST KI TARAH BAAT KARO: Agar user sad ya pareshan hai, toh unhe himmat do. Pucho "kya hua?", "sab theek ho jayega".
    3.  MEDICAL ADVICE MAT DENA: Kabhi bhi doctor wali salah mat dena. Hamesha kaho ki tum ek dost ho jo sunne ke liye hai aur agar zaroorat lage toh professional help leni chahiye.
    4.  BREATHING EXERCISE SUGGEST KARO: Agar user stressed ya anxious lage, toh unhe breathing exercise ke liye pucho. Jaise: "Ek gehri saans lein? Yeh humein shaant karne mein help karega. Try karein? 😊"
    5.  POSITIVE RAHO: Agar user aacha feel kar raha hai, toh unki khushi mein shaamil ho.
    Chat History: {session['dost_chat_history']}
    User ka naya message hai: "{user_message}"
    Ab, ek dost ki tarah reply karo.
    """
    if not model:
        return jsonify({"reply": "Sorry, AI abhi available nahi hai. Baad mein try karein."})
    try:
        response = model.generate_content(prompt)
        bot_reply = response.text
        session['dost_chat_history'].append({"user": user_message, "bot": bot_reply})
        session.modified = True
        return jsonify({"reply": bot_reply})
    except Exception as e:
        print(f"Error calling Gemini: {e}")
        return jsonify({"reply": "Oops! Kuch gadbad ho gayi. Thodi der mein try karein."})
@app.route("/breathing-exercise")
def breathing_exercise_page():
    return render_template("breathing.html")
@app.route("/quotes")
def quotes_page():
    return render_template("quots.html")
@app.route("/Novels")
def novels_page():
    return render_template("novel.html")
@app.route("/motivational-reels")
def motivational_reels_page():
    return render_template("reels.html")
# --- ====================================== ---
# --- MENTAL HEALTH CHATBOT ka Code End ---
# --- ====================================== ---


# --- ========================================================== ---
# --- AI Career Roadmap wala Functionality ---
# --- ========================================================== ---
def clean_json_response(text):
    """AI ke response se extra characters (jaise json) hatata hai."""
    match = re.search(r'json\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        return match.group(1)
    return text.strip()
@app.route("/generate_roadmap", methods=['POST'])
def generate_roadmap():
    # 1. Frontend se user ka data lein
    data = request.get_json()
    field = data.get('field')
    skills = data.get('skills')
    interests = data.get('interests')
    if not all([field, skills, interests]):
        return jsonify({"error": "All fields are required."}), 400
    if not model:
        return jsonify({"error": "AI model is not available."}), 503
    # 2. AI ke liye ek detailed prompt banayein
    prompt = f"""
    Create a detailed career roadmap for a user with the following profile:
    - Current Field/Education: {field}
    - Skills: {skills}
    - Interests: {interests}
    Based on this, suggest a suitable career path.
    Generate the output ONLY in a valid JSON format. Do not add any text before or after the JSON object.
    The JSON object must have the following structure:
    {{
      "career_path": "Suggested Career Path Name",
      "summary": "A brief 2-3 line summary of why this path is suitable.",
      "roadmap": [
        {{
          "phase": "Phase 1: Foundation (e.g., First 3 Months)",
          "duration": "e.g., 3 Months",
          "tasks": ["Task 1", "Task 2", "Task 3"]
        }},
        {{
          "phase": "Phase 2: Intermediate Skills",
          "duration": "e.g., 6 Months",
          "tasks": ["Task A", "Task B", "Task C"]
        }},
        {{
          "phase": "Phase 3: Advanced Topics & Portfolio",
          "duration": "e.g., 6 Months",
          "tasks": ["Project 1", "Learn advanced topic", "Contribute to open source"]
        }},
        {{
          "phase": "Phase 4: Job Preparation",
          "duration": "e.g., 3 Months",
          "tasks": ["Build resume", "Practice interviews", "Networking"]
        }}
      ]
    }}
    """
    try:
        # 3. AI ko call karein aur response generate karein
        response = model.generate_content(prompt)
        ai_response_text = response.text
        # 4. AI ke response ko saaf karke JSON mein convert karein
        cleaned_response = clean_json_response(ai_response_text)
        roadmap_data = json.loads(cleaned_response)
        # 5. Roadmap data ko session mein save karein
        session['roadmap_data'] = roadmap_data
        # 6. Frontend ko success message aur redirect URL bhejein
        return jsonify({
            "success": True,
            "redirect_url": url_for('roadmap_page')
        })
    except json.JSONDecodeError:
        print("Error: AI did not return valid JSON.")
        print("AI Response:", ai_response_text)
        return jsonify({"error": "AI response was not in the correct format."}), 500
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": "An unexpected error occurred."}), 500
@app.route("/roadmap")
def roadmap_page():
    # Session se roadmap data nikaalein
    roadmap_data = session.get('roadmap_data')
    # Agar data nahi hai, to user ko career guide page par wapas bhej dein
    if not roadmap_data:
        return redirect(url_for('career_guide_page'))
    # Data ko roadmap.html template par bhej kar render karein
    return render_template("roadmap.html", data=roadmap_data)
# --- ================================================= ---
# --- NAYA: PYTHON LEARNING PLATFORM BACKEND START ---
# --- ================================================= ---

@app.route("/python-learn")
def python_learn_page():
    """Interactive Python learning page ko render karta hai."""
    return render_template("python_runner.html")

@app.route("/execute_python", methods=['POST'])
def execute_python():
    """Frontend se aaye Python code ko securely execute karta hai."""
    user_code = request.json.get('code', '')
    
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.py', encoding='utf-8') as temp_file:
        temp_file.write(user_code)
        temp_file_name = temp_file.name

    try:
        process = subprocess.run(
            [sys.executable, temp_file_name], 
            capture_output=True, 
            text=True, 
            timeout=5,
            check=False
        )
        
        output = process.stdout
        error = process.stderr
        
    except subprocess.TimeoutExpired:
        output = ""
        error = "Error: Code execution timed out after 5 seconds.\n(Kahin aapka code infinite loop mein to nahi phas gaya?)"
    except Exception as e:
        output = ""
        error = f"An unexpected server error occurred during execution: {e}"
    finally:
        if os.path.exists(temp_file_name):
            os.remove(temp_file_name)

    full_output = ""
    if output:
        full_output += output
    if error:
        full_output += f"Error:\n{error}"
        
    if not full_output:
        full_output = "Code successfully executed, but produced no output."

    return jsonify({"output": full_output})

# --- =============================================== ---
# --- NAYA: PYTHON LEARNING PLATFORM BACKEND END ---
# --- =============================================== ---
# --- ================================================= ---
# --- NAYA: AI QUIZ - PRACTICE QUESTION GENERATOR (UPDATED) ---
# --- ================================================= ---
@app.route("/generate_practice_questions", methods=['POST'])
def generate_practice_questions():
    # 1. Frontend se galat jawabon ki list lein
    data = request.get_json()
    incorrect_questions = data.get('questions')
    topic = data.get('topic')

    if not incorrect_questions or not topic:
        return jsonify({"error": "Zaroori data (questions, topic) nahi mila."}), 400

    if not model:
        return jsonify({"error": "AI model abhi uplabdh nahi hai."}), 500

    # 2. NAYA AUR BEHTAR PROMPT: Ismein explanation aur tips bhi maange gaye hain
    prompt = f"""
    You are an expert exam tutor for Indian competitive exams like JEE and NDA.
    A student is weak in the topic: "{topic}".
    Here are the exact questions they answered incorrectly, which shows their knowledge gap:
    {json.dumps(incorrect_questions, indent=2)}

    Your task is to generate a complete personalized improvement plan in JSON format.
    The plan must include:
    1.  **Topic Explanation**: A brief, easy-to-understand explanation (2-3 sentences) of the core concept of "{topic}".
    2.  **Improvement Tips**: A list of 3-4 short, actionable tips to help the student master this topic.
    3.  **Practice Questions**: Generate 10 new, different multiple-choice practice questions that directly target the student's weaknesses shown in the incorrect questions. The questions should be of a similar style and difficulty.
    4.  **Relevance**: For each new question, provide a one-sentence explanation of why it's a good practice question based on the student's mistakes.

    IMPORTANT: Return your response ONLY as a valid JSON object. Do not add any text, markdown, or comments before or after the JSON object. The JSON structure MUST be exactly as follows:

    {{
      "topic": "{topic}",
      "topic_explanation": "A short, clear explanation of the core concept goes here.",
      "improvement_tips": [
        "First actionable tip for improvement.",
        "Second actionable tip for improvement.",
        "Third actionable tip for improvement."
      ],
      "generated_questions": [
        {{
          "question": "Your new question text here...",
          "options": ["Option A", "Option B", "Option C", "Option D"],
          "answer": "The correct option text",
          "relevance": "A brief explanation of why this question is helpful."
        }}
      ]
    }}
    """

    try:
        # 3. AI ko call karein aur response generate karein
        response = model.generate_content(prompt)
        
        # 4. AI ke response ko saaf karke JSON mein convert karein
        cleaned_response = clean_json_response(response.text)
        ai_data = json.loads(cleaned_response)
        
        # 5. Naye questions, explanation, aur tips ko frontend par wapas bhejein
        return jsonify(ai_data)

    except Exception as e:
        print(f"Practice questions generate karte waqt error aaya: {e}")
        print(f"AI ka raw response tha: {response.text if 'response' in locals() else 'No response'}")
        return jsonify({{"error": "AI response ko process karne mein asamarth."}}), 500
# --- ================================================= ---
# --- AI QUIZ - END ---
# --- ================================================= ---
# --- ================================= ---
# --- NAYA: CHAT ROOM ka Route ---
# --- ================================= ---
@app.route("/chatroom")
def chatroom_page():
    # Check karein ki user logged in hai ya nahi
    if 'username' not in session:
        # Agar logged in nahi hai, to login page par bhej dein
        return redirect(url_for('auth_page'))
    
    # User ka naam template ko pass karein
    username = session.get('username')
    return render_template("chatroom.html", username=username)




# --- App ko Run Karne ke Liye ---
if __name__ == "__main__":
    app.run(debug=True, port=5001)