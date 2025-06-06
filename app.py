import streamlit as st
import pandas as pd
import gspread
import json
from io import StringIO
from oauth2client.service_account import ServiceAccountCredentials
from collections import Counter
from openai import OpenAI
from fpdf import FPDF
from datetime import datetime, date

st.set_option('client.showErrorDetails', True)

st.set_page_config(page_title="Mindful Libraries", layout="centered")

# --- Custom CSS for enhanced UI ---
st.markdown("""
    <style>
    body {
        background-color: #e8f0fe; /* Light blue background for the entire body */
        font-family: 'Inter', sans-serif;
    }

    /* Main content wrapper CSS removed as per user request */

    /* App-like Header (remains at the top of the main content area) */
    /* Targeting the header container in Streamlit and adjusting its appearance */
    /* Removed the explicit div wrapping for this section as per request to remove markdown containers */
    .st-emotion-cache-vk3357.e1nzilvr1 {
        background-color: #ffffff; /* White background for header */
        padding: 0.8rem 1.5rem; /* Adjusted padding */
        border-bottom: 1px solid #e0e0e0; /* Subtle border at the bottom */
        box-shadow: 0 2px 8px rgba(0,0,0,0.1); /* Clearer shadow for depth */
        border-radius: 0 0 12px 12px; /* Rounded bottom corners for the header */
        display: flex;
        align-items: center;
        justify-content: space-between; /* Space between logo and logout */
        position: sticky;
        top: 0;
        z-index: 1000;
        margin-bottom: 0; /* No margin-bottom here to reduce gap */
        width: 100%; /* Ensure header spans full width */
    }

    /* Adjust the main page title for a cleaner look */
    .st-emotion-cache-l9bizv.e1nzilvr5 h1 { /* Targeting specific h1 in Streamlit */
        display: none; /* Hide default Streamlit title */
    }

    /* Custom main app title to replace Streamlit's default h1 */
    h1 {
        text-align: center;
        color: #333333;
        margin-top: 2rem; /* Adjusted top margin after removing .main-content-wrapper */
        margin-bottom: 1.5rem;
        font-size: 2.5em; /* Make it stand out */
        font-weight: 700;
        letter-spacing: -0.02em;
    }

    /* Logo styling */
    .stImage > img {
        margin-left: 0; /* Align logo to the left */
        border-radius: 8px; /* Rounded corners for the logo */
        box-shadow: 1px 1px 3px rgba(0,0,0,0.1);
    }

    /* Buttons */
    .buy-button {
        background-color: #4285F4; /* A shade of blue for accent */
        color: white;
        padding: 0.7em 1.5em;
        border: none;
        border-radius: 8px; /* More rounded */
        text-decoration: none;
        font-weight: bold;
        margin-top: 15px;
        display: inline-block;
        transition: background-color 0.3s ease, transform 0.2s ease;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
    }
    .buy-button:hover {
        background-color: #3367D6; /* Darker blue on hover */
        transform: translateY(-2px);
    }
    .stButton>button {
        background-color: #4CAF50; /* Green button for generation */
        color: white;
        padding: 0.8em 2em;
        border: none;
        border-radius: 8px;
        font-weight: bold;
        transition: background-color 0.3s ease, transform 0.2s ease;
        box-shadow: 2px 2px 4px rgba(0,0,0,0.2); /* Reduced shadow */
    }
    .stButton>button:hover {
        background-color: #45a049;
        transform: translateY(-2px);
    }
    
    /* Text Inputs and Radios */
    .stTextInput>div>div>input {
        border-radius: 8px;
        padding: 10px;
        border: 1px solid #ccc;
        box-shadow: inset 0 1px 2px rgba(0,0,0,0.05); /* Inner shadow for input */
        transition: border-color 0.2s ease;
    }
    .stTextInput>div>div>input:focus {
        border-color: #4CAF50; /* Highlight on focus */
        outline: none;
    }
    .stRadio>label {
        font-weight: bold;
        color: #555;
    }

    /* Headings and Spinners */
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: #333333; /* Darker headings */
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #eeeeee; /* Subtle line under subheaders */
    }
    .stSpinner>div>div>span {
        color: #4CAF50 !important; /* Spinner color */
    }

    /* Alerts and Checkboxes */
    .stAlert {
        border-radius: 8px;
        background-color: #e6f7ff; /* Light blue for info alerts */
        border-color: #91d5ff;
        color: #004085;
    }
    .stAlert.success {
        background-color: #f6ffed; /* Light green for success */
        border-color: #b7eb8f;
        color: #1890ff;
    }
    .stAlert.warning {
        background-color: #fffbe6; /* Light yellow for warning */
        border-color: #ffe58f;
        color: #faad14;
    }
    .stCheckbox span { /* Style for checkbox labels */
        font-size: 1.1em;
        margin-left: 5px;
        color: #444;
    }

    /* Sidebar Navigation Button Styling */
    .stSidebar button { /* Target all buttons in the sidebar */
        width: calc(100% - 10px); /* Adjust width to account for padding */
        text-align: left; /* Align text to the left */
        margin-bottom: 0.5rem; /* Space between buttons */
        background-color: #f0f2f6; /* Light grey for inactive buttons */
        color: #333; /* Darker text */
        border: none;
        border-radius: 8px;
        padding: 0.8em 1.2em;
        font-weight: bold;
        transition: background-color 0.3s ease, color 0.3s ease, transform 0.2s ease;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); /* Subtle shadow for button depth */
    }

    .stSidebar button:hover {
        background-color: #e0e0e0; /* Slightly darker grey on hover */
        color: #007bff; /* Blue text on hover */
        transform: translateX(3px); /* Slight slide effect on hover */
    }

    /* Specific styling for the active navigation button to make it stand out */
    /* This targets Streamlit's internal element responsible for highlighting the active button */
    .stSidebar button[data-testid="stSidebarNav"] div[data-testid="stVerticalBlock"] > div:nth-child(even) > div > button {
        background-color: #007bff !important;
        color: white !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2) !important;
    }

    /* Content Cards CSS removed as per user request */


    /* Specific image styling within cards - remains, as images are still used */
    .stImage > img { /* Changed from .content-card img to a more general Streamlit image selector */
        border-radius: 8px;
        width: 100%;
        height: auto;
        max-width: 180px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    }

    /* Session History Items CSS removed as per user request */

    .session-history-item strong {
        color: #333;
    }

    /* Print Summary Text Area */
    .stTextArea > div > div {
        border-radius: 8px;
        border: 1px solid #ddd;
        padding: 10px;
        background-color: #f8f8f8;
        box-shadow: inset 0 1px 3px rgba(0,0,0,0.05);
    }
    </style>
""", unsafe_allow_html=True)


# --- Google Sheets and OpenAI Initialization ---
try:
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

    if "GOOGLE_SERVICE_JSON" not in st.secrets:
        st.error("❌ GOOGLE_SERVICE_JSON is missing from secrets.")
        st.stop()

    service_account_info = dict(st.secrets["GOOGLE_SERVICE_JSON"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
    client = gspread.authorize(creds)

    if "OPENAI_API_KEY" not in st.secrets:
        st.error("❌ OPENAI_API_KEY is missing from secrets.")
        st.stop()

    client_ai = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

except Exception as e:
    st.error(f"Failed to initialize Google Sheets or OpenAI client. Please check your `st.secrets` configuration. Error: {e}")
    st.stop()


@st.cache_data(ttl=3600)
def generate_activity_guide(activity_description, _ai_client):
    """Generates a downloadable plan with steps and a shopping or supply list for an activity."""
    prompt = f"""
    You are a helpful assistant. Based on the following activity description, create a detailed step-by-step guide including:
    - A supply list (or shopping list if applicable)
    - Clear, numbered instructions

    Activity Description: "{activity_description}"

    Format the response in markdown.
    """
    try:
        response = _ai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Could not generate activity guide. Error: {e}"

@st.cache_data(ttl=3600)
def load_content():
    """Loads content data from Google Sheet and processes tags."""
    try:
        sheet_url = 'https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXJRXcfmxjoj5s'
        sheet = client.open_by_url(sheet_url)
        content_ws = sheet.worksheet('ContentDB')
        df = pd.DataFrame(content_ws.get_all_records())
        if 'Tags' in df.columns:
            # Convert tags to a set of lowercase, stripped strings, excluding 'nostalgia'
            df['tags'] = df['Tags'].apply(lambda x: set(tag.strip().lower() for tag in str(x).split(',') if tag.strip().lower() != 'nostalgia'))
        else:
            df['tags'] = [set() for _ in range(len(df))]
            st.warning(" 'Tags' column not found in 'ContentDB' worksheet. Please ensure it exists.")
        return df
    except Exception as e:
        st.error(f"Failed to load content from Google Sheet. Error: {e}")
        return pd.DataFrame()

content_df = load_content()

# Initialize session state variables if they don't exist
if 'book_counter' not in st.session_state:
    st.session_state['book_counter'] = Counter()
if 'selected_tags' not in st.session_state:
    st.session_state['selected_tags'] = []
if 'active_tags_for_filter' not in st.session_state:
    st.session_state['active_tags_for_filter'] = []
if 'tag_checkbox_states' not in st.session_state:
    st.session_state['tag_checkbox_states'] = {}
if 'current_page' not in st.session_state: # New session state for page management
    st.session_state['current_page'] = 'dashboard' # Default page

# --- Pair Management Session State ---
if 'current_user_name' not in st.session_state: # This will now be the pair's name
    st.session_state['current_user_name'] = ""
if 'current_user_jobs' not in st.session_state:
    st.session_state['current_user_jobs'] = ""
if 'current_user_life_experiences' not in st.session_state:
    st.session_state['current_user_life_experiences'] = ""
if 'current_user_hobbies' not in st.session_state:
    st.session_state['current_user_hobbies'] = ""
if 'current_user_decade' not in st.session_state:
    st.session_state['current_user_decade'] = ""
if 'current_user_college_chapter' not in st.session_state:
    st.session_state['current_user_college_chapter'] = ""
if 'current_user_city' not in st.session_state: # New: City
    st.session_state['current_user_city'] = ""
if 'current_user_state' not in st.session_state: # New: State
    st.session_state['current_user_state'] = ""


# Session state for session notes
if 'session_date' not in st.session_state:
    st.session_state['session_date'] = date.today()
if 'session_mood' not in st.session_state:
    st.session_state['session_mood'] = "Neutral 😐"
if 'session_engagement' not in st.session_state:
    st.session_state['session_engagement'] = "Moderately Engaged ⭐⭐"
if 'session_takeaways' not in st.session_state:
    st.session_state['session_takeaways'] = ""
if 'recommended_books_current_session' not in st.session_state:
    st.session_state['recommended_books_current_session'] = []
if 'recommended_newspapers_current_session' not in st.session_state:
    st.session_state['recommended_newspapers_current_session'] = []
if 'recommended_activities_current_session' not in st.session_state:
    st.session_state['recommended_activities_current_session'] = [] # New: Store just activity titles
if 'activity_guides_for_pdf' not in st.session_state:
    st.session_state['activity_guides_for_pdf'] = [] # New: Store activities with guides for PDF

if 'show_printable_summary' not in st.session_state:
    st.session_state['show_printable_summary'] = False

# --- Authentication Session State ---
if 'is_authenticated' not in st.session_state:
    st.session_state['is_authenticated'] = False
if 'logged_in_username' not in st.session_state:
    st.session_state['logged_in_username'] = ""

# Global variable to store users and pairs, will be loaded from Google Sheet
USERS = {} # {username: password}
PAIRS_DATA = {} # {volunteer_username: {pair_name: {jobs: ..., hobbies: ...}}}

@st.cache_data(ttl=60) # Cache user data for 1 minute
def load_users():
    """Loads user credentials from the 'Users' Google Sheet."""
    users_dict = {}
    try:
        sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXJRXcfmxjoj5s')
        users_ws = sheet.worksheet('Users')
        records = users_ws.get_all_records()
        for record in records:
            username = record.get('Username')
            password = record.get('Password')
            if username and password:
                users_dict[username] = password
    except gspread.exceptions.WorksheetNotFound:
        st.warning("The 'Users' worksheet was not found. Please create a sheet named 'Users' with 'Username' and 'Password' columns to enable registration.")
    except Exception as e:
        st.error(f"Failed to load user data from Google Sheet. Error: {e}")
    return users_dict

@st.cache_data(ttl=60) # Cache pair data for 1 minute
def load_pairs(volunteer_username):
    """Loads pair data for a specific volunteer from the 'Pairs' Google Sheet."""
    pairs_dict = {}
    if not volunteer_username:
        return pairs_dict
    try:
        sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXJRXcfmxjoj5s')
        pairs_ws = sheet.worksheet('Pairs')
        records = pairs_ws.get_all_records()
        for record in records:
            if record.get('Volunteer Username', '').lower() == volunteer_username.lower():
                pair_name = record.get('Pair Name')
                if pair_name:
                    pairs_dict[pair_name] = {
                        'jobs': record.get('Jobs', ''),
                        'life_experiences': record.get('Life Experiences', ''),
                        'hobbies': record.get('Hobbies', ''),
                        'decade': record.get('Decade', ''),
                        'college_chapter': record.get('College Chapter', ''),
                        'city': record.get('City', ''), # Load new field
                        'state': record.get('State', '') # Load new field
                    }
    except gspread.exceptions.WorksheetNotFound:
        st.warning("The 'Pairs' worksheet was not found. Please create a sheet named 'Pairs' with 'Pair Name', 'Jobs', 'Life Experiences', 'Hobbies', 'Decade', 'College Chapter', 'City', 'State', and 'Volunteer Username' columns.")
    except Exception as e:
        st.error(f"Failed to load pair data. Error: {e}")
    return pairs_dict

# Load users and pairs at the start of the app (after client is authorized)
USERS.update(load_users())
if st.session_state['is_authenticated'] and st.session_state['logged_in_username']:
    PAIRS_DATA = load_pairs(st.session_state['logged_in_username'])

def save_new_user(username, password):
    """Saves a new user to the 'Users' Google Sheet."""
    try:
        sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXJRXcfmxjoj5s')
        users_ws = sheet.worksheet('Users')
        
        header_row = users_ws.row_values(1)
        if 'Username' not in header_row or 'Password' not in header_row:
            users_ws.append_row(['Username', 'Password'])
            st.info("Added 'Username' and 'Password' columns to 'Users' worksheet.")

        users_ws.append_row([username, password])
        st.success("Account registered successfully!")
        st.cache_data(load_users).clear() 
        USERS.update(load_users())
        return True
    except gspread.exceptions.WorksheetNotFound:
        st.error("Cannot register: 'Users' worksheet not found. Please create a sheet named 'Users' in your Google Sheet.")
        return False
    except Exception as e:
        st.error(f"Failed to register user. Error: {e}")
        return False

def save_pair_details(volunteer_username, pair_name, jobs, life_experiences, hobbies, decade, college_chapter, city, state):
    global PAIRS_DATA # Declare global at the very beginning of the function
    """Saves or updates pair details in the 'Pairs' Google Sheet."""
    try:
        sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXJRXcfmxjoj5s')
        pairs_ws = sheet.worksheet('Pairs')

        # Add 'College Chapter', 'City', 'State' to expected headers
        expected_headers = ['Pair Name', 'Jobs', 'Life Experiences', 'Hobbies', 'Decade', 'College Chapter', 'City', 'State', 'Volunteer Username']
        header_row = pairs_ws.row_values(1)
        new_headers_to_add = [h for h in expected_headers if h not in header_row]
        if new_headers_to_add:
            pairs_ws.append_row(header_row + new_headers_to_add)
            st.info(f"Added {', '.join(new_headers_to_add)} column(s) to 'Pairs' worksheet.")
            # Reload headers to ensure they are up-to-date for indexing
            header_row = pairs_ws.row_values(1)

        # Find existing row for this pair and volunteer
        records = pairs_ws.get_all_records(head=1) # Get records with first row as header
        found_row_idx = -1
        for i, record in enumerate(records):
            if record.get('Pair Name', '').lower() == pair_name.lower() and \
               record.get('Volunteer Username', '').lower() == volunteer_username.lower():
                found_row_idx = i + 2 # gspread row index is 1-based, plus header row
                break
        
        # Create a dictionary for mapping to header positions
        col_map = {header_name: i for i, header_name in enumerate(header_row)}
        
        # Prepare values to update, ensuring correct order based on header_row
        update_values = [''] * len(header_row) # Initialize with empty strings
        for i, h in enumerate(expected_headers):
            if h in col_map:
                if h == 'Pair Name': update_values[col_map[h]] = pair_name
                elif h == 'Jobs': update_values[col_map[h]] = jobs
                elif h == 'Life Experiences': update_values[col_map[h]] = life_experiences
                elif h == 'Hobbies': update_values[col_map[h]] = hobbies
                elif h == 'Decade': update_values[col_map[h]] = decade
                elif h == 'College Chapter': update_values[col_map[h]] = college_chapter
                elif h == 'City': update_values[col_map[h]] = city # Save new field
                elif h == 'State': update_values[col_map[h]] = state # Save new field
                elif h == 'Volunteer Username': update_values[col_map[h]] = volunteer_username

        if found_row_idx != -1:
            pairs_ws.update(f'A{found_row_idx}', [update_values])
            st.success(f"Details for '{pair_name}' updated successfully!")
        else:
            pairs_ws.append_row(update_values)
            st.success(f"New pair '{pair_name}' added successfully!")

        st.cache_data(load_pairs).clear()
        PAIRS_DATA = load_pairs(volunteer_username) # This assignment is now valid after global declaration
        return True
    except gspread.exceptions.WorksheetNotFound:
        st.error("Cannot save pair: 'Pairs' worksheet not found. Please create a sheet named 'Pairs' in your Google Sheet.")
        return False
    except Exception as e:
        st.error(f"Failed to save pair details. Error: {e}")
        return False


# This function is not used in the current code, but kept for context if PDF generation is needed.
def generate_pdf(name, topics, recs):
    """Generates a PDF summary of recommendations (currently unused)."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=14)
    pdf.cell(200, 10, txt=f"Reading Recommendations for {name}", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Top 10 Personalized Tags:", ln=True)
    for topic in topics:
        pdf.cell(200, 10, txt=f"- {topic}", ln=True)
    pdf.ln(10)
    pdf.cell(200, 10, txt="Recommended Reads:", ln=True)
    for r in recs:
        pdf.multi_cell(0, 10, txt=f"{r.get('Title', 'N/A')} ({r.get('Type', 'N/A')}): {r.get('Summary', 'N/A')}")
        pdf.ln(2)
    return pdf

# Function to save user input to Google Sheet (Logs)
def save_user_input(name, jobs, hobbies, decade, selected_topics, volunteer_username, college_chapter):
    """Saves user input to the 'Logs' Google Sheet."""
    try:
        sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXJRXcfmxjoj5s')
        log_ws = sheet.worksheet('Logs')
        # Check if 'Volunteer Username' and 'College Chapter' column exists, if not, add it
        header_row = log_ws.row_values(1)
        new_log_headers_to_add = []
        if 'Volunteer Username' not in header_row:
            new_log_headers_to_add.append('Volunteer Username')
        if 'College Chapter' not in header_row:
            new_log_headers_to_add.append('College Chapter')

        if new_log_headers_to_add:
            log_ws.append_row(header_row + new_log_headers_to_add) # Append new headers
            st.info(f"Added {', '.join(new_log_headers_to_add)} column(s) to 'Logs' worksheet.")
            header_row = log_ws.row_values(1) # Reload headers after adding

        # Prepare values to update, ensuring correct order based on header_row
        log_col_map = {header_name: i for i, header_name in enumerate(header_row)}
        log_update_values = [''] * len(header_row) # Initialize with empty strings
        
        # Populate values based on mapped positions
        if 'Timestamp' in log_col_map: log_update_values[log_col_map['Timestamp']] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if 'Name' in log_col_map: log_update_values[log_col_map['Name']] = name
        if 'Jobs' in log_col_map: log_update_values[log_col_map['Jobs']] = jobs
        if 'Hobbies' in log_col_map: log_update_values[log_col_map['Hobbies']] = hobbies
        if 'Decade' in log_col_map: log_update_values[log_col_map['Decade']] = decade
        if 'Selected Topics' in log_col_map: log_update_values[log_col_map['Selected Topics']] = ", ".join(selected_topics)
        if 'Volunteer Username' in log_col_map: log_update_values[log_col_map['Volunteer Username']] = volunteer_username
        if 'College Chapter' in log_col_map: log_update_values[log_col_map['College Chapter']] = college_chapter # Save new field

        log_ws.append_row(log_update_values)
    except Exception as e:
        st.warning(f"Failed to save user data. Error: {e}")

# Function to save session notes to Google Sheet (SessionLogs)
def save_session_notes_to_gsheet(pair_name, session_date, mood, engagement, takeaways, recommended_materials_json, volunteer_username):
    """Saves session notes to the 'SessionLogs' Google Sheet."""
    try:
        sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXJRXcfmxjoj5s')
        session_log_ws = sheet.worksheet('SessionLogs')
        # Check if 'Volunteer Username' and 'Recommended Materials' columns exist, if not, add them
        header_row = session_log_ws.row_values(1)
        new_headers_to_add = []
        if 'Volunteer Username' not in header_row:
            new_headers_to_add.append('Volunteer Username')
        if 'Recommended Materials' not in header_row:
            new_headers_to_add.append('Recommended Materials')
        
        if new_headers_to_add:
            session_log_ws.append_row(header_row + new_headers_to_add)
            st.info(f"Added {', '.join(new_headers_to_add)} column(s) to 'SessionLogs' worksheet.")

        # Ensure values are stripped before saving to prevent future issues
        stripped_pair_name = pair_name.strip()
        stripped_volunteer_username = volunteer_username.strip()

        session_log_ws.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            stripped_pair_name, # Use stripped value
            session_date.strftime("%Y-%m-%d"),
            mood,
            engagement,
            takeaways,
            stripped_volunteer_username, # Use stripped value
            recommended_materials_json
        ])
        st.success("Session notes saved successfully!")
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Failed to save session notes: 'SessionLogs' worksheet not found. Please create a sheet named 'SessionLogs' in your Google Sheet.")
    except Exception as e:
        st.error(f"Failed to save session notes. Error: {e}")

@st.cache_data(ttl=60) # Cache session logs for 1 minute
def load_session_logs(pair_name, volunteer_username):
    """Loads session logs for a specific pair and volunteer from Google Sheet."""
    if not pair_name or not volunteer_username: # Require both pair_name and volunteer_username
        return pd.DataFrame()
    
    try:
        sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXJRXcfmxjoj5s')
        session_log_ws = sheet.worksheet('SessionLogs')
        
        all_values = session_log_ws.get_all_values()

        if not all_values:
            st.info("No data found in the 'SessionLogs' worksheet. The sheet might be empty or the data is not in the expected format.")
            return pd.DataFrame()

        raw_headers = [str(h).strip() for h in all_values[0]]
        
        cleaned_headers = []
        header_name_counts = Counter()
        for header in raw_headers:
            if not header:
                header_name_counts['Unnamed'] += 1
                cleaned_headers.append(f'Unnamed_{header_name_counts["Unnamed"]}')
            elif header in cleaned_headers:
                header_name_counts[header] += 1
                cleaned_headers.append(f'{header}_{header_name_counts[header]}')
            else:
                cleaned_headers.append(header)

        data_rows = all_values[1:]

        df_raw = pd.DataFrame(data_rows, columns=cleaned_headers)

        # Define the exact expected headers for the final DataFrame
        expected_headers = ['Timestamp', 'Pair Name', 'Session Date', 'Mood', 'Engagement', 'Takeaways', 'Volunteer Username', 'Recommended Materials']
        
        df_final = pd.DataFrame()
        for col in expected_headers:
            # Find the best match for the expected column name, considering potential numbered duplicates
            found_col_name = None
            for df_col in df_raw.columns:
                if df_col == col or (df_col.startswith(f"{col}_") and df_col[len(col):].replace('_', '').isdigit()):
                    found_col_name = df_col
                    break
            
            if found_col_name and found_col_name in df_raw.columns:
                df_final[col] = df_raw[found_col_name]
            else:
                df_final[col] = '' # Add missing column with empty string

        # Ensure 'Pair Name' and 'Volunteer Username' are cleaned for filtering
        if 'Pair Name' in df_final.columns:
            df_final['Pair Name'] = df_final['Pair Name'].astype(str).str.strip().str.lower()
        if 'Volunteer Username' in df_final.columns:
            df_final['Volunteer Username'] = df_final['Volunteer Username'].astype(str).str.strip().str.lower()

        # Filter by both Pair Name and Volunteer Username, ensuring comparison values are also cleaned
        filtered_df = df_final[
            (df_final['Pair Name'] == pair_name.strip().lower()) &
            (df_final['Volunteer Username'] == volunteer_username.strip().lower())
        ].sort_values(by='Timestamp', ascending=False)
        
        return filtered_df

    except gspread.exceptions.WorksheetNotFound:
        st.info(f"The 'SessionLogs' worksheet was not found. Please create a sheet named 'SessionLogs' in your Google Sheet to enable session history tracking.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Could not load session history for {pair_name} and {volunteer_username}. An unexpected error occurred: {e}. "
                 "This often happens if there are empty or duplicate column headers in your 'SessionLogs' worksheet, "
                 "or if the column names do not exactly match. "
                 "Please ensure the first row of your 'SessionLogs' sheet contains unique and clear headers like "
                 "'Timestamp', 'Pair Name', 'Session Date', 'Mood', 'Engagement', 'Takeaways', 'Recommended Materials', 'Volunteer Username'. "
                 "Also, check for any entirely blank leading columns that might be causing issues.")
        return pd.DataFrame()

@st.cache_data(ttl=3600) # Cache the explanation for an hour
def generate_recommendation_explanation(item, user_info, selected_tags_from_session, _ai_client):
    """Generates an AI-powered explanation for a specific recommendation."""
    prompt = f"""
    You are a helpful assistant for a student volunteer working with an individual living with dementia.
    Explain why the following reading material is a good recommendation for a session with their pair, given the user's background and the item's details. Focus on how it could spark positive memories, facilitate conversation, or provide a calming activity. Frame it as if you are giving advice to the student volunteer.

    User's Background:
    Name: {user_info['name']}
    Job: {user_info['jobs'] if user_info['jobs'] else 'Not provided'}
    Hobbies: {user_info['hobbies'] if user_info['hobbies'] else 'Not provided'}
    Favorite Decade: {user_info['decade'] if user_info['decade'] else 'Not provided'}
    Significant Life Experiences: {user_info['life_experiences'] if user_info['life_experiences'] else 'Not provided'}
    College Chapter: {user_info['college_chapter'] if user_info['college_chapter'] else 'Not provided'}
    City: {user_info['city'] if 'city' in user_info and user_info['city'] else 'Not provided'}
    State: {user_info['state'] if 'state' in user_info and user_info['state'] else 'Not provided'}

    Recommended Item:
    Title: {item.get('Title', 'N/A')}
    Type: {item.get('Type', 'N/A')}
    Summary: {item.get('Summary', 'N/A')}
    Tags: {', '.join(item.get('tags', set()))}

    The personalized tags for the user that led to this recommendation were: {', '.join(selected_tags_from_session)}

    Explain in 2-3 sentences.
    """
    try:
        response = _ai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Could not generate explanation at this time. Error: {e}"

@st.cache_data(ttl=3600) # Cache the historical context for an hour
def generate_historical_context(decade, _ai_client):
    """Generates a brief, positive historical overview for a given decade."""
    prompt = f"""
    You are a helpful assistant for a student volunteer working with an individual living with dementia.
    Given the decade "{decade}", provide a brief (2-3 sentences), positive, and gentle overview of what made that era special. Focus on aspects that could evoke pleasant memories, such as common pastimes, cultural trends, or general positive feelings associated with the period. This information will help the student volunteer understand the context for their pair. Avoid any potentially sensitive or negative historical events.
    """
    try:
        response = _ai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Could not retrieve historical context for {decade}. Error: {e}"

@st.cache_data(ttl=3600) # Cache the expanded search tags for an hour
def get_ai_expanded_search_tags(search_term, content_tags_list, _ai_client):
    """Uses AI to expand a search term into relevant content tags."""
    if not search_term:
        return set()

    search_prompt = f"""
        Given the user's search query, provide up to 10 relevant and specific tags from the following list that would help find related reading content.
        Ensure the tags you return are exactly from the 'Available tags' list.
        Available tags:
        {", ".join(content_tags_list)}

        User search query: "{search_term}"

        Only return comma-separated tags from the list above. Do not include any additional text or formatting.
    """
    try:
        response = _ai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": search_prompt}] # Corrected from 'prompt' to 'search_prompt'
        )
        ai_tags_output = response.choices[0].message.content.strip()
        ai_tags_from_response = {t.strip().lower() for t in ai_tags_output.split(',') if t.strip()}
        return ai_tags_from_response.intersection(set(content_tags_list))
    except Exception as e:
        st.warning(f"Could not expand search with AI. Error: {e}")
        return set() # Return empty set on error

@st.cache_data(ttl=600) # Cache feedback scores for 10 minutes, can be adjusted based on update frequency
def load_feedback_tag_scores():
    """Loads tag scores from the 'Feedback' Google Sheet for reweighting."""
    feedback_scores = {}
    try:
        sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXJRXcfmxjoj5s')
        fb_ws = sheet.worksheet('Feedback')
        fb_data = pd.DataFrame(fb_ws.get_all_records())
        for _, row in fb_data.iterrows():
            tags_str = str(row.get('Tags', '')).strip()
            feedback_str = str(row.get('Feedback', '')).strip().lower()
            if tags_str and feedback_str:
                for tag in tags_str.split(','):
                    tag = tag.strip().lower()
                    if tag:
                        feedback_scores[tag] = feedback_scores.get(tag, 0) + (1 if 'yes' in feedback_str else -1)
    except Exception as e:
        st.info(f"Could not load feedback tag scores. Recommendations will not be reweighted by feedback. Error: {e}")
    return feedback_scores

@st.cache_data(ttl=3600) # Cache the activity suggestions for an hour
def generate_activities(_ai_client, active_tags, recommended_titles):
    """Generates 5-10 general activity suggestions based on tags and recommended titles."""
    if not active_tags and not recommended_titles:
        return ["No specific tags or recommended titles to suggest activities for. Try generating personalized tags first!"]

    titles_str = ", ".join(recommended_titles) if recommended_titles else "No specific reading materials recommended yet."
    prompt = f"""
    You are a helpful assistant for a student volunteer working with an individual living with dementia.
    Given the following key interests (tags) and recommended reading materials, suggest 5-10 gentle and engaging activities that a student volunteer can do with their pair. Always include "Reading the recommended books/newspapers together and discussing them" as one of the suggestions. Focus on activities that can spark positive memories, facilitate conversation, and provide calming engagement, suitable for individuals with dementia.

    Key Interests (Tags): {', '.join(active_tags)}
    Recommended Reading Titles: {titles_str}

    Suggest activities in a numbered list format. Each activity should be a short, actionable sentence.
    """
    try:
        response = _ai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        generated_activities = response.choices[0].message.content.strip().split('\n')
        # Filter out empty strings and ensure each item is stripped
        clean_activities = [activity.strip() for activity in generated_activities if activity.strip()]
        # Ensure that only 5-10 activities are returned if the AI generates more or less
        if len(clean_activities) < 5:
            return clean_activities
        else:
            return clean_activities[:10]
    except Exception as e:
        return [f"Could not generate activity suggestions at this time. Error: {e}"]

@st.cache_data(ttl=3600) # Cache the activity suggestions for an hour
def generate_location_based_activities(_ai_client, city, state, pair_hobbies, pair_decade):
    """Generates location-based activity suggestions using AI (without Google Search)."""
    if not city or not state:
        return ["Please enter the Pair's City and State in the Pair Profile to get location-based suggestions."]

    combined_info = f"City: {city}, State: {state}\n"
    if pair_hobbies: combined_info += f"Pair Hobbies: {pair_hobbies}\n"
    if pair_decade: combined_info += f"Pair Favorite Decade: {pair_decade}\n"

    prompt = f"""
    You are a helpful assistant for a student volunteer working with an individual living with dementia.
    Given the following location and pair interests, suggest 5-10 gentle and engaging activities that are available locally or can be related to the local area, suitable for individuals with dementia. Focus on activities that can spark positive memories, facilitate conversation, and provide calming engagement. Since direct search is not available, provide general but relevant ideas for the specified city/state and interests.

    Information:
    {combined_info}

    Suggest activities in a numbered list format. Each activity should be a short, actionable sentence.
    """
    try:
        response = _ai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        generated_activities = response.choices[0].message.content.strip().split('\n')
        clean_activities = [activity.strip() for activity in generated_activities if activity.strip()]
        return clean_activities[:10]
    except Exception as e:
        return [f"Could not generate location-based activity suggestions at this time. Error: {e}"]

def get_printable_summary(user_info, tags, books, newspapers, activities_with_guides, volunteer_username):
    """Generates a formatted string summary for printing, including activity guides."""
    summary = f"--- Session Plan Summary for {user_info['name'] if user_info['name'] else 'Your Pair'} ---\n\n"
    summary += f"Date: {datetime.now().strftime('%Y-%m-%d')}\n"
    summary += f"Volunteer: {volunteer_username}\n"
    summary += f"User Profile:\n"
    summary += f" Job: {user_info['jobs'] if user_info['jobs'] else 'N/A'}\n"
    summary += f" Life Experiences: {user_info['life_experiences'] if user_info['life_experiences'] else 'N/A'}\n"
    summary += f" Hobbies: {user_info['hobbies'] if user_info['hobbies'] else 'N/A'}\n"
    summary += f" Favorite Decade: {user_info['decade'] if user_info['decade'] else 'N/A'}\n"
    summary += f" College Chapter: {user_info['college_chapter'] if user_info['college_chapter'] else 'N/A'}\n"
    summary += f" City: {user_info['city'] if 'city' in user_info and user_info['city'] else 'N/A'}\n"
    summary += f" State: {user_info['state'] if 'state' in user_info and user_info['state'] else 'N/A'}\n\n"
    summary += f"Personalized Tags:\n- {', '.join(tags)}\n\n"

    if books:
        summary += "Recommended Books:\n"
        for book in books:
            summary += f"- Title: {book.get('Title', 'N/A')}\n"
            summary += f"  Summary: {book.get('Summary', 'N/A')}\n"
            summary += f"  Link: {book.get('URL', 'N/A')}\n\n"

    if newspapers:
        summary += "Recommended Newspapers:\n"
        for newspaper in newspapers:
            summary += f"- Title: {newspaper.get('Title', 'N/A')}\n"
            summary += f"  Summary: {newspaper.get('Summary', 'N/A')}\n"
            summary += f"  Link: {newspaper.get('URL', 'N/A')}\n\n"

    if activities_with_guides: # New section for activities with guides
        summary += "Suggested Activities with How-To Guides:\n"
        for item in activities_with_guides:
            summary += f"--- Activity: {item['activity']}\n"
            summary += f"{item['guide']}\n\n" # Add the guide content
    else:
        summary += "No Suggested Activities.\n\n"

    summary += "\n--- End of Summary ---"
    return summary

def create_pdf_from_summary(summary_text, filename="session_summary.pdf"):
    """Creates a PDF from a given summary text."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    # Use multi_cell to handle line breaks in the summary text
    # Encode to latin-1 and decode back to handle non-ASCII characters gracefully for FPDF
    pdf.multi_cell(0, 10, summary_text.encode('latin-1', 'replace').decode('latin-1'))
    st.download_button(
        label="Download Summary as PDF",
        data=pdf.output(dest='S').encode('latin-1'),
        file_name=filename,
        mime="application/pdf",
        key="download_pdf_button"
    )

# --- Login/Registration Functions ---
def login():
    st.title("Welcome to Mindful Libraries")
    st.subheader("Login")
    with st.form("login_form"):
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("Login"):
                if username in USERS and USERS[username] == password:
                    st.session_state['is_authenticated'] = True
                    st.session_state['logged_in_username'] = username
                    st.session_state['current_page'] = 'dashboard' # Navigate to dashboard on successful login
                    st.success("Logged in successfully!")
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
        with col2:
            if st.form_submit_button("Register"):
                st.session_state['current_page'] = 'register'
                st.rerun()

def register():
    st.title("Mindful Libraries")
    st.subheader("Register New Account")
    with st.form("register_form"):
        new_username = st.text_input("Choose Username", key="new_username")
        new_password = st.text_input("Choose Password", type="password", key="new_password")
        confirm_password = st.text_input("Confirm Password", type="password", key="confirm_password")
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("Create Account"):
                if new_username and new_password and confirm_password:
                    if new_password == confirm_password:
                        if new_username not in USERS:
                            if save_new_user(new_username, new_password):
                                # Automatically log in after successful registration
                                st.session_state['is_authenticated'] = True
                                st.session_state['logged_in_username'] = new_username
                                st.session_state['current_page'] = 'dashboard'
                                st.rerun()
                        else:
                            st.warning("Username already exists. Please choose a different one.")
                    else:
                        st.error("Passwords do not match.")
                else:
                    st.error("Please fill in all fields.")
        with col2:
            if st.form_submit_button("Back to Login"):
                st.session_state['current_page'] = 'login'
                st.rerun()

def logout():
    st.session_state['is_authenticated'] = False
    st.session_state['logged_in_username'] = ""
    st.session_state['current_page'] = 'login' # Go back to login page
    st.success("Logged out successfully.")
    st.rerun()

# --- Main App Logic ---
if not st.session_state['is_authenticated']:
    if st.session_state['current_page'] == 'register':
        register()
    else:
        login()
else:
    # Sidebar navigation
    st.sidebar.image("https://i.ibb.co/q17Y0r7/Logo.png", use_column_width=True)
    st.sidebar.title(f"Hello, {st.session_state['logged_in_username']}") # Corrected: Removed extraneous characters

    if st.sidebar.button("Dashboard"):
        st.session_state['current_page'] = 'dashboard'
    if st.sidebar.button("Pair Profile"):
        st.session_state['current_page'] = 'pair_profile'
    if st.sidebar.button("Session Notes"):
        st.session_state['current_page'] = 'session_notes'
    if st.sidebar.button("Session History"):
        st.session_state['current_page'] = 'session_history'
    if st.sidebar.button("Decade Summary"):
        st.session_state['current_page'] = 'decade_summary'
    if st.sidebar.button("Logout"):
        logout()

    # --- Dashboard Page ---
    if st.session_state['current_page'] == 'dashboard':
        st.header("Home Dashboard")
        st.write("Welcome to your Mindful Libraries dashboard. Use the sidebar to navigate.")
        st.subheader("Your Pairs:")
        if PAIRS_DATA:
            current_pairs_list = list(PAIRS_DATA.keys())
            
            # Add "Select a Pair" as the first option
            display_pairs = ["Select a Pair"] + current_pairs_list
            
            # Find the index of the currently selected pair, if any, for setting default
            try:
                default_index = display_pairs.index(st.session_state['current_user_name'])
            except ValueError:
                default_index = 0 # Default to "Select a Pair" if not found or initial state

            selected_pair_name = st.selectbox(
                "Choose an existing Pair:",
                options=display_pairs,
                index=default_index,
                key="dashboard_pair_selector"
            )

            if selected_pair_name and selected_pair_name != "Select a Pair":
                st.session_state['current_user_name'] = selected_pair_name
                pair_details = PAIRS_DATA.get(selected_pair_name, {})
                st.session_state['current_user_jobs'] = pair_details.get('jobs', '')
                st.session_state['current_user_life_experiences'] = pair_details.get('life_experiences', '')
                st.session_state['current_user_hobbies'] = pair_details.get('hobbies', '')
                st.session_state['current_user_decade'] = pair_details.get('decade', '')
                st.session_state['current_user_college_chapter'] = pair_details.get('college_chapter', '')
                st.session_state['current_user_city'] = pair_details.get('city', '') # Load city
                st.session_state['current_user_state'] = pair_details.get('state', '') # Load state

                st.success(f"Loaded profile for: {st.session_state['current_user_name']}")
                st.write(f"**Jobs:** {st.session_state['current_user_jobs']}")
                st.write(f"**Life Experiences:** {st.session_state['current_user_life_experiences']}")
                st.write(f"**Hobbies:** {st.session_state['current_user_hobbies']}")
                st.write(f"**Favorite Decade:** {st.session_state['current_user_decade']}")
                st.write(f"**College Chapter:** {st.session_state['current_user_college_chapter']}")
                st.write(f"**City:** {st.session_state['current_user_city']}") # Display City
                st.write(f"**State:** {st.session_state['current_user_state']}") # Display State

            else:
                st.info("Select a pair or create a new one in 'Pair Profile'.")
        else:
            st.info("No pairs added yet. Go to 'Pair Profile' to add a new pair.")

    # --- Pair Profile Page ---
    elif st.session_state['current_page'] == 'pair_profile':
        st.header("Pair Profile")
        st.info("Enter or update your pair's details here. Make sure to click 'Save Pair Details'!")

        # Input fields for pair's details
        st.session_state['current_user_name'] = st.text_input("Pair's Name", value=st.session_state['current_user_name'])
        st.session_state['current_user_jobs'] = st.text_area("Jobs (e.g., Teacher, Engineer)", value=st.session_state['current_user_jobs'])
        st.session_state['current_user_life_experiences'] = st.text_area("Significant Life Experiences (e.g., lived abroad, military service)", value=st.session_state['current_user_life_experiences'])
        st.session_state['current_user_hobbies'] = st.text_area("Hobbies (e.g., gardening, painting, sports)", value=st.session_state['current_user_hobbies'])
        st.session_state['current_user_decade'] = st.text_input("Favorite Decade (e.g., 1950s, 1960s)", value=st.session_state['current_user_decade'])
        st.session_state['current_user_college_chapter'] = st.text_input("College Chapter (e.g., Alpha Beta Gamma)", value=st.session_state['current_user_college_chapter'])
        st.session_state['current_user_city'] = st.text_input("City", value=st.session_state['current_user_city']) # New input
        st.session_state['current_user_state'] = st.text_input("State", value=st.session_state['current_user_state']) # New input


        # Save button for pair details
        st.button(
            "Save Pair Details",
            on_click=lambda: save_pair_details(
                st.session_state['logged_in_username'],
                st.session_state['current_user_name'],
                st.session_state['current_user_jobs'],
                st.session_state['current_user_life_experiences'],
                st.session_state['current_user_hobbies'],
                st.session_state['current_user_decade'],
                st.session_state['current_user_college_chapter'],
                st.session_state['current_user_city'], # New argument
                st.session_state['current_user_state'] # New argument
            )
        )

        st.subheader("Generate Personalized Tags and Recommendations")
        if st.session_state['current_user_name']:
            if st.button("Generate Personalized Tags"):
                user_info = {
                    "name": st.session_state['current_user_name'],
                    "jobs": st.session_state['current_user_jobs'],
                    "life_experiences": st.session_state['current_user_life_experiences'],
                    "hobbies": st.session_state['current_user_hobbies'],
                    "decade": st.session_state['current_user_decade'],
                    "college_chapter": st.session_state['current_user_college_chapter'],
                    "city": st.session_state['current_user_city'], # Include city
                    "state": st.session_state['current_user_state'] # Include state
                }
                all_available_tags = {tag for tags_set in content_df['tags'] for tag in tags_set}
                
                with st.spinner("Generating personalized tags..."):
                    personalized_tags_str = client_ai.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant that generates personalized tags for a person living with dementia based on their profile. Select relevant tags from the provided list. If you generate more than 10 tags, prioritize the most relevant. Do not include 'nostalgia' unless it is explicitly mentioned by the user as a tag to generate. If the user provides a college chapter, also include tags related to common college activities like 'campus life', 'college sports', 'student clubs', 'academics', 'fraternity/sorority life', or specific chapter names if applicable. If no relevant tags are found, state 'No specific tags found based on the provided profile.'"},
                            {"role": "user", "content": f"Generate personalized tags for a person with the following profile:\nJobs: {user_info['jobs']}\nLife Experiences: {user_info['life_experiences']}\nHobbies: {user_info['hobbies']}\nFavorite Decade: {user_info['decade']}\nCollege Chapter: {user_info['college_chapter']}\nCity: {user_info['city']}\nState: {user_info['state']}\n\nAvailable tags: {', '.join(all_available_tags)}\n\nOnly return comma-separated tags from the available list. Do not include any additional text or formatting."}
                        ]
                    ).choices[0].message.content.strip()

                    if personalized_tags_str == 'No specific tags found based on the provided profile.':
                        st.session_state['selected_tags'] = []
                        st.info(personalized_tags_str)
                    else:
                        st.session_state['selected_tags'] = [tag.strip().lower() for tag in personalized_tags_str.split(',') if tag.strip()]
                        
                        # Filter to ensure only valid tags from the content_df are kept
                        st.session_state['selected_tags'] = [tag for tag in st.session_state['selected_tags'] if tag in all_available_tags]

                        if st.session_state['selected_tags']:
                            st.success("Personalized tags generated!")
                            st.write("Suggested Tags:")
                            st.session_state['active_tags_for_filter'] = [] # Reset for new session
                            st.session_state['tag_checkbox_states'] = {tag: True for tag in st.session_state['selected_tags']} # All active by default

                            cols = st.columns(3)
                            for i, tag in enumerate(st.session_state['selected_tags']):
                                with cols[i % 3]:
                                    st.session_state['tag_checkbox_states'][tag] = st.checkbox(
                                        tag.title(),
                                        value=st.session_state['tag_checkbox_states'][tag],
                                        key=f"tag_checkbox_{tag}"
                                    )
                                    if st.session_state['tag_checkbox_states'][tag]:
                                        st.session_state['active_tags_for_filter'].append(tag)
                            st.info("Adjust the checkboxes to refine your recommendations.")
                        else:
                            st.info("No personalized tags could be generated for the given profile. Try adding more details.")
            
            # Always display active tags and search bar if selected_tags exist
            if st.session_state['selected_tags']:
                st.subheader("Filter Content by Tags:")
                active_tags_display = st.session_state['active_tags_for_filter'] if st.session_state['active_tags_for_filter'] else ["No active tags selected."]
                st.markdown(f"**Active Tags:** {', '.join(active_tags_display).title()}")

                search_query = st.text_input("Search for additional tags (e.g., 'gardening'):", key="tag_search_input")
                if st.button("Add Search Tags"):
                    if search_query:
                        all_available_tags = {tag for tags_set in content_df['tags'] for tag in tags_set}
                        ai_expanded_tags = get_ai_expanded_search_tags(search_query, list(all_available_tags), client_ai)
                        
                        if ai_expanded_tags:
                            new_tags_added = False
                            for tag in ai_expanded_tags:
                                if tag not in st.session_state['selected_tags']:
                                    st.session_state['selected_tags'].append(tag)
                                    st.session_state['tag_checkbox_states'][tag] = True
                                    new_tags_added = True
                            if new_tags_added:
                                st.success(f"Added relevant tags from search: {', '.join(ai_expanded_tags).title()}")
                                st.rerun() # Rerun to update checkboxes
                            else:
                                st.info("No new relevant tags found from your search that aren't already selected.")
                        else:
                            st.info("No tags found for your search query.")
                    else:
                        st.warning("Please enter a search query for tags.")
                
                # Dynamic checkboxes for all selected tags (including AI expanded ones)
                if st.session_state['selected_tags']:
                    st.write("Refine Tags:")
                    st.session_state['active_tags_for_filter'] = []
                    cols = st.columns(3)
                    for i, tag in enumerate(st.session_state['selected_tags']):
                        with cols[i % 3]:
                            st.session_state['tag_checkbox_states'][tag] = st.checkbox(
                                tag.title(),
                                value=st.session_state['tag_checkbox_states'].get(tag, False), # Ensure initial state is False if not set
                                key=f"dynamic_tag_checkbox_{tag}"
                            )
                            if st.session_state['tag_checkbox_states'][tag]:
                                st.session_state['active_tags_for_filter'].append(tag)


                st.subheader("Recommended Reading Materials")
                if st.session_state['active_tags_for_filter']:
                    # Filter content based on active tags, prioritizing items with more matching tags
                    filtered_content = content_df[
                        content_df['tags'].apply(lambda x: bool(x.intersection(st.session_state['active_tags_for_filter'])))
                    ].copy() # Use .copy() to avoid SettingWithCopyWarning
                    
                    if not filtered_content.empty:
                        # Calculate a score for each item based on how many active tags it matches
                        filtered_content['score'] = filtered_content['tags'].apply(
                            lambda x: len(x.intersection(st.session_state['active_tags_for_filter']))
                        )

                        # Load feedback scores for reweighting
                        feedback_scores = load_feedback_tag_scores()
                        if feedback_scores:
                            filtered_content['feedback_score'] = filtered_content['tags'].apply(
                                lambda x: sum(feedback_scores.get(tag, 0) for tag in x.intersection(st.session_state['active_tags_for_filter']))
                            )
                            # Combine content score with feedback score, giving more weight to content match
                            filtered_content['final_score'] = filtered_content['score'] * 10 + filtered_content['feedback_score']
                            recommended_items = filtered_content.sort_values(by='final_score', ascending=False)
                        else:
                            recommended_items = filtered_content.sort_values(by='score', ascending=False)

                        # Categorize recommendations into books and newspapers
                        recommended_books = recommended_items[recommended_items['Type'] == 'Book'].head(5).to_dict('records')
                        recommended_newspapers = recommended_items[recommended_items['Type'] == 'Newspaper'].head(5).to_dict('records')
                        
                        st.session_state['recommended_books_current_session'] = recommended_books
                        st.session_state['recommended_newspapers_current_session'] = recommended_newspapers

                        if recommended_books:
                            st.write("---")
                            st.markdown("##### 📚 Top Recommended Books:")
                            for book in recommended_books:
                                st.markdown(f"**Title:** {book.get('Title', 'N/A')}")
                                st.markdown(f"**Summary:** {book.get('Summary', 'N/A')}")
                                st.markdown(f"**Link:** [{book.get('URL', 'N/A')}]({book.get('URL', '#')})")
                                # Generate and display explanation
                                user_info_for_explanation = {
                                    "name": st.session_state['current_user_name'],
                                    "jobs": st.session_state['current_user_jobs'],
                                    "life_experiences": st.session_state['current_user_life_experiences'],
                                    "hobbies": st.session_state['current_user_hobbies'],
                                    "decade": st.session_state['current_user_decade'],
                                    "college_chapter": st.session_state['current_user_college_chapter'],
                                    "city": st.session_state['current_user_city'],
                                    "state": st.session_state['current_user_state']
                                }
                                with st.spinner(f"Generating explanation for '{book.get('Title', 'N/A')}'..."):
                                    explanation = generate_recommendation_explanation(book, user_info_for_explanation, st.session_state['active_tags_for_filter'], client_ai)
                                    st.info(explanation)
                                st.write("---")
                        else:
                            st.info("No books found for the selected tags.")

                        if recommended_newspapers:
                            st.write("---")
                            st.markdown("##### 📰 Top Recommended Newspapers/Articles:")
                            for newspaper in recommended_newspapers:
                                st.markdown(f"**Title:** {newspaper.get('Title', 'N/A')}")
                                st.markdown(f"**Summary:** {newspaper.get('Summary', 'N/A')}")
                                st.markdown(f"**Link:** [{newspaper.get('URL', 'N/A')}]({newspaper.get('URL', '#')})")
                                # Generate and display explanation
                                user_info_for_explanation = {
                                    "name": st.session_state['current_user_name'],
                                    "jobs": st.session_state['current_user_jobs'],
                                    "life_experiences": st.session_state['current_user_life_experiences'],
                                    "hobbies": st.session_state['current_user_hobbies'],
                                    "decade": st.session_state['current_user_decade'],
                                    "college_chapter": st.session_state['current_user_college_chapter'],
                                    "city": st.session_state['current_user_city'],
                                    "state": st.session_state['current_user_state']
                                }
                                with st.spinner(f"Generating explanation for '{newspaper.get('Title', 'N/A')}'..."):
                                    explanation = generate_recommendation_explanation(newspaper, user_info_for_explanation, st.session_state['active_tags_for_filter'], client_ai)
                                    st.info(explanation)
                                st.write("---")
                        else:
                            st.info("No newspapers/articles found for the selected tags.")
                    else:
                        st.info("No content found matching the active tags. Try adjusting your tags or searching for more.")
                else:
                    st.info("Select tags above to get reading recommendations.")

            st.subheader("Generate Activity Suggestions")
            recommended_titles = [item.get('Title', '') for item in st.session_state['recommended_books_current_session']] + \
                                [item.get('Title', '') for item in st.session_state['recommended_newspapers_current_session']]

            activity_type = st.radio(
                "Choose Activity Type:",
                ("General Activities", "Location-Based Activities"),
                key="activity_type_radio"
            )

            if st.button(f"Generate {activity_type}"):
                with st.spinner(f"Generating {activity_type.lower()}..."):
                    st.session_state['recommended_activities_current_session'] = []
                    st.session_state['activity_guides_for_pdf'] = [] # Reset for new generation

                    if activity_type == "General Activities":
                        activities = generate_activities(
                            client_ai,
                            st.session_state['active_tags_for_filter'],
                            recommended_titles
                        )
                    else: # Location-Based Activities
                        activities = generate_location_based_activities(
                            client_ai,
                            st.session_state['current_user_city'],
                            st.session_state['current_user_state'],
                            st.session_state['current_user_hobbies'],
                            st.session_state['current_user_decade']
                        )

                    st.session_state['recommended_activities_current_session'] = activities

                    if st.session_state['recommended_activities_current_session']:
                        st.subheader("Suggested Activities:")
                        for i, activity_title in enumerate(st.session_state['recommended_activities_current_session']):
                            with st.expander(f"✨ {activity_title}"):
                                with st.spinner(f"Generating guide for '{activity_title}'..."):
                                    guide = generate_activity_guide(activity_title, client_ai)
                                    st.markdown(guide)
                                    st.session_state['activity_guides_for_pdf'].append({'activity': activity_title, 'guide': guide})
                        st.info("Click on each activity to see a step-by-step guide and supply list.")
                    else:
                        st.info("No activities generated. Please check the profile information or try again.")

            if st.session_state['recommended_activities_current_session']:
                st.subheader("Printable Summary")
                st.write("Generate a printable summary of the current session's recommendations and activity guides.")
                if st.button("Show Printable Summary"):
                    st.session_state['show_printable_summary'] = True
                    user_info_for_summary = {
                        "name": st.session_state['current_user_name'],
                        "jobs": st.session_state['current_user_jobs'],
                        "life_experiences": st.session_state['current_user_life_experiences'],
                        "hobbies": st.session_state['current_user_hobbies'],
                        "decade": st.session_state['current_user_decade'],
                        "college_chapter": st.session_state['current_user_college_chapter'],
                        "city": st.session_state['current_user_city'],
                        "state": st.session_state['current_user_state']
                    }
                    summary_text = get_printable_summary(
                        user_info_for_summary,
                        st.session_state['active_tags_for_filter'],
                        st.session_state['recommended_books_current_session'],
                        st.session_state['recommended_newspapers_current_session'],
                        st.session_state['activity_guides_for_pdf'], # Pass activities with guides
                        st.session_state['logged_in_username']
                    )
                    st.session_state['printable_summary_text'] = summary_text
                    st.text_area("Session Summary", value=st.session_state['printable_summary_text'], height=400, key="summary_text_area")
                    create_pdf_from_summary(st.session_state['printable_summary_text'])
                
                if st.session_state['show_printable_summary'] and 'printable_summary_text' in st.session_state:
                     st.text_area("Session Summary", value=st.session_state['printable_summary_text'], height=400, key="summary_text_area_after_gen")
                     create_pdf_from_summary(st.session_state['printable_summary_text'])


        else:
            st.info("Enter a 'Pair's Name' above to start generating personalized tags and recommendations.")

    # --- Session Notes Page ---
    elif st.session_state['current_page'] == 'session_notes':
        st.header(f"✍️ Session Notes for {st.session_state['current_user_name']}")
        if st.session_state['current_user_name']:
            st.date_input("Session Date", value=st.session_state['session_date'], key="session_date_input")
            st.session_state['session_mood'] = st.selectbox(
                "Pair's Mood during session:",
                ("Very Happy 😄", "Happy 😊", "Neutral 😐", "Sad 😞", "Very Sad 😭"),
                index=("Very Happy 😄", "Happy 😊", "Neutral 😐", "Sad 😞", "Very Sad 😭").index(st.session_state['session_mood'])
            )
            st.session_state['session_engagement'] = st.selectbox(
                "Pair's Engagement level:",
                ("Very Engaged ⭐⭐⭐", "Moderately Engaged ⭐⭐", "Slightly Engaged ⭐", "Not Engaged 🚫"),
                index=("Very Engaged ⭐⭐⭐", "Moderately Engaged ⭐⭐", "Slightly Engaged ⭐", "Not Engaged 🚫").index(st.session_state['session_engagement'])
            )
            st.session_state['session_takeaways'] = st.text_area("Key Takeaways/Observations:", value=st.session_state['session_takeaways'])

            st.markdown("---")
            st.subheader("Recommended Materials from this Session:")
            recommended_materials_summary = []

            if st.session_state['recommended_books_current_session']:
                st.markdown("##### Books:")
                for book in st.session_state['recommended_books_current_session']:
                    st.markdown(f"- **{book.get('Title', 'N/A')}** ({book.get('Type', 'N/A')})")
                    recommended_materials_summary.append({"Type": "Book", "Title": book.get('Title', 'N/A'), "URL": book.get('URL', 'N/A')})
            if st.session_state['recommended_newspapers_current_session']:
                st.markdown("##### Newspapers/Articles:")
                for newspaper in st.session_state['recommended_newspapers_current_session']:
                    st.markdown(f"- **{newspaper.get('Title', 'N/A')}** ({newspaper.get('Type', 'N/A')})")
                    recommended_materials_summary.append({"Type": "Newspaper", "Title": newspaper.get('Title', 'N/A'), "URL": newspaper.get('URL', 'N/A')})
            if st.session_state['recommended_activities_current_session']:
                st.markdown("##### Activities:")
                for activity in st.session_state['recommended_activities_current_session']:
                    st.markdown(f"- **{activity}**")
                    # Store activity title only, guide will be regenerated if needed from PDF summary
                    recommended_materials_summary.append({"Type": "Activity", "Title": activity})
            
            if not recommended_materials_summary:
                st.info("No materials were recommended in this session. Generate some on the 'Pair Profile' page.")

            if st.button("Save Session Notes"):
                if st.session_state['current_user_name'] and st.session_state['session_takeaways']:
                    save_session_notes_to_gsheet(
                        st.session_state['current_user_name'],
                        st.session_state['session_date_input'], # Use the value from the date_input widget
                        st.session_state['session_mood'],
                        st.session_state['session_engagement'],
                        st.session_state['session_takeaways'],
                        json.dumps(recommended_materials_summary), # Save as JSON string
                        st.session_state['logged_in_username']
                    )
                else:
                    st.warning("Please enter Pair's Name and Key Takeaways before saving.")
        else:
            st.info("Select a 'Pair's Name' on the Dashboard or 'Pair Profile' page to start taking session notes.")

    # --- Session History Page ---
    elif st.session_state['current_page'] == 'session_history':
        st.header(f"📜 Session History for {st.session_state['current_user_name']}:")
        if st.session_state['current_user_name']:
            # Load session logs for the current pair and logged-in volunteer
            session_history_df = load_session_logs(st.session_state['current_user_name'], st.session_state['logged_in_username'])

            if not session_history_df.empty:
                # Display history in reverse chronological order
                for index, row in session_history_df.iterrows():
                    st.markdown(f"**Session Date:** {row['Session Date']}")
                    st.markdown(f"**Mood:** {row['Mood']}")
                    st.markdown(f"**Engagement:** {row['Engagement']}")
                    st.markdown(f"**Takeaways:** {row['Takeaways']}")
                    
                    # Parse and display recommended materials
                    recommended_materials_raw = row.get('Recommended Materials')
                    if recommended_materials_raw:
                        try:
                            recs = json.loads(recommended_materials_raw)
                            if recs:
                                st.markdown("##### Recommended Materials for this Session:")
                                for rec_item in recs:
                                    item_type = rec_item.get('Type', 'N/A')
                                    item_title = rec_item.get('Title', 'N/A')
                                    item_url = rec_item.get('URL', '#')
                                    if item_type in ["Book", "Newspaper"] and item_url != 'N/A':
                                        st.markdown(f"- {item_type}: [{item_title}]({item_url})")
                                    else:
                                        st.markdown(f"- {item_type}: {item_title}")
                        except json.JSONDecodeError:
                            st.markdown("_Error loading recommended materials. Data format may be incorrect._")
                    st.markdown("---") # Add a separator between history items
            else:
                st.info(f"No past session notes found for {st.session_state['current_user_name']} logged by {st.session_state['logged_in_username']}. Save a session to see history!")
        else:
            st.info("Enter a 'Pair's Name' above to view their session history.")

    elif st.session_state['current_page'] == 'decade_summary':
        # Removed the custom anchor tag: st.markdown('<a name=\"decade_summary\"></a>', unsafe_allow_html=True)
        st.header(f"🕰️ A Glimpse into the {st.session_state['current_user_decade']}:")
        if st.session_state['current_user_decade']:
            with st.spinner(f"Generating context for the {st.session_state['current_user_decade']}..."):
                historical_context = generate_historical_context(st.session_state['current_user_decade'], client_ai)
                st.info(historical_context)
        else:
            st.info("Please set a 'Favorite Decade' in the Pair Profile to view a historical summary.")
