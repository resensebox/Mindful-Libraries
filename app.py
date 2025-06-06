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
        sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXRcfmxjoj5s')
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
        sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXRcfmxjoj5s')
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
        sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXRcfmxjoj5s')
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
        sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXRcfmxjoj5s')
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
        sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXRcfmxjoj5s')
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
        sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXRcfmxjoj5s')
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
        sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXRcfmxjoj5s')
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
        sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXRcfmxjoj5s')
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
# Removed explicit markdown div here
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

# --- Login / Register Section ---
if not st.session_state['is_authenticated']:
    # Main title is outside the main-content-wrapper when logged out
    st.markdown("<h1 style='text-align: center; color: #333333; margin-top: 1rem; margin-bottom: 1.5rem; font-size: 2.5em; font-weight: 700; letter-spacing: -0.02em;'>Discover Your Next Nostalgic Read!</h1>", unsafe_allow_html=True)
    st.info("Please log in or register to use the Mindful Libraries app.")

    # Toggles between login and registration forms
    login_tab, register_tab = st.tabs(["Log In", "Register"])

    with login_tab:
        with st.form("login_form"):
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            if st.form_submit_button("Log In"):
                if username in USERS and USERS[username] == password:
                    st.session_state['is_authenticated'] = True
                    st.session_state['logged_in_username'] = username
                    PAIRS_DATA = load_pairs(username) # Load pairs for the logged-in volunteer
                    st.success("Logged in successfully!")
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
    with register_tab:
        with st.form("register_form"):
            new_username = st.text_input("New Username", key="register_username")
            new_password = st.text_input("New Password", type="password", key="register_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="register_confirm_password")
            if st.form_submit_button("Register"):
                if new_username and new_password and confirm_password:
                    if new_password == confirm_password:
                        if new_username in USERS:
                            st.error("Username already exists. Please choose a different one.")
                        else:
                            if save_new_user(new_username, new_password):
                                st.session_state['is_authenticated'] = True
                                st.session_state['logged_in_username'] = new_username
                                PAIRS_DATA = load_pairs(new_username) # Load pairs for the new volunteer
                                st.rerun()
                    else:
                        st.error("Passwords do not match.")
                else:
                    st.error("Please fill in all fields.")

else: # User is authenticated
    # Page navigation in sidebar
    st.sidebar.header("Navigation")
    if st.sidebar.button("Dashboard", key="nav_dashboard"):
        st.session_state['current_page'] = 'dashboard'
    if st.sidebar.button("Pair Profile", key="nav_pair_profile"):
        st.session_state['current_page'] = 'pair_profile'
    if st.sidebar.button("Session Notes", key="nav_session_notes"):
        st.session_state['current_page'] = 'session_notes'
    if st.sidebar.button("Session History", key="nav_session_history"):
        st.session_state['current_page'] = 'session_history'
    if st.sidebar.button("Decade Summary", key="nav_decade_summary"):
        st.session_state['current_page'] = 'decade_summary'
    
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"Logged in as: **{st.session_state['logged_in_username']}**")

    # --- Page Content ---
    if st.session_state['current_page'] == 'dashboard':
        st.header("Welcome to Mindful Libraries! 📚")
        st.markdown(f"Hello **{st.session_state['logged_in_username']}**, start by selecting or adding a pair to begin your session.")

        pair_names = [""] + sorted(list(PAIRS_DATA.keys()))
        selected_pair_name = st.selectbox("Select Pair", pair_names, index=pair_names.index(st.session_state['current_user_name']) if st.session_state['current_user_name'] in pair_names else 0)

        with st.expander("Add New Pair"):
            with st.form("new_pair_form"):
                new_pair_name = st.text_input("New Pair's Name").strip()
                new_pair_jobs = st.text_input("New Pair's Past Jobs/Professions (comma-separated)")
                new_pair_life_experiences = st.text_area("New Pair's Significant Life Experiences (e.g., historical events, major life changes)")
                new_pair_hobbies = st.text_input("New Pair's Hobbies/Interests (comma-separated)")
                new_pair_decade = st.text_input("New Pair's Favorite Decade (e.g., 1950s, 1960s)").strip()
                new_pair_college_chapter = st.text_input("New Pair's College Chapter (if applicable)").strip() # New input field
                if st.form_submit_button("Add Pair"):
                    if new_pair_name:
                        if new_pair_name not in PAIRS_DATA:
                            if save_pair_details(st.session_state['logged_in_username'], new_pair_name, new_pair_jobs, new_pair_life_experiences, new_pair_hobbies, new_pair_decade, new_pair_college_chapter):
                                st.session_state['current_user_name'] = new_pair_name
                                st.session_state['current_user_jobs'] = new_pair_jobs
                                st.session_state['current_user_life_experiences'] = new_pair_life_experiences
                                st.session_state['current_user_hobbies'] = new_pair_hobbies
                                st.session_state['current_user_decade'] = new_pair_decade
                                st.session_state['current_user_college_chapter'] = new_pair_college_chapter
                                st.rerun() # Rerun to update the selectbox
                        else:
                            st.warning(f"A pair with the name '{new_pair_name}' already exists for your account.")
                    else:
                        st.warning("Please enter a name for the new pair.")

        if selected_pair_name and selected_pair_name != st.session_state['current_user_name']:
            st.session_state['current_user_name'] = selected_pair_name
            pair_info = PAIRS_DATA.get(selected_pair_name, {})
            st.session_state['current_user_jobs'] = pair_info.get('jobs', '')
            st.session_state['current_user_life_experiences'] = pair_info.get('life_experiences', '')
            st.session_state['current_user_hobbies'] = pair_info.get('hobbies', '')
            st.session_state['current_user_decade'] = pair_info.get('decade', '')
            st.session_state['current_user_college_chapter'] = pair_info.get('college_chapter', '')
            st.session_state['selected_tags'] = [] # Clear tags when changing pair
            st.session_state['active_tags_for_filter'] = []
            st.session_state['tag_checkbox_states'] = {}
            st.session_state['recommended_books_current_session'] = [] # Clear recommendations
            st.session_state['recommended_newspapers_current_session'] = []
            st.rerun() # Rerun to update the UI with the new pair's data
        elif not selected_pair_name and st.session_state['current_user_name']:
            # This handles the case where the user deselects the current pair (selects "")
            st.session_state['current_user_name'] = ""
            st.session_state['current_user_jobs'] = ""
            st.session_state['current_user_life_experiences'] = ""
            st.session_state['current_user_hobbies'] = ""
            st.session_state['current_user_decade'] = ""
            st.session_state['current_user_college_chapter'] = ""
            st.session_state['selected_tags'] = []
            st.session_state['active_tags_for_filter'] = []
            st.session_state['tag_checkbox_states'] = {}
            st.session_state['recommended_books_current_session'] = []
            st.session_state['recommended_newspapers_current_session'] = []
            st.rerun()

        if st.session_state['current_user_name']:
            st.markdown(f"### Current Pair: **{st.session_state['current_user_name']}**")
            st.markdown(f"**Jobs:** {st.session_state['current_user_jobs'] if st.session_state['current_user_jobs'] else 'N/A'}")
            st.markdown(f"**Life Experiences:** {st.session_state['current_user_life_experiences'] if st.session_state['current_user_life_experiences'] else 'N/A'}")
            st.markdown(f"**Hobbies:** {st.session_state['current_user_hobbies'] if st.session_state['current_user_hobbies'] else 'N/A'}")
            st.markdown(f"**Favorite Decade:** {st.session_state['current_user_decade'] if st.session_state['current_user_decade'] else 'N/A'}")
            st.markdown(f"**College Chapter:** {st.session_state['current_user_college_chapter'] if st.session_state['current_user_college_chapter'] else 'N/A'}") # Display new field

            st.markdown("---")
            st.subheader("Personalized Tag Generation")
            search_query = st.text_input("Enter a search term to find relevant topics (e.g., 'gardening', 'history', 'sports'):")
            
            all_content_tags = sorted(list(set(tag for tags_set in content_df['tags'] for tag in tags_set if tag)))

            # Dynamic tag selection
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("##### **Available Topics:**")
                for tag in all_content_tags:
                    if tag not in st.session_state['tag_checkbox_states']:
                        st.session_state['tag_checkbox_states'][tag] = False
                    
                    # Update checkbox state if tag is in selected_tags from a previous session or AI search
                    if tag in st.session_state['selected_tags'] or tag in st.session_state['active_tags_for_filter']:
                        st.session_state['tag_checkbox_states'][tag] = True

                    st.session_state['tag_checkbox_states'][tag] = st.checkbox(
                        tag.replace('_', ' ').title(), 
                        value=st.session_state['tag_checkbox_states'][tag], 
                        key=f"checkbox_{tag}"
                    )
            
            with col2:
                st.markdown("##### **Selected Topics:**")
                # Filter selected tags based on checkbox states
                st.session_state['selected_tags'] = [tag for tag, is_checked in st.session_state['tag_checkbox_states'].items() if is_checked]
                
                if st.session_state['selected_tags']:
                    st.write(", ".join([tag.replace('_', ' ').title() for tag in st.session_state['selected_tags']]))
                else:
                    st.info("No topics selected yet.")

            if st.button("Expand Search with AI (based on search term)", key="ai_expand_button"):
                if search_query:
                    with st.spinner("Expanding search query with AI..."):
                        ai_expanded_tags = get_ai_expanded_search_tags(search_query, all_content_tags, client_ai)
                        if ai_expanded_tags:
                            # Add new AI-generated tags to selected_tags and update checkboxes
                            for tag in ai_expanded_tags:
                                if tag not in st.session_state['selected_tags']:
                                    st.session_state['selected_tags'].append(tag)
                                st.session_state['tag_checkbox_states'][tag] = True # Mark as checked
                            st.success(f"AI added relevant tags: {', '.join(ai_expanded_tags)}")
                            st.rerun() # Rerun to update checkboxes
                        else:
                            st.info("AI could not find relevant tags for your query.")
                else:
                    st.warning("Please enter a search term to expand with AI.")

            st.markdown("---")
            if st.button("Generate Reading Recommendations"):
                if st.session_state['selected_tags']:
                    st.session_state['active_tags_for_filter'] = st.session_state['selected_tags']
                    st.session_state['recommended_books_current_session'] = []
                    st.session_state['recommended_newspapers_current_session'] = []
                else:
                    st.warning("Please select some topics before generating recommendations.")

            if st.session_state['active_tags_for_filter']:
                st.subheader("Recommended for this Session:")

                # Load feedback scores for reweighting
                feedback_scores = load_feedback_tag_scores()

                # Filter content by active tags and apply reweighting
                filtered_content = content_df[content_df['tags'].apply(lambda x: bool(x.intersection(set(st.session_state['active_tags_for_filter']))))].copy()
                
                if not filtered_content.empty:
                    # Calculate relevance score based on matched tags and feedback
                    filtered_content['relevance_score'] = filtered_content['tags'].apply(
                        lambda item_tags: sum(
                            1 + feedback_scores.get(tag, 0) for tag in item_tags.intersection(set(st.session_state['active_tags_for_filter']))
                        )
                    )
                    # Sort by relevance score, then by interaction count (descending)
                    filtered_content['interaction_count'] = filtered_content['Title'].apply(lambda title: st.session_state['book_counter'][title])
                    
                    # Sort by relevance score (descending), then interaction count (ascending - to show less read first)
                    # This logic was reversed. It should be most relevant, then least read for novelty.
                    # corrected: sort by relevance_score (desc), then interaction_count (asc)
                    sorted_content = filtered_content.sort_values(
                        by=['relevance_score', 'interaction_count'],
                        ascending=[False, True]
                    ).drop_duplicates(subset=['Title'])

                    books = sorted_content[sorted_content['Type'] == 'Book'].head(5)
                    newspapers = sorted_content[sorted_content['Type'] == 'Newspaper'].head(5)
                    
                    st.session_state['recommended_books_current_session'] = books.to_dict('records')
                    st.session_state['recommended_newspapers_current_session'] = newspapers.to_dict('records')

                if st.session_state['recommended_books_current_session'] or st.session_state['recommended_newspapers_current_session']:
                    st.subheader("Books:")
                    if st.session_state['recommended_books_current_session']:
                        for book in st.session_state['recommended_books_current_session']:
                            with st.container(border=True): # Use a container for each book for better visual separation
                                img_url = get_image_url(book)
                                col_img, col_info = st.columns([1, 3])
                                with col_img:
                                    st.image(img_url, width=120)
                                with col_info:
                                    st.markdown(f"**Title:** {book.get('Title', 'N/A')}")
                                    st.markdown(f"**Summary:** {book.get('Summary', 'N/A')}")
                                    st.link_button("View on Amazon", url=book.get('URL', '#'))
                                    
                                    # Generate and display explanation
                                    explanation = generate_recommendation_explanation(
                                        book,
                                        {'name': st.session_state['current_user_name'],
                                         'jobs': st.session_state['current_user_jobs'],
                                         'hobbies': st.session_state['current_user_hobbies'],
                                         'decade': st.session_state['current_user_decade'],
                                         'life_experiences': st.session_state['current_user_life_experiences'],
                                         'college_chapter': st.session_state['current_user_college_chapter'] # Pass new field
                                        },
                                        st.session_state['selected_tags'],
                                        client_ai
                                    )
                                    st.markdown(f"**Why this is recommended:** {explanation}")
                                    
                                    # Feedback mechanism for each book
                                    feedback_key = f"feedback_book_{book.get('Title', 'N/A')}"
                                    st.write("Was this a good recommendation?")
                                    col_like, col_dislike = st.columns(2)
                                    with col_like:
                                        if st.button("👍 Yes", key=f"like_{feedback_key}"):
                                            # Update Feedback sheet with positive feedback
                                            try:
                                                sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXRcfmxjoj5s')
                                                fb_ws = sheet.worksheet('Feedback')
                                                fb_ws.append_row([book.get('Title', ''), ", ".join(book.get('tags', [])), "Yes"])
                                                st.success("Feedback recorded!")
                                                st.cache_data(load_feedback_tag_scores).clear() # Clear cache to reload scores
                                            except Exception as e:
                                                st.error(f"Failed to record feedback. Error: {e}")
                                    with col_dislike:
                                        if st.button("👎 No", key=f"dislike_{feedback_key}"):
                                            # Update Feedback sheet with negative feedback
                                            try:
                                                sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXRcfmxjoj5s')
                                                fb_ws = sheet.worksheet('Feedback')
                                                fb_ws.append_row([book.get('Title', ''), ", ".join(book.get('tags', [])), "No"])
                                                st.success("Feedback recorded!")
                                                st.cache_data(load_feedback_tag_scores).clear() # Clear cache to reload scores
                                            except Exception as e:
                                                st.error(f"Failed to record feedback. Error: {e}")
                                
                                st.session_state['book_counter'][book.get('Title', 'N/A')] += 1 # Increment interaction count


                    else:
                        st.info("No book recommendations based on selected topics.")

                    st.subheader("Newspapers:")
                    if st.session_state['recommended_newspapers_current_session']:
                        for newspaper in st.session_state['recommended_newspapers_current_session']:
                            with st.container(border=True): # Use a container for each newspaper for better visual separation
                                img_url = get_image_url(newspaper)
                                col_img, col_info = st.columns([1, 3])
                                with col_img:
                                    st.image(img_url, width=120)
                                with col_info:
                                    st.markdown(f"**Title:** {newspaper.get('Title', 'N/A')}")
                                    st.markdown(f"**Summary:** {newspaper.get('Summary', 'N/A')}")
                                    st.link_button("View Article", url=newspaper.get('URL', '#'))
                                    
                                    # Generate and display explanation
                                    explanation = generate_recommendation_explanation(
                                        newspaper,
                                        {'name': st.session_state['current_user_name'],
                                         'jobs': st.session_state['current_user_jobs'],
                                         'hobbies': st.session_state['current_user_hobbies'],
                                         'decade': st.session_state['current_user_decade'],
                                         'life_experiences': st.session_state['current_user_life_experiences'],
                                         'college_chapter': st.session_state['current_user_college_chapter'] # Pass new field
                                        },
                                        st.session_state['selected_tags'],
                                        client_ai
                                    )
                                    st.markdown(f"**Why this is recommended:** {explanation}")

                                    # Feedback mechanism for each newspaper
                                    feedback_key = f"feedback_newspaper_{newspaper.get('Title', 'N/A')}"
                                    st.write("Was this a good recommendation?")
                                    col_like, col_dislike = st.columns(2)
                                    with col_like:
                                        if st.button("👍 Yes", key=f"like_{feedback_key}"):
                                            # Update Feedback sheet with positive feedback
                                            try:
                                                sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXRcfmxjoj5s')
                                                fb_ws = sheet.worksheet('Feedback')
                                                fb_ws.append_row([newspaper.get('Title', ''), ", ".join(newspaper.get('tags', [])), "Yes"])
                                                st.success("Feedback recorded!")
                                                st.cache_data(load_feedback_tag_scores).clear() # Clear cache to reload scores
                                            except Exception as e:
                                                st.error(f"Failed to record feedback. Error: {e}")
                                    with col_dislike:
                                        if st.button("👎 No", key=f"dislike_{feedback_key}"):
                                            # Update Feedback sheet with negative feedback
                                            try:
                                                sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXRcfmxjoj5s')
                                                fb_ws = sheet.worksheet('Feedback')
                                                fb_ws.append_row([newspaper.get('Title', ''), ", ".join(newspaper.get('tags', [])), "No"])
                                                st.success("Feedback recorded!")
                                                st.cache_data(load_feedback_tag_scores).clear() # Clear cache to reload scores
                                            except Exception as e:
                                                st.error(f"Failed to record feedback. Error: {e}")

                                st.session_state['book_counter'][newspaper.get('Title', 'N/A')] += 1 # Increment interaction count
                    else:
                        st.info("No newspaper recommendations based on selected topics.")
                
                st.markdown("---")
                st.subheader("Suggested Activities:")
                recommended_titles_list = [item.get('Title', '') for item in st.session_state['recommended_books_current_session'] + st.session_state['recommended_newspapers_current_session']]
                activity_suggestions = generate_activities(client_ai, st.session_state['active_tags_for_filter'], recommended_titles_list)
                for activity in activity_suggestions:
                    st.markdown(f"- {activity}")
                
            else:
                st.info("Select topics and click 'Generate Reading Recommendations' to see personalized content and activities.")

    elif st.session_state['current_page'] == 'pair_profile':
        st.header(f"✏️ Edit Profile for: {st.session_state['current_user_name']}")
        if st.session_state['current_user_name']:
            with st.form("edit_pair_form"):
                edited_jobs = st.text_input("Past Jobs/Professions (comma-separated)", value=st.session_state['current_user_jobs'])
                edited_life_experiences = st.text_area("Significant Life Experiences (e.g., historical events, major life changes)", value=st.session_state['current_user_life_experiences'])
                edited_hobbies = st.text_input("Hobbies/Interests (comma-separated)", value=st.session_state['current_user_hobbies'])
                edited_decade = st.text_input("Favorite Decade (e.g., 1950s, 1960s)", value=st.session_state['current_user_decade'])
                edited_college_chapter = st.text_input("College Chapter (if applicable)", value=st.session_state['current_user_college_chapter']) # New input field
                if st.form_submit_button("Save Changes"):
                    if save_pair_details(
                        st.session_state['logged_in_username'],
                        st.session_state['current_user_name'],
                        edited_jobs,
                        edited_life_experiences,
                        edited_hobbies,
                        edited_decade,
                        edited_college_chapter
                    ):
                        st.session_state['current_user_jobs'] = edited_jobs
                        st.session_state['current_user_life_experiences'] = edited_life_experiences
                        st.session_state['current_user_hobbies'] = edited_hobbies
                        st.session_state['current_user_decade'] = edited_decade
                        st.session_state['current_user_college_chapter'] = edited_college_chapter
                        st.rerun() # Rerun to update displayed info
        else:
            st.info("Please select a 'Pair' on the Dashboard to edit their profile.")

    elif st.session_state['current_page'] == 'session_notes':
        st.header(f"📝 Session Notes for {st.session_state['current_user_name']}")
        if st.session_state['current_user_name']:
            with st.form("session_notes_form"):
                st.session_state['session_date'] = st.date_input("Session Date", value=st.session_state['session_date'])
                st.session_state['session_mood'] = st.selectbox("Pair's Mood During Session", 
                                                                 ["Very Happy 😁", "Happy 😊", "Neutral 😐", "Sad 🙁", "Very Sad 😭"], 
                                                                 index=["Very Happy 😁", "Happy 😊", "Neutral 😐", "Sad 🙁", "Very Sad 😭"].index(st.session_state['session_mood']))
                st.session_state['session_engagement'] = st.selectbox("Pair's Engagement Level", 
                                                                      ["Highly Engaged ⭐⭐⭐", "Moderately Engaged ⭐⭐", "Minimally Engaged ⭐", "Not Engaged 🚫"],
                                                                      index=["Highly Engaged ⭐⭐⭐", "Moderately Engaged ⭐⭐", "Minimally Engaged ⭐", "Not Engaged 🚫"].index(st.session_state['session_engagement']))
                st.session_state['session_takeaways'] = st.text_area("Key Takeaways/Observations from Session", value=st.session_state['session_takeaways'])

                st.markdown("##### **Recommended Materials from this session (if any):**")
                
                # Combine books and newspapers from current session recommendations
                all_recommended_materials = st.session_state['recommended_books_current_session'] + st.session_state['recommended_newspapers_current_session']
                
                if all_recommended_materials:
                    for item in all_recommended_materials:
                        st.markdown(f"- **{item.get('Title', 'N/A')}** ({item.get('Type', 'N/A')})")
                        # Include summary or explanation if available
                        if item.get('Summary'):
                            st.markdown(f"  Summary: {item.get('Summary')}")
                        elif item.get('Explanation'): # Assuming 'Explanation' might come from AI or similar
                            st.markdown(f"  Explanation: {item.get('Explanation')}")

                    # Convert the list of dictionaries to a JSON string for saving
                    recommended_materials_json = json.dumps(all_recommended_materials)
                else:
                    st.info("No materials were recommended during the current session.")
                    recommended_materials_json = "[]" # Save an empty JSON array if no recommendations

                if st.form_submit_button("Save Session Notes"):
                    if st.session_state['current_user_name'] and st.session_state['session_takeaways']:
                        save_session_notes_to_gsheet(
                            st.session_state['current_user_name'],
                            st.session_state['session_date'],
                            st.session_state['session_mood'],
                            st.session_state['session_engagement'],
                            st.session_state['session_takeaways'],
                            recommended_materials_json,
                            st.session_state['logged_in_username'] # Pass the logged-in volunteer's username
                        )
                        st.session_state['show_printable_summary'] = True # Set flag to show summary
                        st.cache_data(load_session_logs).clear() # Clear cache for session logs
                        st.rerun() # Rerun to show the summary or confirm save
                    else:
                        st.warning("Please select a 'Pair' and enter 'Key Takeaways' to save session notes.")
        else:
            st.info("Please select a 'Pair' on the Dashboard to log session notes.")

        if st.session_state['show_printable_summary']:
            st.subheader("Printable Session Summary")
            user_info = {
                'name': st.session_state['current_user_name'],
                'jobs': st.session_state['current_user_jobs'],
                'life_experiences': st.session_state['current_user_life_experiences'],
                'hobbies': st.session_state['current_user_hobbies'],
                'decade': st.session_state['current_user_decade'],
                'college_chapter': st.session_state['current_user_college_chapter']
            }
            printable_summary = get_printable_summary(
                user_info,
                st.session_state['active_tags_for_filter'],
                st.session_state['recommended_books_current_session'],
                st.session_state['recommended_newspapers_current_session'],
                generate_activities(client_ai, st.session_state['active_tags_for_filter'], [item.get('Title', '') for item in st.session_state['recommended_books_current_session'] + st.session_state['recommended_newspapers_current_session']]),
                st.session_state['logged_in_username'] # Pass volunteer username
            )
            st.text_area("Copy this summary for your records:", printable_summary, height=400)
            st.download_button(
                label="Download Summary as TXT",
                data=printable_summary,
                file_name=f"{st.session_state['current_user_name']}_session_summary_{datetime.now().strftime('%Y%m%d')}.txt",
                mime="text/plain"
            )

    elif st.session_state['current_page'] == 'session_history':
        st.header(f"📖 Session History for: {st.session_state['current_user_name']}")
        if st.session_state['current_user_name']:
            session_history_df = load_session_logs(st.session_state['current_user_name'], st.session_state['logged_in_username'])
            
            if not session_history_df.empty:
                for index, row in session_history_df.iterrows():
                    st.markdown(f"### Session on {row['Session Date']}")
                    st.markdown(f"**Mood:** {row['Mood']}")
                    st.markdown(f"**Engagement:** {row['Engagement']}")
                    st.markdown(f"**Takeaways:** {row['Takeaways']}")
                    
                    # Display recommended materials in-line
                    recommended_materials_str = row.get('Recommended Materials', '[]')
                    try:
                        recs = json.loads(recommended_materials_str)
                        if recs:
                            st.markdown("##### **Recommended Materials for this Session:**")
                            # Display each recommended item with title and explanation
                            for item in recs: # recs is a list of dictionaries
                                title = item.get('Title', 'N/A')
                                # Assuming 'Explanation' key might exist, or 'Summary' if not
                                explanation = item.get('Explanation', item.get('Summary', 'No explanation or summary provided.'))
                                st.markdown(f"- **Title:** {title}")
                                st.markdown(f"  **Why this is recommended:** {explanation}")
                                # Optional: Add URL if available
                                if item.get('URL'):
                                    st.markdown(f"  [View Material]({item.get('URL')})")
                    except json.JSONDecodeError:
                        st.markdown("_Error loading recommended materials. Data format may be incorrect._")
                    st.markdown("---") # Add a separator between history items
            else:
                st.info(f"No past session notes found for {st.session_state['current_user_name']} logged by {st.session_state['logged_in_username']}. Save a session to see history!")
        else:
            st.info("Enter a 'Pair's Name' above to view their session history.")

    elif st.session_state['current_page'] == 'decade_summary':
        # Removed the custom anchor tag: st.markdown('<a name="decade_summary"></a>', unsafe_allow_html=True)
        st.header(f"🕰️ A Glimpse into the {st.session_state['current_user_decade']}:")
        if st.session_state['current_user_decade']:
            with st.spinner(f"Generating context for the {st.session_state['current_user_decade']}..."):
                historical_context = generate_historical_context(st.session_state['current_user_decade'], client_ai)
                st.info(historical_context)
        else:
            st.info("Please set a 'Favorite Decade' in the Pair Profile to view a historical summary.")
