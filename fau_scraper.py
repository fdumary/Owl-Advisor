import requests
from bs4 import BeautifulSoup
import json
import time

def scrape_fau_courses(term="202408"):
    """
    Attempts to scrape course data from FAU's public searchable schedule.
    Since Banner heavily relies on session cookies and hidden inputs, 
    this script demonstrates the conceptual workflow of scraping it.
    """
    print(f"Starting scraping for term {term}...")
    
    # Base URLs for Banner 9 / XE
    base_url = "https://bannerxe.fau.edu/StudentRegistrationSsb/ssb"
    term_select_url = f"{base_url}/term/search?mode=search"
    search_results_url = f"{base_url}/searchResults/searchResults"

    session = requests.Session()
    
    # 1. Initialize session and get cookies
    # Banner requires accepting terms or setting term in session first
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json, text/javascript, */*; q=0.01",
    }
    
    try:
        # Set term in session
        data = {"term": term, "studyPath": "", "studyPathText": "", "startDatepicker": "", "endDatepicker": ""}
        response = session.post(f"{base_url}/term/search?mode=search", data=data, headers=headers)
        
        # 2. Query search results
        # A typical payload for an open search across CS courses
        params = {
            "txt_subject": "COP",
            "txt_term": term,
            "startDatepicker": "",
            "endDatepicker": "",
            "pageOffset": 0,
            "pageMaxSize": 50,
            "sortColumn": "subjectDescription",
            "sortDirection": "asc"
        }
        res = session.get(search_results_url, params=params, headers=headers)
        
        if res.status_code == 200 and 'application/json' in res.headers.get('Content-Type', ''):
            json_data = res.json()
            if json_data.get('success'):
                courses = []
                for item in json_data.get('data', []):
                    course = {
                        "crn": item.get("courseReferenceNumber"),
                        "subject": item.get("subject"),
                        "course_number": item.get("courseNumber"),
                        "title": item.get("courseTitle"),
                        "credits": item.get("creditHourHigh"),
                        "instructor": item.get("faculty", [{}])[0].get("displayName", "TBA") if item.get("faculty") else "TBA",
                        "status": "Open" if item.get("seatsAvailable", 0) > 0 else "Closed",
                        "waitlist": item.get("waitAvailable", 0)
                    }
                    courses.append(course)
                
                print(f"Scraped {len(courses)} courses successfully.")
                
                # Save to data/course_data.json
                with open('data/course_data.json', 'w') as f:
                    json.dump(courses, f, indent=2)
                return True
            
        print("Failed to scrape live data. Proceeding with fallback static data for demo.")
        return False
        
    except Exception as e:
        print(f"Error scraping data: {e}")
        return False

if __name__ == "__main__":
    scrape_fau_courses()
