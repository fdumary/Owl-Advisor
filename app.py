from flask import Flask, send_from_directory, request, jsonify
import json
import os

app = Flask(__name__, static_folder='static', static_url_path='')

# Load data
def load_data():
    try:
        with open('data/campus_data.json', 'r') as f:
            campus_data = json.load(f)
    except Exception:
        campus_data = {}
        
    try:
        with open('data/course_data.json', 'r') as f:
            course_data = json.load(f)
    except Exception:
        course_data = []
        
    return campus_data, course_data

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    user_input = request.json.get('message', '').lower()
    campus_data, course_data = load_data()
    
    response = ""
    
    # Simple rule-based AI for the Hackathon Demo
    if 'course' in user_input or 'class' in user_input or 'cop 3530' in user_input:
        course = next((c for c in course_data if c['course_number'] == '3530'), None)
        if course:
            response = f"I found **{course['title']}** (COP {course['course_number']}) taught by {course['instructor']}. It meets on {course['days']} at {course['time']} in {course['location']}. Status is currently {course['status']} with {course['waitlist']} on the waitlist. {course['ta_info']}."
        else:
            response = "I can help you find a course! Try asking for 'COP 3530' or 'Foundations of Computer Science'."
            
    elif 'library' in user_input:
        lib = next((b for b in campus_data.get('buildings', []) if b['code'] == 'LY'), None)
        if lib:
            response = f"The **{lib['name']}** is located at the {lib['location']} (GPS: {lib['gps']}). Its hours are: {lib['hours']}. You can contact them at {lib['contact']}."
            
    elif 'advisor' in user_input:
        adv = campus_data.get('advisors', [])[0]
        response = f"For {adv['department']}, your advisor is **{adv['name']}**. They are located in {adv['location']}. Hours: {adv['hours']}. Email: {adv['email']}."
        
    elif 'parking' in user_input:
        response = "For Engineering East, the best parking is **Lot 1 (Blue Lot)**, but it's usually full by 10am. Alternatively, try **Parking Garage 1** near the Student Union."
        
    elif 'hello' in user_input or 'hi' in user_input:
        response = "Hello! I'm Owl-Advisor, your AI assistant for FAU. I can help you find courses, check waitlists, locate buildings, find your advisor, or get parking info. What do you need help with?"
        
    else:
        response = "I'm still learning! I have data on FAU courses, buildings, parking, and advisors. Try asking: 'Where is the library?', 'Who is the CS advisor?', or 'Tell me about COP 3530'."
        
    return jsonify({"response": response})

if __name__ == '__main__':
    # Make sure static directory exists
    os.makedirs('static', exist_ok=True)
    app.run(debug=True, port=5000)
