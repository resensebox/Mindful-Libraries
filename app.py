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

    /* Main content wrapper to create the "floating rectangle" effect */
    .main-content-wrapper {
        background-color: #ffffff; /* White background for the main content area */
        border-radius: 16px; /* More rounded corners for the main container */
        box-shadow: 0 8px 24px rgba(0,0,0,0.15); /* Stronger, more noticeable shadow */
        padding: 2rem; /* Increased padding inside the main content area */
        margin: 1.5rem auto; /* Adjusted top/bottom margin, and auto left/right for centering */
        max-width: 900px; /* Limit width for better floating effect */
        min-height: auto; /* Allows content area to shrink when content is sparse */
        box-sizing: border-box; /* Include padding in the element's total width and height */
    }

    /* App-like Header (remains at the top of the main content area) */
    /* Targeting the header container in Streamlit and adjusting its appearance */
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
        margin-top: 1rem; /* Reduced top margin */
        margin-bottom: 1.5rem; /* Slightly reduced bottom margin */
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
        background-color: #007bff; /* Blue background for active button */
        color: white; /* White text for active button */
        box-shadow: 0 4px 8px rgba(0,0,0,0.2); /* More pronounced shadow */
    }

    /* Content Cards */
    .content-card {
        background-color: #ffffff;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08); /* More pronounced shadow */
        padding: 1.5rem;
        margin-bottom: 2rem; /* Space between cards */
        display: flex;
        flex-direction: column; /* Stack elements inside card */
        transition: transform 0.2s ease;
    }
    .content-card:hover {
        transform: translateY(-5px); /* Lift effect on hover */
    }

    .content-card-image-col {
        display: flex;
        justify-content: center;
        align-items: center;
        padding-right: 1.5rem; /* Space between image and text */
    }

    /* Specific image styling within cards */
    .content-card img {
        border-radius: 8px;
        width: 100%; /* Make image responsive within its column */
        height: auto;
        max-width: 180px; /* Max width for images */
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    }

    /* Session History Items */
    .session-history-item {
        background-color: #ffffff;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06); /* Lighter shadow for history items */
        padding: 1.2rem;
        margin-bottom: 1.5rem; /* Space between history items */
        border-left: 5px solid #4CAF50; /* Accent border */
    }

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
                        'college_chapter': record.get('College Chapter', '') # Load new field
                    }
    except gspread.exceptions.WorksheetNotFound:
        st.warning("The 'Pairs' worksheet was not found. Please create a sheet named 'Pairs' with 'Pair Name', 'Jobs', 'Life Experiences', 'Hobbies', 'Decade', 'College Chapter', and 'Volunteer Username' columns.")
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

def save_pair_details(volunteer_username, pair_name, jobs, life_experiences, hobbies, decade, college_chapter):
    global PAIRS_DATA # Declare global at the very beginning of the function
    """Saves or updates pair details in the 'Pairs' Google Sheet."""
    try:
        sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXJRXcfmxjoj5s')
        pairs_ws = sheet.worksheet('Pairs')

        # Add 'College Chapter' to expected headers
        expected_headers = ['Pair Name', 'Jobs', 'Life Experiences', 'Hobbies', 'Decade', 'College Chapter', 'Volunteer Username']
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
                elif h == 'College Chapter': update_values[col_map[h]] = college_chapter # Save new field
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
    """Generates activity suggestions based on tags and recommended titles."""
    if not active_tags and not recommended_titles:
        return ["No specific tags or recommended titles to suggest activities for. Try generating personalized tags first!"]

    titles_str = ", ".join(recommended_titles) if recommended_titles else "No specific reading materials recommended yet."

    prompt = f"""
    You are a helpful assistant for a student volunteer working with an individual living with dementia.
    Given the following key interests (tags) and recommended reading materials, suggest 3-5 gentle and engaging activities that a student volunteer can do with their pair.
    Always include "Reading the recommended books/newspapers together and discussing them" as one of the suggestions.
    Focus on activities that can spark positive memories, facilitate conversation, and provide calming engagement, suitable for individuals with dementia.

    Key Interests (Tags): {', '.join(active_tags)}
    Recommended Reading Titles: {titles_str}

    Suggest activities in a numbered list format. Each activity should be a short, actionable sentence.
    """
    try:
        response = _ai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip().split('\n')
    except Exception as e:
        return [f"Could not generate activity suggestions at this time. Error: {e}"]

def get_printable_summary(user_info, tags, books, newspapers, activities, volunteer_username):
    """Generates a formatted string summary for printing."""
    summary = f"--- Session Plan Summary for {user_info['name'] if user_info['name'] else 'Your Pair'} ---\n\n"
    summary += f"Date: {datetime.now().strftime('%Y-%m-%d')}\n"
    summary += f"Volunteer: {volunteer_username}\n" # Add volunteer username to summary
    summary += f"User Profile:\n"
    summary += f"  Job: {user_info['jobs'] if user_info['jobs'] else 'N/A'}\n"
    summary += f"  Life Experiences: {user_info['life_experiences'] if user_info['life_experiences'] else 'N/A'}\n"
    summary += f"  Hobbies: {user_info['hobbies'] if user_info['hobbies'] else 'N/A'}\n"
    summary += f"  Favorite Decade: {user_info['decade'] if user_info['decade'] else 'N/A'}\n"
    summary += f"  College Chapter: {user_info['college_chapter'] if user_info['college_chapter'] else 'N/A'}\n\n"


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

    summary += "Suggested Activities:\n"
    for activity in activities:
        summary += f"{activity}\n"
    
    summary += "\n--- End of Summary ---"
    return summary

def get_image_url(item):
    """Determines the best image URL for an item."""
    img_url = None
    if item.get('Image', '').startswith("http"):
        img_url = item['Image']
    elif 'URL' in item and "amazon." in item['URL'] and "/dp/" in item['URL']:
        # Safely extract ASIN if URL is from Amazon and contains '/dp/'
        parts_dp = item['URL'].split('/dp/')
        if len(parts_dp) > 1:
            remaining_url = parts_dp[1]
            parts_slash = remaining_url.split('/')
            if len(parts_slash) > 0:
                asin_with_params = parts_slash[0]
                asin = asin_with_params.split('?')[0]
                img_url = f"https://images-na.ssl-images-amazon.com/images/P/{asin}.01._SL250_.jpg"
    
    if not img_url:
        item_type = item.get('Type', '').lower()
        if item_type == 'newspaper':
            img_url = "https://placehold.co/180x250/007bff/ffffff?text=Newspaper"
        else:
            img_url = f"https://placehold.co/180x250/cccccc/333333?text=No+Image"
    return img_url

# --- Streamlit UI ---
# Custom header area with logo and logout button
st.markdown('<div class="st-emotion-cache-vk3357 e1nzilvr1">', unsafe_allow_html=True)
st.image("https://i.postimg.cc/0yVG4bhN/mindfullibrarieswhite-01.png", width=180) # Adjust width as needed
if st.session_state['is_authenticated']:
    if st.button("Log Out"):
        st.session_state['is_authenticated'] = False
        st.session_state['logged_in_username'] = ""
        # Clear all pair-related session state on logout
        st.session_state['current_user_name'] = ""
        st.session_state['current_user_jobs'] = ""
        st.session_state['current_user_life_experiences'] = ""
        st.session_state['current_user_hobbies'] = ""
        st.session_state['current_user_decade'] = ""
        st.session_state['current_user_college_chapter'] = ""
        st.session_state['selected_tags'] = []
        st.session_state['active_tags_for_filter'] = []
        st.session_state['tag_checkbox_states'] = {}
        st.session_state['session_date'] = date.today()
        st.session_state['session_mood'] = "Neutral 😐"
        st.session_state['session_engagement'] = "Moderately Engaged ⭐⭐"
        st.session_state['session_takeaways'] = ""
        st.session_state['recommended_books_current_session'] = []
        st.session_state['recommended_newspapers_current_session'] = []
        st.session_state['show_printable_summary'] = False
        PAIRS_DATA = {} # Clear global PAIRS_DATA on logout
        st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# Main title that replaces Streamlit's default h1
st.markdown("<h1 style='text-align: center; color: #333333; margin-top: 1rem; margin-bottom: 1.5rem; font-size: 2.5em; font-weight: 700; letter-spacing: -0.02em;'>Discover Your Next Nostalgic Read!</h1>", unsafe_allow_html=True)


# --- Login / Register Section ---
if not st.session_state['is_authenticated']:
    st.info("Please log in or register to use the Mindful Libraries app.")

    # Toggles between login and registration forms
    login_tab, register_tab = st.tabs(["Log In", "Register"])

    with login_tab:
        with st.form("login_form"):
            username = st.text_input("Username", key="login_username_input")
            password = st.text_input("Password", type="password", key="login_password_input")
            login_button = st.form_submit_button("Log In")

            if login_button:
                if username in USERS and USERS[username] == password:
                    st.session_state['is_authenticated'] = True
                    st.session_state['logged_in_username'] = username
                    st.success(f"Welcome back, {username}!")
                    # Reload pairs specific to this user after successful login
                    PAIRS_DATA = load_pairs(st.session_state['logged_in_username'])
                    # Clear pair-specific data for direct input
                    st.session_state['current_user_name'] = ""
                    st.session_state['current_user_jobs'] = ""
                    st.session_state['current_user_life_experiences'] = ""
                    st.session_state['current_user_hobbies'] = ""
                    st.session_state['current_user_decade'] = ""
                    st.session_state['current_user_college_chapter'] = ""
                    st.rerun()
                else:
                    st.error("Invalid username or password")
    
    with register_tab:
        with st.form("register_form"):
            new_username = st.text_input("Choose a Username", key="register_username_input")
            new_password = st.text_input("Create a Password", type="password", key="register_password_input")
            confirm_password = st.text_input("Confirm Password", type="password", key="confirm_password_input")
            register_button = st.form_submit_button("Register Account")

            if register_button:
                if not new_username:
                    st.error("Username cannot be empty.")
                elif new_username in USERS:
                    st.error("Username already exists. Please choose a different one.")
                elif not new_password:
                    st.error("Password cannot be empty.")
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    if save_new_user(new_username, new_password):
                        st.session_state['is_authenticated'] = True
                        st.session_state['logged_in_username'] = new_username
                        PAIRS_DATA = {} # Update global PAIRS_DATA for new user (empty initially)
                        # Clear all pair-related session state on new registration for direct input
                        st.session_state['current_user_name'] = ""
                        st.session_state['current_user_jobs'] = ""
                        st.session_state['current_user_life_experiences'] = ""
                        st.session_state['current_user_hobbies'] = ""
                        st.session_state['current_user_decade'] = ""
                        st.session_state['current_user_college_chapter'] = ""
                        st.rerun()

# --- Main App Content (visible only if authenticated) ---
if st.session_state['is_authenticated']:
    # Define user_info globally within the authenticated block
    user_info = {
        'name': st.session_state['current_user_name'],
        'jobs': st.session_state['current_user_jobs'],
        'life_experiences': st.session_state['current_user_life_experiences'],
        'hobbies': st.session_state['current_user_hobbies'],
        'decade': st.session_state['current_user_decade'],
        'college_chapter': st.session_state['current_user_college_chapter']
    }

    # Sidebar for navigation
    with st.sidebar:
        st.markdown(f"**Welcome, {st.session_state['logged_in_username']}!**")
        st.markdown("---")
        st.subheader("App Navigation")

        # Define page options and their corresponding session state values
        page_options = {
            "Dashboard": "dashboard",
            "Search Content": "search",
            "My Recommendations": "recommendations",
            "Activities": "activities",
            "Related Materials": "related_books",
            "Session Notes": "session_notes",
            "Session History": "session_history",
            "Decade Summary": "decade_summary",
        }

        # Create sidebar buttons
        for label, page_key in page_options.items():
            disabled_state = False
            if label == "Decade Summary" and not st.session_state['current_user_decade']:
                disabled_state = True # Disable if no decade is set

            # Check if the current button is the active page
            is_active = (st.session_state['current_page'] == page_key)
            
            # Apply custom class for active state
            # Note: Streamlit's internal rendering applies classes dynamically.
            # This CSS injection is a common workaround to ensure active state styling is applied.
            active_style = ""
            if is_active:
                active_style = """
                    <style>
                        /* This targets the specific button that Streamlit marks as active */
                        .stSidebar button[data-testid="stSidebarNav"] > div > div > button[kind="secondary"][aria-selected="true"] {
                            background-color: #007bff !important;
                            color: white !important;
                            box-shadow: 0 4px 8px rgba(0,0,0,0.2) !important;
                        }
                    </style>
                """
                st.markdown(active_style, unsafe_allow_html=True)


            if st.button(label, key=f"sidebar_btn_{page_key}", disabled=disabled_state, help=f"Go to {label}"):
                st.session_state['current_page'] = page_key
                st.rerun() # Rerun to switch page


    # --- Main Content Area Wrapper ---
    # This div will act as the "floating rectangle"
    st.markdown('<div class="main-content-wrapper">', unsafe_allow_html=True)

    # Content Area based on selected page
    if st.session_state['current_page'] == 'dashboard':
        st.markdown("""
            Welcome to Mindful Libraries! This tool helps student volunteers curate personalized reading materials to engage individuals living with dementia.
            Answer a few simple questions about your "pair" to get tailored suggestions that can spark positive memories and facilitate meaningful interactions.
            Let's find the perfect book or newspaper to transport them back in time and create a shared experience!
        """)

        st.markdown("---")
        st.header("👥 Manage Your Pair's Profile:")

        # Callback function to load existing pair data when pair name input changes
        def load_existing_pair_data_callback():
            typed_pair_name = st.session_state.get('pair_name_input_external', '').strip()
            if typed_pair_name and typed_pair_name in PAIRS_DATA:
                pair_info = PAIRS_DATA[typed_pair_name]
                st.session_state['current_user_name'] = typed_pair_name
                st.session_state['current_user_jobs'] = pair_info.get('jobs', '')
                st.session_state['current_user_life_experiences'] = pair_info.get('life_experiences', '')
                st.session_state['current_user_hobbies'] = pair_info.get('hobbies', '')
                st.session_state['current_user_decade'] = pair_info.get('decade', '')
                st.session_state['current_user_college_chapter'] = pair_info.get('college_chapter', '')
            elif typed_pair_name: # If a new name is typed, clear other fields
                if st.session_state['current_user_name'] != typed_pair_name: # Only clear if name actually changed to a new one
                    st.session_state['current_user_jobs'] = ""
                    st.session_state['current_user_life_experiences'] = ""
                    st.session_state['current_user_hobbies'] = ""
                    st.session_state['current_user_decade'] = ""
                    st.session_state['current_user_college_chapter'] = ""
                st.session_state['current_user_name'] = typed_pair_name # Update current_user_name with the typed name
            else: # Clear all if input is empty
                st.session_state['current_user_name'] = ""
                st.session_state['current_user_jobs'] = ""
                st.session_state['current_user_life_experiences'] = ""
                st.session_state['current_user_hobbies'] = ""
                st.session_state['current_user_decade'] = ""
                st.session_state['current_user_college_chapter'] = ""

        # External text input for Pair's Name
        pair_name_input_external = st.text_input(
            "Enter Pair's Name (e.g., 'Grandma Smith', 'John Doe')",
            value=st.session_state['current_user_name'],
            key="pair_name_input_external",
            on_change=load_existing_pair_data_callback, # Callback is now allowed here
            help="Type a name to load existing details or create a new profile."
        )
        # Ensure current_user_name always reflects the external input
        st.session_state['current_user_name'] = pair_name_input_external


        # Display the pair details input form within an expander that is always expanded
        with st.expander("✨ Pair Profile Details", expanded=True):
            st.subheader("Edit Pair Profile")
            st.info("Complete the details below for the active pair. Click 'Save Pair Details' to update.")

            with st.form("pair_details_form"):
                # Use current_user_name (from external input) as initial value, and update on form submission
                jobs_input = st.text_input("What did they used to do for a living? (e.g., Teacher, Engineer, Homemaker)", value=st.session_state['current_user_jobs'], key="form_pair_jobs_input")
                life_experiences_input = st.text_input("What are some significant life experiences or memorable events they often talk about? (e.g., specific projects at work, historical events they lived through, family milestones)", value=st.session_state['current_user_life_experiences'], key="form_pair_life_experiences_input")
                hobbies_input = st.text_input("What are their hobbies or favorite activities? (e.g., Gardening, Reading, Music, Sports)", value=st.session_state['current_user_hobbies'], key="form_pair_hobbies_input")
                decade_input = st.text_input("What is their favorite decade or era? (e.g., 1950s, 1970s, Victorian era)", value=st.session_state['current_user_decade'], key="form_pair_decade_input")
                college_chapter_input = st.text_input("College Chapter (e.g., Alpha Beta Gamma, 1965-1969)", value=st.session_state['current_user_college_chapter'], key="form_pair_college_chapter_input")


                save_pair_button = st.form_submit_button("Save Pair Details")

                if save_pair_button:
                    if not st.session_state['current_user_name']: # Check the external input's value
                        st.error("Pair's Name is required. Please enter a name in the field above the 'Pair Profile Details' section.")
                    else:
                        if save_pair_details(
                            st.session_state['logged_in_username'],
                            st.session_state['current_user_name'], # Use the value from the external input
                            jobs_input,
                            life_experiences_input,
                            hobbies_input,
                            decade_input,
                            college_chapter_input
                        ):
                            # Update session state with the new values from the form to ensure consistency
                            st.session_state['current_user_jobs'] = jobs_input
                            st.session_state['current_user_life_experiences'] = life_experiences_input
                            st.session_state['current_user_hobbies'] = hobbies_input
                            st.session_state['current_user_decade'] = decade_input
                            st.session_state['current_user_college_chapter'] = college_chapter_input
                            st.rerun() # Rerun to refresh UI with saved data

        # Display the current active pair's details outside the form
        if st.session_state['current_user_name']:
            st.markdown(f"---")
            st.subheader(f"Current Active Pair: **{st.session_state['current_user_name']}**")
            st.markdown(f"Job: {st.session_state['current_user_jobs'] if st.session_state['current_user_jobs'] else 'N/A'}")
            st.markdown(f"Life Experiences: {st.session_state['current_user_life_experiences'] if st.session_state['current_user_life_experiences'] else 'N/A'}")
            st.markdown(f"Hobbies: {st.session_state['current_user_hobbies'] if st.session_state['current_user_hobbies'] else 'N/A'}")
            st.markdown(f"Favorite Decade: {st.session_state['current_user_decade'] if st.session_state['current_user_decade'] else 'N/A'}")
            st.markdown(f"College Chapter: {st.session_state['current_user_college_chapter'] if st.session_state['current_user_college_chapter'] else 'N/A'}")
            st.markdown("---")

            if st.button("Generate Personalized Tags & Recommendations", key="generate_main_btn_dashboard"):
                if not (st.session_state['current_user_jobs'] or st.session_state['current_user_hobbies'] or st.session_state['current_user_decade'] or st.session_state['current_user_life_experiences'] or st.session_state['current_user_college_chapter']):
                    st.warning("Please enter at least one detail about your pair (job, life experiences, hobbies, favorite decade, or college chapter) to generate tags.")
                    st.stop()

                if st.session_state['current_user_hobbies']:
                    hobby_list = [h.strip() for h in st.session_state['current_user_hobbies'].split(',') if h.strip()]
                    if len(hobby_list) < 4:
                        st.warning("Please enter at least 4 hobbies, separated by commas.")
                        st.stop()

                with st.spinner("Our expert librarian AI is thinking deeply..."):
                    if not content_df.empty and 'tags' in content_df.columns:
                        content_tags_list = sorted(list(set(tag for tags_set in content_df['tags'] for tag in tags_set)))
                        prompt = f"""
                            You are an expert librarian and therapist assistant. Your job is to recommend 20 **extremely specific and granular** tags for reading content,
                            using **only** the available tags list.
                            These tags will help a student volunteer find appropriate materials for an individual living with dementia.
                            Instead of vague tags like "wellness" or "spirituality", aim for tags like "mindfulness meditation guides", "cognitive behavioral therapy", "historical fiction - roman empire", "sci-fi - cyberpunk", "vintage fashion", "classic Hollywood", "WWII memoirs", "1950s rock and roll".
                            Make sure you really analyze each aspect of what they do, their hobbies, their favorite decade, and significant life experiences, and come up with specific tags that **exactly** match the list of tags in the google sheet.
                            The goal is to spark positive memories and facilitate engagement for the individual with dementia.

                            Available tags:
                            {", ".join(content_tags_list)}

                            Person's background:
                            Name: {st.session_state['current_user_name'] if st.session_state['current_user_name'] else 'Not provided'}
                            Job: {st.session_state['current_user_jobs'] if st.session_state['current_user_jobs'] else 'Not provided'}
                            Hobbies: {st.session_state['current_user_hobbies'] if st.session_state['current_user_hobbies'] else 'Not provided'}
                            Favorite Decade: {st.session_state['current_user_decade'] if st.session_state['current_user_decade'] else 'Not provided'}
                            Significant Life Experiences: {st.session_state['current_user_life_experiences'] if st.session_state['current_user_life_experiences'] else 'Not provided'}
                            College Chapter: {st.session_state['current_user_college_chapter'] if st.session_state['current_user_college_chapter'] else 'Not provided'}

                            Only return 20 comma-separated tags from the list above. Do not include any additional text or formatting.
                            Please ensure the tags are varied and cover different aspects of their life to maximize recommendation diversity, aiming to provide as close to 20 unique tags as possible.
                        """
                        try:
                            response = client_ai.chat.completions.create(
                                model="gpt-3.5-turbo",
                                messages=[{"role": "user", "content": prompt}]
                            )
                            topic_output = response.choices[0].message.content.strip()
                            st.session_state['selected_tags'] = sorted(list(set([t.strip().lower() for t in topic_output.split(',') if t.strip()])))

                            st.session_state['tag_checkbox_states'] = {tag: True for tag in st.session_state['selected_tags']}
                            st.session_state['active_tags_for_filter'] = list(st.session_state['selected_tags'])
                            st.success("✨ Tags generated!")
                            save_user_input(st.session_state['current_user_name'], st.session_state['current_user_jobs'], st.session_state['current_user_hobbies'], st.session_state['current_user_decade'], st.session_state['selected_tags'], st.session_state['logged_in_username'], st.session_state['current_user_college_chapter'])
                        except Exception as e:
                            st.error(f"Failed to generate tags using OpenAI. Please check your API key and try again. Error: {e}")
                    else:
                        st.warning("Cannot generate tags as content database is empty or 'tags' column is missing.")

            if st.session_state['selected_tags']:
                st.subheader("Your Personalized Tags:")
                st.markdown("Here are the tags our AI suggests. **You can uncheck any tags you don't feel are relevant** for your pair.")

                for tag in st.session_state['selected_tags']:
                    if tag not in st.session_state['tag_checkbox_states']:
                        st.session_state['tag_checkbox_states'][tag] = True

                current_active_tags = []
                cols = st.columns(min(len(st.session_state['selected_tags']), 5))
                for i, tag in enumerate(st.session_state['selected_tags']):
                    with cols[i % 5]:
                        checked_status = st.checkbox(
                            tag.capitalize(),
                            value=st.session_state['tag_checkbox_states'].get(tag, True),
                            key=f"interactive_tag_checkbox_{tag}"
                        )
                        st.session_state['tag_checkbox_states'][tag] = checked_status

                        if checked_status:
                            current_active_tags.append(tag)

                st.session_state['active_tags_for_filter'] = current_active_tags

                if st.button("Apply Tag Filters & Update Recommendations", key="apply_filter_btn_dashboard"):
                    st.success("Recommendations updated based on your selected tags!")

                st.markdown("Now, select 'My Recommendations' from the sidebar to view your tailored recommendations!")

    elif st.session_state['current_page'] == 'search':
        st.markdown('<a name="search_section"></a>', unsafe_allow_html=True)
        st.header("🔍 Search for a Specific Topic:")
        search_term = st.text_input("Enter a keyword (e.g., 'adventure', 'history', 'science fiction', 'actor')", key="search_input")

        if search_term:
            st.markdown(f"### Results for '{search_term}'")
            generated_search_tags = set()
            with st.spinner(f"Expanding search for '{search_term}' with AI..."):
                content_tags_list = sorted(list(set(tag for tags_set in content_df['tags'] for tag in tags_set)))
                generated_search_tags = get_ai_expanded_search_tags(search_term, content_tags_list, client_ai)

                if generated_search_tags:
                    st.info(f"AI-expanded your search to include tags: **{', '.join(generated_search_tags)}**")
                else:
                    st.info("AI did not find specific tags for your search. Searching for direct keyword matches.")

            results = []
            search_term_lower = search_term.lower()

            for item in content_df.to_dict('records'):
                item_title_lower = item.get('Title', '').lower()
                item_summary_lower = item.get('Summary', '').lower()
                item_tags_set = item.get('tags', set())

                direct_text_match = search_term_lower in item_title_lower or \
                                    search_term_lower in item_summary_lower

                direct_tag_match = search_term_lower in item_tags_set

                ai_tag_found = False
                for ai_tag in generated_search_tags:
                    if ai_tag in item_tags_set:
                        ai_tag_found = True
                        break

                if direct_text_match or direct_tag_match or ai_tag_found:
                    results.append(item)

            if results:
                for item in results[:5]:
                    # Only render content-card if there's meaningful content
                    if item.get('Title') or item.get('Summary') or item.get('Image') or item.get('URL'):
                        st.markdown('<div class="content-card">', unsafe_allow_html=True) # Start card
                        cols = st.columns([1, 2])
                        with cols[0]:
                            img_url = get_image_url(item) # Use the new helper function
                            st.markdown('<div class="content-card-image-col">', unsafe_allow_html=True)
                            st.image(img_url, width=180) # Always display image using the determined URL
                            st.markdown('</div>', unsafe_allow_html=True) # End content-card-image-col

                        with cols[1]:
                            st.markdown(f"### {item.get('Title', 'N/A')} ({item.get('Type', 'N/A')})")
                            st.markdown(item.get('Summary', 'N/A'))
                            item_tags_display = item.get('tags', set())
                            if item_tags_display:
                                 st.markdown(f"_Tags: {', '.join(item_tags_display)}_")

                            if 'URL' in item and item['URL']:
                                st.markdown(f"<a class='buy-button' href='{item['URL']}' target='_blank'>Buy Now</a>", unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True) # End card
                if len(results) > 5:
                    st.info(f"Showing top 5 results. Found {len(results)} total matches for '{search_term}'.")
            else:
                st.info(f"No results found for '{search_term}' or its related tags. Try a different keyword or explore the personalized recommendations below.")

    elif st.session_state['current_page'] == 'recommendations':
        st.markdown('<a name="personalized_recommendations"></a>', unsafe_allow_html=True)
        st.header(f"📚 Personalized Recommendations for You!")

        if not st.session_state['active_tags_for_filter']:
            st.info("Please generate personalized tags on the Dashboard first to see recommendations.")
        else:
            feedback_tag_scores = load_feedback_tag_scores()
            books_candidates = []
            newspapers_candidates = []

            for item in content_df.itertuples(index=False):
                item_tags = getattr(item, 'tags', set())
                item_type = getattr(item, 'Type', '').lower()

                tag_matches = item_tags & set(st.session_state['active_tags_for_filter'])
                num_matches = len(tag_matches)
                tag_weight = sum(feedback_tag_scores.get(tag, 0) for tag in tag_matches)

                if item_type == 'newspaper' and num_matches >= 1 and tag_weight >= -2:
                    newspapers_candidates.append((num_matches, tag_weight, item._asdict()))
                elif item_type == 'book' and num_matches >= 2 and tag_weight >= 0:
                    books_candidates.append((num_matches, tag_weight, item._asdict()))

            books_candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
            newspapers_candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)

            books = [item_dict for _, _, item_dict in books_candidates[:3]]
            newspapers = [item_dict for _, _, item_dict in newspapers_candidates[:3]]
            
            st.session_state['recommended_books_current_session'] = books
            st.session_state['recommended_newspapers_current_session'] = newspapers

            if books or newspapers:
                for item in books + newspapers:
                    # Only render content-card if there's meaningful content
                    if item.get('Title') or item.get('Summary') or item.get('Image') or item.get('URL'):
                        st.markdown('<div class="content-card">', unsafe_allow_html=True) # Start card
                        cols = st.columns([1, 2])
                        with cols[0]:
                            img_url = get_image_url(item) # Use the new helper function
                            st.markdown('<div class="content-card-image-col">', unsafe_allow_html=True)
                            st.image(img_url, width=180) # Always display image using the determined URL
                            st.markdown('</div>', unsafe_allow_html=True) # End content-card-image-col

                        with cols[1]:
                            st.markdown(f"### {item.get('Title', 'N/A')} ({item.get('Type', 'N/A')})")
                            st.markdown(item.get('Summary', 'N/A'))
                            original_tag_matches = item.get('tags', set()) & set(st.session_state['active_tags_for_filter'])
                            if original_tag_matches:
                                 st.markdown(f"**Why this was recommended:** Matched tags — **{', '.join(original_tag_matches)}**")
                            else:
                                st.markdown("_No direct tag matches found for this recommendation._")

                            with st.expander("Why this recommendation is great for your pair:"):
                                with st.spinner("Generating personalized insights..."):
                                    explanation = generate_recommendation_explanation(item, user_info, st.session_state['active_tags_for_filter'], client_ai)
                                    st.markdown(explanation)

                            feedback_key = f"feedback_{item.get('Title', 'NoTitle')}_{item.get('Type', 'NoType')}"
                            feedback = st.radio(
                                f"Was this recommendation helpful?",
                                ["Select an option", "✅ Yes", "❌ No"],
                                index=0,
                                key=feedback_key
                            )

                            if feedback != "Select an option" and not st.session_state.get(f"feedback_submitted_{feedback_key}", False):
                                try:
                                    # Corrected Google Sheet URL for feedback
                                    sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXJRXcfmxjoj5s')
                                    feedback_ws = sheet.worksheet('Feedback')
                                    feedback_ws.append_row([
                                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        st.session_state['current_user_name'], # Use the current pair's name
                                        item.get('Title', 'N/A'),
                                        item.get('Type', 'N/A'),
                                        feedback,
                                        ", ".join(item.get('tags', set()))
                                    ])
                                    st.session_state[f"feedback_submitted_{feedback_key}"] = True
                                    st.success("✅ Feedback submitted! Thank you for helping us improve.")
                                except Exception as e:
                                    st.warning(f"⚠️ Failed to save feedback. Error: {e}")

                            if 'URL' in item and item['URL']:
                                st.markdown(f"<a class='buy-button' href='{item['URL']}' target='_blank'>Buy Now</a>", unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True) # End card
                if not (books or newspapers):
                    st.markdown("_No primary recommendations found based on your current tags. Please try adjusting your input or generating new tags._")
            else:
                st.markdown("_No primary recommendations found based on your current tags. Please try adjusting your input or generating new tags._")

    elif st.session_state['current_page'] == 'activities':
        st.markdown('<a name="activities_section"></a>', unsafe_allow_html=True)
        st.header("💡 Recommended Activities:")
        
        # user_info is now defined at a higher scope
        recommended_titles_for_activities = [item.get('Title', 'N/A') for item in st.session_state['recommended_books_current_session'] + st.session_state['recommended_newspapers_current_session']]

        with st.spinner("Generating activity suggestions..."):
            activities = generate_activities(client_ai, st.session_state['active_tags_for_filter'], recommended_titles_for_activities)
            for activity in activities:
                st.markdown(activity)
        
        st.markdown("---")
        if st.button("Prepare Printable Session Summary", key="printable_summary_btn_activities"):
            st.session_state['show_printable_summary'] = True

        if st.session_state['show_printable_summary']:
            st.subheader("📄 Printable Session Summary:")
            printable_summary_content = get_printable_summary(user_info, st.session_state['active_tags_for_filter'], st.session_state['recommended_books_current_session'], st.session_state['recommended_newspapers_current_session'], activities, st.session_state['logged_in_username'])
            st.text_area("Copy and Print Your Session Plan", value=printable_summary_content, height=300, key="printable_summary_text_activities")
            st.info("You can copy the text above and paste it into a document for printing.")
            st.session_state['show_printable_summary'] = False


    elif st.session_state['current_page'] == 'related_books':
        st.markdown('<a name="you_might_also_like"></a>', unsafe_allow_html=True)
        st.header("📖 You Might Also Like:") # Changed header text here
        
        # user_info is now defined at a higher scope
        feedback_tag_scores = load_feedback_tag_scores()
        
        primary_recommended_titles = {item.get('Title') for item in st.session_state['recommended_books_current_session'] + st.session_state['recommended_newspapers_current_session'] if item.get('Title')}
        
        related_books = []
        all_relevant_tags = set(st.session_state['active_tags_for_filter'])
        for item in st.session_state['recommended_books_current_session'] + st.session_state['recommended_newspapers_current_session']:
            all_relevant_tags.update(item.get('tags', set()))

        temp_related_books_candidates = []
        for item in content_df.to_dict('records'):
            if item.get('Title') not in primary_recommended_titles and item.get('Type', '').lower() == 'book':
                common_tags = set(item.get('tags', set())) & all_relevant_tags
                if len(common_tags) > 0:
                    temp_related_books_candidates.append((len(common_tags), item))

        temp_related_books_candidates.sort(key=lambda x: x[0], reverse=True)
        related_books = [book_dict for _, book_dict in temp_related_books_candidates][:10]


        if related_books:
            st.markdown("Based on your interests, here are a few more materials you might enjoy.") # Changed text here
            num_cols = min(5, len(related_books))
            cols = st.columns(num_cols)
            for i, book in enumerate(related_books):
                # Only render content-card if there's meaningful content
                if book.get('Title') or book.get('Summary') or book.get('Image') or book.get('URL'):
                    # Using a column for each related book to arrange them in a grid-like manner
                    with cols[i % num_cols]:
                        st.markdown('<div class="content-card" style="padding: 1rem; margin-bottom: 1rem; height: auto;">', unsafe_allow_html=True) # Smaller card for related books, auto height
                        img_url = get_image_url(book) # Use the new helper function
                        st.image(img_url, width=120) # Always display image using the determined URL
                        st.caption(book.get('Title', 'N/A'))

                        with st.expander("Why this recommendation is great for your pair:"):
                            with st.spinner("Generating personalized insights..."):
                                explanation = generate_recommendation_explanation(book, user_info, st.session_state['active_tags_for_filter'], client_ai)
                                st.markdown(explanation)

                        if 'URL' in book and book['URL']:
                            st.markdown(f"<a class='buy-button' href='{book['URL']}' target='_blank'>Buy Now</a>", unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True) # End content-card
        else:
            st.markdown("_No other related materials found with your current tags. Try generating new tags or searching for a specific topic!_") # Changed text here
            st.markdown("---")
            st.subheader("✨ Or, explore some popular titles:")
            st.markdown("Here are some widely appreciated books to get you started.")
            if not content_df.empty and 'Type' in content_df.columns:
                fallback_books_df = content_df[content_df['Type'].str.lower() == 'book']
                if not fallback_books_df.empty:
                    num_cols_fallback = st.columns(min(5, len(fallback_books_df)))
                    for i, book in enumerate(fallback_books_df.sample(min(5, len(fallback_books_df)), random_state=1).to_dict('records')):
                        # Only render content-card if there's meaningful content
                        if book.get('Title') or book.get('Summary') or book.get('Image') or book.get('URL'):
                            with num_cols_fallback[i % len(num_cols_fallback)]:
                                st.markdown('<div class="content-card" style="padding: 1rem; margin-bottom: 1rem; height: auto;">', unsafe_allow_html=True) # Smaller card for fallback books, auto height
                                img_url = get_image_url(book) # Use the new helper function
                                st.image(img_url, width=120) # Always display image using the determined URL
                                st.caption(book.get('Title', 'N/A'))
                                if 'URL' in book and book['URL']:
                                    st.markdown(f"<a class='buy-button' href='{book['URL']}' target='_blank'>Buy Now</a>", unsafe_allow_html=True)
                                st.markdown('</div>', unsafe_allow_html=True) # End content-card
                else:
                    st.markdown("_No books available in the database to recommend._")
            else:
                st.markdown("_No books available in the database to recommend._")

    elif st.session_state['current_page'] == 'session_notes':
        st.markdown('<a name="session_notes_section"></a>', unsafe_allow_html=True)
        st.header("📝 Record Your Session Notes:")

        notes_col1, notes_col2, notes_col3 = st.columns([1, 1, 1])
        with notes_col1:
            session_date = st.date_input("Session Date", value=st.session_state['session_date'], key="session_date_input")
            st.session_state['session_date'] = session_date
        with notes_col2:
            session_mood = st.radio(
                "Pair's Overall Mood During Session:",
                ["Happy 😊", "Calm 😌", "Neutral 😐", "Agitated 😠", "Sad 😢"],
                index=["Happy 😊", "Calm 😌", "Neutral 😐", "Agitated 😠", "Sad 😢"].index(st.session_state['session_mood']),
                key="session_mood_input"
            )
            st.session_state['session_mood'] = session_mood
        with notes_col3:
            session_engagement = st.radio(
                "Engagement Level:",
                ["Highly Engaged ⭐⭐⭐", "Moderately Engaged ⭐⭐", "Minimally Engaged ⭐", "Not Engaged 🚫"],
                index=["Highly Engaged ⭐⭐⭐", "Moderately Engaged ⭐⭐", "Minimally Engaged ⭐", "Not Engaged 🚫"].index(st.session_state['session_engagement']),
                key="session_engagement_input"
            )
            st.session_state['session_engagement'] = session_engagement

        session_takeaways = st.text_area(
            "Key Takeaways & Observations (e.g., specific topics they responded well to, new memories recalled, challenges faced):",
            value=st.session_state['session_takeaways'],
            height=150,
            key="session_takeaways_input"
        )
        st.session_state['session_takeaways'] = session_takeaways

        if st.button("Save Session Notes", key="save_session_notes_btn"):
            if st.session_state['current_user_name']:
                # Extract only titles for logging in a list of strings
                recommended_book_titles = [book.get('Title', 'N/A') for book in st.session_state['recommended_books_current_session']]
                recommended_newspaper_titles = [newspaper.get('Title', 'N/A') for newspaper in st.session_state['recommended_newspapers_current_session']]
                
                # Combine all titles into a single list
                all_recommended_titles = recommended_book_titles + recommended_newspaper_titles
                recommended_materials_json = json.dumps(all_recommended_titles) # Now dumping a list of strings

                save_session_notes_to_gsheet(
                    st.session_state['current_user_name'], # Use the current pair's name
                    st.session_state['session_date'],
                    st.session_state['session_mood'],
                    st.session_state['session_engagement'],
                    st.session_state['session_takeaways'],
                    recommended_materials_json,
                    st.session_state['logged_in_username']
                )
                st.session_state['session_date'] = date.today()
                st.session_state['session_mood'] = "Neutral 😐"
                st.session_state['session_engagement'] = "Moderately Engaged ⭐⭐"
                st.session_state['session_takeaways'] = ""
                st.session_state['recommended_books_current_session'] = []
                st.session_state['recommended_newspapers_current_session'] = []
                st.rerun()
            else:
                st.warning("Please enter a 'Pair's Name' at the top to save session notes.")

    elif st.session_state['current_page'] == 'session_history':
        st.markdown('<a name="session_history_section"></a>', unsafe_allow_html=True)
        st.header("Past Session History:")

        if st.session_state['current_user_name'] and st.session_state['logged_in_username']:
            session_history_df = load_session_logs(st.session_state['current_user_name'], st.session_state['logged_in_username'])
            if not session_history_df.empty:
                for index, row in session_history_df.iterrows():
                    st.markdown('<div class="session-history-item">', unsafe_allow_html=True) # Start history item card
                    st.markdown(f"**Session Date:** {row['Session Date']}")
                    st.markdown(f"**Pair Name:** {row['Pair Name']}")
                    st.markdown(f"**Mood:** {row['Mood']}")
                    st.markdown(f"**Engagement:** {row['Engagement']}")
                    st.markdown(f"**Takeaways:** {row['Takeaways']}")
                    
                    if 'Recommended Materials' in row and row['Recommended Materials']:
                        try:
                            # When loading, parse the JSON string back into a list of titles
                            recs = json.loads(row['Recommended Materials'])
                            if recs:
                                st.markdown("**Recommended Materials for this Session:**")
                                # Display each title in the list
                                for rec_title in recs:
                                    st.markdown(f"- {rec_title}") # Displaying just the title
                        except json.JSONDecodeError:
                            st.markdown("_Error loading recommended materials. Data format may be incorrect._")
                    st.markdown("</div>", unsafe_allow_html=True) # End history item card
            else:
                st.info(f"No past session notes found for {st.session_state['current_user_name']} logged by {st.session_state['logged_in_username']}. Save a session to see history!")
        else:
            st.info("Enter a 'Pair's Name' above to view their session history.")

    elif st.session_state['current_page'] == 'decade_summary':
        st.markdown('<a name="decade_summary"></a>', unsafe_allow_html=True)
        st.header(f"🕰️ A Glimpse into the {st.session_state['current_user_decade']}:")
        if st.session_state['current_user_decade']:
            with st.spinner(f"Generating context for the {st.session_state['current_user_decade']}..."):
                historical_context = generate_historical_context(st.session_state['current_user_decade'], client_ai)
                st.info(historical_context)
        else:
            st.info("Please set a 'Favorite Decade' in the Pair Profile to view a historical summary.")

    # --- End of Main Content Area Wrapper ---
    st.markdown('</div>', unsafe_allow_html=True)
