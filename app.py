import streamlit as st
import json
from fpdf import FPDF
from datetime import datetime, date
import os
import logging
import sqlite3
import smtplib
from email.mime.text import MIMEText
import requests # For Gemini API
import base64 # For encoding image to base64 if needed for image understanding, not used here
import time # For simulating loading

# --- Logging Setup ---
logging.basicConfig(filename='app_activity.log', level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

st.set_option('client.showErrorDetails', True)
st.set_page_config(page_title="History Hub", layout="wide", initial_sidebar_state="expanded") # Changed to wide layout for sidebar

# --- Database Setup (SQLite for Users) ---
DB_NAME = 'users.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Drop the table if it exists to ensure a clean schema, especially during development
    # This ensures the 'password' column is always present if the schema changes
    c.execute('''
        DROP TABLE IF EXISTS users
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_user(username, password):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False # Username already exists
    finally:
        conn.close()

def verify_user(username, password):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    user = c.fetchone()
    conn.close()
    return user is not None

# --- Gemini API Configuration ---
# Use an empty string for the API key; Canvas will provide it at runtime.
GEMINI_API_KEY = ""
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# --- Email Configuration ---
# For demonstration purposes. In a real app, use Streamlit secrets or environment variables.
# SMTP_SERVER = "smtp.gmail.com" # Example for Gmail
# SMTP_PORT = 587
# SMTP_USERNAME = "your_email@example.com"
# SMTP_PASSWORD = "your_email_password" # Use app-specific passwords for Gmail/Outlook

# --- Session State Initialization ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = None
if 'preferred_categories' not in st.session_state:
    st.session_state['preferred_categories'] = ['Historical', 'Births', 'Deaths', 'Holidays', 'Other'] # Default all
if 'all_categories' not in st.session_state:
    st.session_state['all_categories'] = ['Historical', 'Births', 'Deaths', 'Holidays', 'Other']
if 'show_category_filter' not in st.session_state: # To manage category filter visibility
    st.session_state['show_category_filter'] = False

# --- Helper Functions ---

def display_message(message_type, text):
    """Displays a custom message with styling using st.info, st.success, etc."""
    if message_type == 'success':
        st.success(text)
    elif message_type == 'error':
        st.error(text)
    elif message_type == 'warning':
        st.warning(text)
    elif message_type == 'info':
        st.info(text)
    else:
        st.write(text) # Fallback for unknown types

@st.cache_data(ttl=3600*24) # Cache events for 24 hours
def get_historical_events_from_gemini(selected_date: date):
    """Fetches historical events for a given date using the Gemini API."""
    prompt = (
        f"Provide a list of significant historical events, births, deaths, and holidays for "
        f"{selected_date.strftime('%B %d')}. Categorize each event as 'Historical', 'Births', "
        f"'Deaths', 'Holidays', or 'Other'. Ensure the output is a JSON array of objects, "
        f"each with 'year' (string), 'event' (string), and 'category' (string) fields. "
        f"Example: [{{'year': '1944', 'event': 'D-Day landings.', 'category': 'Historical'}}] "
        f"Ensure the JSON is perfectly parseable and directly usable."
    )

    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": prompt}]}
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "year": {"type": "STRING"},
                        "event": {"type": "STRING"},
                        "category": {"type": "STRING", "enum": st.session_state['all_categories']}
                    },
                    "required": ["year", "event", "category"]
                }
            }
        }
    }

    try:
        response = requests.post(f"{GEMINI_API_URL}?key={GEMINI_API_KEY}", headers=headers, json=payload)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        result = response.json()

        if result and 'candidates' in result and len(result['candidates']) > 0 and \
           'content' in result['candidates'][0] and 'parts' in result['candidates'][0]['content'] and \
           len(result['candidates'][0]['content']['parts']) > 0:
            json_text = result['candidates'][0]['content']['parts'][0]['text']
            events = json.loads(json_text)
            return events
        else:
            logging.error(f"Gemini API returned unexpected structure: {result}")
            display_message('error', 'Failed to get events: Unexpected API response.')
            return []
    except requests.exceptions.RequestException as e:
        logging.error(f"Gemini API request failed: {e}")
        display_message('error', f'Failed to fetch events from Gemini API: {e}')
        return []
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse Gemini API JSON response: {e}. Raw response: {response.text}")
        display_message('error', 'Failed to parse events. Please try again.')
        return []

def create_pdf(events, selected_date):
    """Generates a PDF from the list of events."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size = 12)
    pdf.cell(200, 10, txt = f"Historical Events for {selected_date.strftime('%B %d, %Y')}", ln = True, align = 'C')
    pdf.ln(10) # Add some space

    for event in events:
        pdf.set_font("Arial", 'B', 10) # Bold for year and category
        pdf.multi_cell(0, 5, f"{event['year']}: (Category: {event['category']})", align='L')
        pdf.set_font("Arial", '', 10) # Normal for event text
        pdf.multi_cell(0, 5, f"  {event['event']}", align='L')
        pdf.ln(3) # Small line break between events

    # Save to a temporary file
    filename = f"Events_{selected_date.strftime('%Y%m%d')}.pdf"
    pdf.output(filename)
    return filename

def send_email_via_mailto(events, selected_date):
    """Prepares a mailto: link for sharing events via email."""
    subject = f"This Day in History - {selected_date.strftime('%B %d, %Y')}"
    body = f"Hello,\n\nHere are some historical events for {selected_date.strftime('%B %d')}:\n\n"
    for event in events:
        body += f"- {event['year']}: {event['event']} (Category: {event['category']})\n"
    body += "\nEnjoy your day!"

    mailto_link = f"mailto:?subject={requests.utils.quote(subject)}&body={requests.utils.quote(body)}"
    return mailto_link


# --- UI Styling (Tailwind-like CSS for Streamlit) ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

html, body, .stApp {
    font-family: 'Inter', sans-serif;
    color: #2b2b2b;
    background-color: #e8f0fe; /* Light blue background from MindfulVersion */
}

/* Main container for the app content, similar to MindfulVersion */
.main .block-container {
    padding-top: 2rem;
    padding-right: 2rem;
    padding-left: 2rem;
    padding-bottom: 2rem;
    background-color: #e8f0fe; /* Light blue background for content area */
}

/* Sidebar styling from MindfulVersion (adapted for History App's color scheme) */
[data-testid="stSidebar"] {
    background-color: #36393f; /* Darker purple/gray for sidebar */
    color: #ffffff;
    padding: 2rem 1.5rem;
    border-radius: 0 10px 10px 0; /* Rounded right corners */
    box-shadow: 2px 0 10px rgba(0, 0, 0, 0.1);
}

[data-testid="stSidebar"] .stButton > button {
    background-color: #663399; /* Medium purple for sidebar buttons */
    color: #ffffff;
    font-weight: 600;
    border: none;
    border-radius: 8px;
    padding: 0.7em 1em;
    width: 100%;
    text-align: left;
    transition: background-color 0.2s ease;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1); /* Subtle shadow for buttons */
}

[data-testid="stSidebar"] .stButton > button:hover {
    background-color: #7b4aa7; /* Lighter purple on hover */
    transform: translateY(-1px); /* Slight lift effect */
}

/* Date input in sidebar */
[data-testid="stSidebar"] input[type="date"] {
    background-color: #474a50; /* Darker input background */
    color: #ffffff;
    border: 1px solid #5a5d62;
    border-radius: 8px;
    padding: 0.5rem;
}
/* Calendar icon color for date input */
[data-testid="stSidebar"] .stDateInput label + div::before {
    filter: brightness(0) invert(1); /* Makes the calendar icon white */
}


/* Checkbox styling in sidebar */
[data-testid="stSidebar"] .stCheckbox span {
    color: #ffffff;
    font-size: 1.1em; /* Larger font for checkboxes */
    margin-left: 5px;
}

[data-testid="stSidebar"] .stCheckbox label {
    display: flex;
    align-items: center;
    margin-bottom: 0.5rem;
}

[data-testid="stSidebar"] .stCheckbox input[type="checkbox"] {
    margin-right: 0.5rem;
    /* Custom checkbox styling */
    width: 18px; /* Larger checkbox */
    height: 18px;
    accent-color: #9333ea; /* Purple checkmark */
    border-radius: 4px;
}


/* Headings from MindfulVersion */
h1, h2, h3, h4, h5, h6, label {
    color: #333333; /* Darker headings */
    font-weight: bold;
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #eeeeee; /* Subtle line under subheaders */
}
/* Main page title outside of block-container structure for login screen */
h1.main-title {
    text-align: center;
    color: #333333;
    margin-top: 1rem; /* Adjusted top margin after removing .main-content-wrapper */
    margin-bottom: 1.5rem;
    font-size: 2.5em; /* Make it stand out */
    font-weight: 700;
    letter-spacing: -0.02em;
    border-bottom: none; /* No border for main app title */
    padding-bottom: 0;
}


/* Event cards (like chat messages) - Adapted from previous version for consistency */
.event-card {
    background-color: #ffffff;
    border-radius: 12px;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.05);
    padding: 1.5rem;
    margin-bottom: 1rem;
    display: flex;
    align-items: flex-start;
    gap: 1rem;
    border: 1px solid #e0e0e0;
}

.event-card .year-avatar {
    flex-shrink: 0;
    width: 3.5rem;
    height: 3.5rem;
    border-radius: 50%;
    background-color: #663399; /* Purple avatar */
    color: #ffffff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
    font-size: 1.1em;
}

.event-card .event-content p {
    margin: 0;
    color: #333333;
    font-size: 1.05em;
    line-height: 1.5;
}

.event-card .event-meta {
    display: flex;
    align-items: center;
    margin-top: 0.5rem;
    font-size: 0.85em;
    color: #666666;
}

.event-card .category-badge {
    padding: 0.25em 0.75em;
    border-radius: 9999px; /* Full rounded */
    font-weight: 600;
    font-size: 0.75em;
    white-space: nowrap;
}

/* Category colors - from previous version */
.badge-historical { background-color: #ede9fe; color: #5b21b6; } /* Purple */
.badge-births { background-color: #d1fae5; color: #065f46; } /* Green */
.badge-deaths { background-color: #fee2e2; color: #991b1b; } /* Red */
.badge-holidays { background-color: #dbeafe; color: #1e40af; } /* Blue */
.badge-other { background-color: #e0e0e0; color: #4b5563; } /* Gray */


/* Buttons for PDF/Email - Adapted from MindfulVersion buy-button style */
.stButton > button {
    background-color: #f49d37; /* Orange for main actions (keeping from history app) */
    color: #ffffff;
    font-weight: 600;
    font-size: 1em;
    padding: 0.7em 1.5em;
    border: none;
    border-radius: 8px;
    box-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    transition: background-color 0.3s ease, transform 0.2s ease;
    display: inline-flex;
    align-items: center;
    gap: 0.5em;
}

.stButton > button:hover {
    background-color: #e08b29; /* Darker orange on hover */
    transform: translateY(-2px); /* Lift effect */
}

.stButton > button:active {
    transform: translateY(0); /* Return to normal on click */
}

/* Login screen styles from MindfulVersion */
.login-container {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: calc(100vh - 80px); /* Adjust for header height */
    background-color: #e8f0fe; /* Light blue background */
}

.login-box {
    background-color: #ffffff;
    border-radius: 12px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
    padding: 3rem;
    width: 100%;
    max-width: 400px;
    text-align: center;
}

.login-box h2 {
    color: #663399; /* Purple for login heading */
    font-size: 2.2em;
    margin-bottom: 1.5rem;
    border-bottom: none; /* Remove border from login h2 */
    padding-bottom: 0;
}

.login-box input {
    width: 100%;
    padding: 0.8rem;
    margin-bottom: 1rem;
    border: 1px solid #cccccc;
    border-radius: 8px;
    font-size: 1em;
    transition: border-color 0.2s ease;
    box-shadow: inset 0 1px 2px rgba(0,0,0,0.05); /* Inner shadow for input */
}

.login-box input:focus {
    border-color: #663399; /* Highlight on focus (purple) */
    outline: none;
    box-shadow: 0 0 0 2px rgba(102, 51, 153, 0.2);
}

.login-box button {
    width: 100%;
    padding: 0.8rem;
    background-color: #663399; /* Purple login button */
    color: #ffffff;
    font-weight: 600;
    border: none;
    border-radius: 8px;
    font-size: 1.1em;
    cursor: pointer;
    transition: background-color 0.2s ease;
    box-shadow: 2px 2px 4px rgba(0,0,0,0.2); /* Added shadow for depth */
}

.login-box button:hover {
    background-color: #7b4aa7; /* Lighter purple on hover */
    transform: translateY(-2px); /* Lift effect */
}
.login-box button:active {
    transform: translateY(0); /* Return to normal on click */
}

/* Streamlit Alert styling (from MindfulVersion) */
.stAlert {
    border-radius: 8px;
    /* Specific background/border/color are managed by Streamlit's internal classes for success/info/warning/error */
    /* Adjust padding and shadow for visual appeal */
    padding: 1rem;
    box-shadow: 0 2px 6px rgba(0,0,0,0.08);
}
.stAlert.st-emotion-cache-12fm248.e1ytz8g21 { /* Example: targeting info alert */
    background-color: #e6f7ff; /* Light blue for info alerts */
    border-color: #91d5ff;
    color: #004085;
}
.stAlert.st-emotion-cache-12fm248.e1ytz8g21[kind="success"] {
    background-color: #f6ffed; /* Light green for success */
    border-color: #b7eb8f;
    color: #1890ff; /* Changed to match success text */
}
.stAlert.st-emotion-cache-12fm248.e1ytz8g21[kind="warning"] {
    background-color: #fffbe6; /* Light yellow for warning */
    border-color: #ffe58f;
    color: #faad14;
}
.stAlert.st-emotion-cache-12fm248.e1ytz8g21[kind="error"] {
    background-color: #fff1f0; /* Light red for error */
    border-color: #ffccc7;
    color: #cf1322;
}

/* Custom header/logo positioning */
[data-testid="stHeader"] {
    background-color: #ffffff;
    padding: 0.8rem 1.5rem;
    border-bottom: 1px solid #e0e0e0;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    border-radius: 0 0 12px 12px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: sticky;
    top: 0;
    z-index: 1000;
    margin-bottom: 0;
    width: 100%;
}
[data-testid="stHeader"] > div:first-child { /* Targets the internal container for logo */
    width: 100%; /* Allows logo to take full width for justify-content */
    display: flex;
    justify-content: flex-start; /* Align logo to the left */
    align-items: center;
}
[data-testid="stHeader"] button { /* Style for the logout button in the header */
    background-color: #dc3545; /* Red for logout */
    color: white;
    padding: 0.5rem 1rem;
    border-radius: 8px;
    font-weight: bold;
    transition: background-color 0.3s ease;
    box-shadow: none; /* Remove extra shadow */
}
[data-testid="stHeader"] button:hover {
    background-color: #c82333;
}
</style>
""", unsafe_allow_html=True)


# --- Login / Main App Flow ---

def login_page():
    # Header is now handled by Streamlit's default header area
    # This ensures logo and logout button are consistently at the very top
    
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    st.markdown('<h2>Welcome Back!</h2>', unsafe_allow_html=True)

    username = st.text_input("Username", key="login_username")
    password = st.text_input("Password", type="password", key="login_password")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Login", use_container_width=True):
            if verify_user(username, password):
                st.session_state['logged_in'] = True
                st.session_state['username'] = username
                st.rerun()
            else:
                display_message('error', "Invalid username or password.")
    with col2:
        if st.button("Sign Up", use_container_width=True):
            if username and password:
                # Dummy sign-up for demonstration; replace with actual user creation
                if add_user(username, password):
                    display_message('success', "Account created! Please log in.")
                else:
                    display_message('warning', "Username already exists.")
            else:
                display_message('warning', "Please enter a username and password to sign up.")

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def main_app():
    # Ensure header content is set at the top, outside specific page logic
    # This will be rendered by Streamlit's internal header mechanism
    # st.image("https://i.postimg.cc/0yVG4bhN/mindfullibrarieswhite-01.png", width=180) # Use this in actual header if needed
    
    # Sidebar
    with st.sidebar:
        st.markdown(f"""
            <div style="text-align: center; margin-bottom: 2rem;">
                <h1 style="color: white; font-size: 2.5em; margin-bottom: 0.5rem; border-bottom: none; padding-bottom: 0;">
                    <img src="https://api.iconify.design/lucide/history.svg?color=%23ffffff" width="32" height="32" style="display:inline-block; vertical-align: middle; margin-right: 0.5rem;" />
                    History Hub
                </h1>
                <p style="color: #ccc; font-size: 0.9em;">Hello, {st.session_state['username']}!</p>
            </div>
        """, unsafe_allow_html=True)

        selected_date = st.date_input("Select Date", datetime.today(), key="date_picker")

        st.markdown('<div style="margin-top: 1.5rem; margin-bottom: 1rem;">', unsafe_allow_html=True)
        if st.session_state.get('show_category_filter', False):
            if st.button("Categories  ▲", key="hide_categories_btn"):
                st.session_state['show_category_filter'] = False
        else:
            if st.button("Categories  ▼", key="show_categories_btn"):
                st.session_state['show_category_filter'] = True
        st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state.get('show_category_filter', False):
            st.markdown('<div style="background-color: #474a50; padding: 1rem; border-radius: 8px;">', unsafe_allow_html=True)
            new_preferred_categories = []
            for category in st.session_state['all_categories']:
                # Ensure each checkbox has a unique key for proper state management
                if st.checkbox(category, value=category in st.session_state['preferred_categories'], key=f"cat_checkbox_{category}"):
                    new_preferred_categories.append(category)
            st.session_state['preferred_categories'] = new_preferred_categories
            st.markdown('</div>', unsafe_allow_html=True)

        # Logout button in sidebar
        st.markdown('<div style="margin-top: auto; padding-top: 2rem;">', unsafe_allow_html=True)
        if st.button("Logout", key="logout_btn"):
            st.session_state['logged_in'] = False
            st.session_state['username'] = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # Main Content Area
    st.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem;">
            <h2 style="font-size: 2.5em; margin: 0; color: #333333; border-bottom: 1px solid #eeeeee; padding-bottom: 0.5rem;">
                Events for {selected_date.strftime('%B %d, %Y')}
            </h2>
            <div style="display: flex; gap: 1rem;">
                <a href="javascript:void(0);" onclick="window.downloadPDF()" style="
                    background-color: #f49d37; color: #ffffff; font-weight: 600; font-size: 1em;
                    padding: 0.7em 1.5em; border: none; border-radius: 8px; box-shadow: 2px 2px 4px rgba(0,0,0,0.1);
                    transition: background-color 0.3s ease, transform 0.2s ease; display: inline-flex; align-items: center; gap: 0.5em;
                ">
                    <img src="https://api.iconify.design/lucide/download.svg?color=%23ffffff" width="20" height="20" style="filter: invert(1);"/>
                    Download PDF
                </a>
                <a href="javascript:void(0);" onclick="window.sendEmail()" style="
                    background-color: #4CAF50; color: #ffffff; font-weight: 600; font-size: 1em;
                    padding: 0.7em 1.5em; border: none; border-radius: 8px; box-shadow: 2px 2px 4px rgba(0,0,0,0.1);
                    transition: background-color 0.3s ease, transform 0.2s ease; display: inline-flex; align-items: center; gap: 0.5em;
                ">
                    <img src="https://api.iconify.design/lucide/mail.svg?color=%23ffffff" width="20" height="20" style="filter: invert(1);" />
                    Share via Email
                </a>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Fetch events
    events_placeholder = st.empty()
    with events_placeholder:
        with st.spinner("Fetching historical events..."):
            events = get_historical_events_from_gemini(selected_date)
            time.sleep(1) # Simulate a brief loading time for better UX

    filtered_events = [
        event for event in events
        if event.get('category') in st.session_state['preferred_categories']
    ]

    if not filtered_events:
        display_message('info', "No events found for this date or matching your selected categories.")
    else:
        for event in filtered_events:
            category_class = f"badge-{event.get('category', 'Other').lower()}"
            st.markdown(f"""
                <div class="event-card">
                    <div class="year-avatar">
                        {event.get('year', '?')[:4]}
                    </div>
                    <div class="event-content">
                        <p>{event.get('event', 'No event description.')}</p>
                        <div class="event-meta">
                            <span class="category-badge {category_class}">
                                {event.get('category', 'Other')}
                            </span>
                            <span style="margin-left: 0.5rem;">Year: {event.get('year', 'N/A')}</span>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

    # JavaScript for download/email actions.
    # These functions will be called by the <a> tags created above.
    if filtered_events:
        pdf_file = create_pdf(filtered_events, selected_date)
        # To make the PDF download work from JS onclick, you'd typically need a base64 encoded string
        # However, for simplicity and Streamlit's direct download capabilities,
        # we'll use Streamlit's own download_button below the events display,
        # and keep the JS mailto for email.
        with open(pdf_file, "rb") as f:
            pdf_bytes = f.read()
        os.remove(pdf_file) # Clean up the generated PDF file

        st.download_button(
            label="Click to Download PDF (Full Report)",
            data=pdf_bytes,
            file_name=f"Events_{selected_date.strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            key="download_pdf_python_btn",
            help="Download the filtered events as a PDF document."
        )

        mailto_link = send_email_via_mailto(filtered_events, selected_date)
        st.markdown(f"""
            <script>
                // Function to trigger PDF download via JavaScript.
                // Note: Direct in-browser PDF generation from Streamlit is complex via JS.
                // The Python st.download_button is more reliable for direct file download.
                // This JS function is mainly a placeholder to align with the HTML button pattern.
                window.downloadPDF = function() {{
                    alert("Please use the 'Click to Download PDF (Full Report)' button below the events for direct download.");
                }};

                window.sendEmail = function() {{
                    window.open('{mailto_link}', '_blank');
                }};
            </script>
        """, unsafe_allow_html=True)
    else:
        st.markdown("<p style='visibility:hidden;'>No events to download/email</p>", unsafe_allow_html=True)


# --- Main App Execution ---
if __name__ == '__main__':
    init_db()
    # Apply global header styling for the logo and logout button
    st.markdown("""
        <div data-testid="stHeader">
            <div>
                <img src="https://i.postimg.cc/0yVG4bhN/mindfullibrarieswhite-01.png" width="180" style="border-radius: 8px; box-shadow: 1px 1px 3px rgba(0,0,0,0.1); margin-right: auto;"/>
            </div>
            """, unsafe_allow_html=True)
    if st.session_state['logged_in']:
        # This button is explicitly placed in the header div, styled by the CSS
        if st.markdown("""<button onclick="window.streamlit_logout()">Log Out</button>""", unsafe_allow_html=True):
             st.session_state['logged_in'] = False
             st.session_state['username'] = None
             st.rerun()
        st.markdown("""
        </div>
        <script>
            // JavaScript function to trigger logout action in Streamlit
            function streamlit_logout() {
                const logoutButton = window.parent.document.querySelector('button[key="logout_btn"]');
                if (logoutButton) {
                    logoutButton.click();
                } else {
                    console.error("Logout button not found.");
                }
            }
        </script>
        """, unsafe_allow_html=True) # Close the header div and add JS

        main_app()
    else:
        # The main title will be shown for the login page
        st.markdown("<h1 class='main-title'>Discover Your Next Nostalgic Read!</h1>", unsafe_allow_html=True)
        login_page()
