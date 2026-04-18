from flask import Flask, send_from_directory, request, jsonify
import json
import os
import re
import requests
import math

def haversine(lat1, lon1, lat2, lon2):
    R = 3958.8 # Earth radius in miles
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2) * math.sin(dlat/2) + \
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
        math.sin(dlon/2) * math.sin(dlon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

# Simple global state for the Hackathon Demo
session_context = {
    "subject": None,
    "course_number": None,
    "parking_requested": False
}

base_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=os.path.join(base_dir, 'static'), static_url_path='')

def scrape_live_course(subject, course_number, term="202408"):
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
    }
    try:
        session.get("https://bannerxe.fau.edu/StudentRegistrationSsb/ssb/term/termSelection?mode=search", headers=headers, timeout=5)
        data = {"term": term, "studyPath": "", "studyPathText": "", "startDatepicker": "", "endDatepicker": ""}
        session.post("https://bannerxe.fau.edu/StudentRegistrationSsb/ssb/term/search?mode=search", data=data, headers=headers, timeout=5)
        
        params = {
            "txt_subject": subject,
            "txt_courseNumber": course_number,
            "txt_term": term,
            "pageOffset": 0,
            "pageMaxSize": 10,
            "sortColumn": "subjectDescription",
            "sortDirection": "asc"
        }
        res = session.get("https://bannerxe.fau.edu/StudentRegistrationSsb/ssb/searchResults/searchResults", params=params, headers=headers, timeout=5)
        
        if res.status_code == 200:
            json_data = res.json()
            if json_data.get('success') and json_data.get('data'):
                courses = []
                for item in json_data['data']:
                    days = "TBA"
                    time_str = "TBA"
                    location = "TBA"
                    if item.get("meetingsFaculty"):
                        meeting = item["meetingsFaculty"][0].get("meetingTime", {})
                        room = meeting.get("room", "TBA")
                        bldg = meeting.get("building", "")
                        location = f"{bldg} {room}".strip()
                        if meeting.get("beginTime"):
                            time_str = f"{meeting.get('beginTime')} - {meeting.get('endTime')}"
                        
                        day_str = ""
                        if meeting.get("monday"): day_str += "M"
                        if meeting.get("tuesday"): day_str += "T"
                        if meeting.get("wednesday"): day_str += "W"
                        if meeting.get("thursday"): day_str += "R"
                        if meeting.get("friday"): day_str += "F"
                        if day_str: days = day_str
                        
                    is_online = False
                    # Basic heuristic for online classes
                    if item.get("instructionalMethod") in ["Fully Online", "Online"] or "Online" in location or location == "TBA":
                        is_online = True
                        location = "Online"
                        
                    courses.append({
                        "subject": subject.upper(),
                        "course_number": course_number,
                        "section": item.get("sequenceNumber", "001"),
                        "title": item.get("courseTitle", "Unknown"),
                        "instructor": item.get("faculty", [{}])[0].get("displayName", "TBA") if item.get("faculty") else "TBA",
                        "status": "Open" if item.get("seatsAvailable", 0) > 0 else "Waitlist",
                        "spots_left": item.get("seatsAvailable", 0),
                        "waitlist": item.get("waitAvailable", 0),
                        "days": days,
                        "time": time_str,
                        "location": location,
                        "is_online": is_online,
                        "ta_info": "Not listed publicly",
                        "zoom_link": "Check Canvas for Zoom link"
                    })
                return courses
    except Exception as e:
        print(f"Scrape error: {e}")
    return []

def load_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    try:
        with open(os.path.join(base_dir, 'data', 'campus_data.json'), 'r') as f:
            campus_data = json.load(f)
    except Exception:
        campus_data = {}
    try:
        with open(os.path.join(base_dir, 'data', 'course_data.json'), 'r') as f:
            course_data = json.load(f)
    except Exception:
        course_data = []
    return campus_data, course_data

@app.route('/')
def index():
    return send_from_directory(os.path.join(base_dir, 'static'), 'index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    global session_context
    user_input = request.json.get('message', '').lower()
    user_lat = request.json.get('lat')
    user_lon = request.json.get('lon')
    campus_data, course_data = load_data()
    response = ""
    
    # Check if the user is asking about a building
    building_match = None
    for b in campus_data.get('buildings', []):
        name_lower = b['name'].lower()
        code_lower = b['code'].lower()
        if name_lower in user_input or re.search(rf'\b{code_lower}\b', user_input):
            building_match = b
            break
            
    # Check for course
    course_match = re.search(r'([a-z]{3})\s*(\d{4})(?:\s+(?:section|sec|#)\s*0*([a-z0-9]+))?', user_input)
    section_only_match = re.search(r'(?:section|sec|#)\s*0*([a-z0-9]+)', user_input)
    just_number_match = re.fullmatch(r'0*(\d{1,3}[a-z]?)', user_input.strip())
    
    subject = None
    course_number = None
    section = None
    
    if course_match:
        subject = course_match.group(1).upper()
        course_number = course_match.group(2)
        section = course_match.group(3)
        # Remember context
        session_context['subject'] = subject
        session_context['course_number'] = course_number
        session_context['parking_requested'] = 'parking' in user_input
    elif (section_only_match or just_number_match) and session_context['subject']:
        subject = session_context['subject']
        course_number = session_context['course_number']
        section = section_only_match.group(1) if section_only_match else just_number_match.group(1)
        if session_context['parking_requested'] and 'parking' not in user_input:
            user_input += " parking"
            
    if subject and course_number:
        
        # Local data
        found_courses = [c for c in course_data if c['subject'] == subject and c['course_number'] == course_number]
        
        # Live scrape if not found locally
        if not found_courses:
            found_courses = scrape_live_course(subject, course_number)
            
        if not found_courses:
            response = f"I couldn't find any data for {subject} {course_number}. Are you sure it's offered this semester?"
        else:
            if not section:
                secs = [c.get('section', '001') for c in found_courses]
                response = f"I found multiple sections for **{subject} {course_number}**: {', '.join(secs)}. Which section are you looking for? (e.g. 'section {secs[0]}')"
            else:
                # Find specific section without crashing on int()
                course = next((c for c in found_courses if c.get('section', '001').lstrip('0') == section.lstrip('0')), None)
                if not course:
                    response = f"I couldn't find section {section} for {subject} {course_number}."
                else:
                    if 'spot' in user_input or 'left' in user_input or 'waitlist' in user_input or 'available' in user_input and 'parking' not in user_input:
                        response = f"**{course['subject']} {course['course_number']} (Section {course['section']})** ({course['title']}) currently has **{course.get('spots_left', 0)} spots left** to register. There are **{course.get('waitlist', 0)} seats** taken on the waitlist."
                    else:
                        response = f"I found **{course['title']}** ({course['subject']} {course['course_number']} Section {course['section']}) taught by {course['instructor']}."
                        if course.get('is_online'):
                            response += f" This is an **Online** class. Zoom Link: {course.get('zoom_link', 'Check Canvas')}."
                        else:
                            response += f" It meets **in-person** on {course['days']} at {course['time']} in {course['location']}."
                        
                        response += f" Status is currently {course['status']} with {course.get('spots_left', 0)} spots open and {course.get('waitlist', 0)} on the waitlist."
                        
                    # Parking logic
                    if not course.get('is_online'):
                        loc = course['location']
                        building_name = ""
                        for b in campus_data.get('buildings', []):
                            if b['name'].lower() in loc.lower() or b['code'].lower() in loc.lower().split():
                                building_name = b['name']
                                break
                        
                        if building_name:
                            lots = [p for p in campus_data.get('parking', []) if building_name in p.get('closest_buildings', [])]
                            if lots:
                                closest_lot = lots[0]
                                if closest_lot.get('spaces_available', 0) > 0:
                                    response += f"\n\n🚗 **Parking**: The closest lot to {building_name} is **{closest_lot['lot_name']}** which currently has {closest_lot['spaces_available']} spaces available."
                                else:
                                    response += f"\n\n🚗 **Parking**: The closest lot to {building_name} is **{closest_lot['lot_name']}**, but it is currently **full**. "
                                    next_lot = next((p for p in lots[1:] if p.get('spaces_available', 0) > 0), None)
                                    if next_lot:
                                        response += f"The next best option is **{next_lot['lot_name']}**, which has {next_lot['spaces_available']} spaces available."
                                    else:
                                        response += "Unfortunately, all nearby parking lots appear to be full right now."
                            else:
                                response += f"\n\n🚗 **Parking**: I couldn't find a specific parking lot for {building_name}. Try Parking Garage 1 or Lot 1!"
                        else:
                            response += f"\n\n🚗 **Parking**: I couldn't identify the specific building to give you a parking location. Try Parking Garage 1!"
                    elif 'parking' in user_input:
                        response += "\n\n🚗 **Parking**: This class is online, so no parking is needed!"

    elif building_match:
        b = building_match
        response = f"The **{b['name']}** ({b['code']}) is located at the {b['location']}. Its hours are: {b['hours']}."
        if b.get('contact'):
            response += f" Contact: {b['contact']}."
            
        if user_lat is not None and user_lon is not None and b.get('gps'):
            try:
                b_lat, b_lon = map(float, b['gps'].split(','))
                dist_miles = haversine(float(user_lat), float(user_lon), b_lat, b_lon)
                walk_time_mins = max(1, round(dist_miles * 20))
                response += f"\n\nBased on your device's GPS, you are **{dist_miles:.2f} miles** away. It will take you approximately **{walk_time_mins} minute(s)** to walk there."
            except Exception as e:
                pass
        else:
            response += "\n\n(If you enable Location Services in your browser, I can calculate your walking distance and time to this building!)"

    elif 'course' in user_input or 'class' in user_input:
        response = "I can help you find a course! Try asking for specific courses like 'COP 3540 section 001', or 'STA 4821'."
    elif 'advisor' in user_input:
        adv = campus_data.get('advisors', [])[0]
        response = f"For {adv['department']}, your advisor is **{adv['name']}**. They are located in {adv['location']}. Hours: {adv['hours']}. Email: {adv['email']}."
    elif 'parking' in user_input:
        response = "For Engineering East, the best parking is **Lot 1 (Blue Lot)**, but it's usually full by 10am. Alternatively, try **Parking Garage 1** near the Student Union."
    elif 'hello' in user_input or 'hi' in user_input:
        response = "Hello! I'm Owl-Advisor, your AI assistant for FAU. I can help you find courses, check waitlists, locate buildings, find your advisor, or get parking info. What do you need help with?"
    else:
        response = "I'm still learning! I have data on FAU courses, buildings, parking, and advisors. Try asking: 'Where is EE?', 'Tell me about COP 3530 section 001', or 'Who is the CS advisor?'."
        
    return jsonify({"response": response})

if __name__ == '__main__':
    os.makedirs('static', exist_ok=True)
    app.run(host='0.0.0.0', debug=True, port=5000)
