import streamlit as st
import pandas as pd
import gspread
import json
from io import StringIO
from oauth2client.service_account import ServiceAccountCredentials
from collections import Counter
from openai import OpenAI
from fpdf import FPDF
from datetime import datetime

st.set_page_config(page_title="Mindful Libraries", layout="centered")
st.markdown("""
    <style>
    body { background-color: white; }
    .buy-button {
        background-color: orange;
        color: white;
        padding: 0.5em 1em;
        border: none;
        border-radius: 5px;
        text-decoration: none;
        font-weight: bold;
        margin-top: 10px;
        display: inline-block;
    }
    </style>
""", unsafe_allow_html=True)

# --- Google Sheets and OpenAI Initialization ---
try:
    scope = ['https://sheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    service_account_info = json.load(StringIO(st.secrets["GOOGLE_SERVICE_JSON"]))
    creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
    client = gspread.authorize(creds)
    client_ai = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except Exception as e:
    st.error(f"Failed to initialize Google Sheets or OpenAI client. Please check your `st.secrets` configuration. Error: {e}")
    st.stop() # Stop the app if essential services cannot be initialized

@st.cache_data(ttl=3600)
def load_content():
    """Loads content from the 'ContentDB' worksheet and processes tags."""
    try:
        sheet_url = 'https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXJRXcfmxjoj5s'
        sheet = client.open_by_url(sheet_url)
        content_ws = sheet.worksheet('ContentDB')
        df = pd.DataFrame(content_ws.get_all_records())
        # Ensure 'Tags' column exists and handle potential NaN values
        if 'Tags' in df.columns:
            df['tags'] = df['Tags'].apply(lambda x: set(tag.strip().lower() for tag in str(x).split(',') if tag.strip().lower() != 'nostalgia'))
        else:
            df['tags'] = [set() for _ in range(len(df))] # Add an empty set for 'tags' if 'Tags' column is missing
            st.warning(" 'Tags' column not found in 'ContentDB' worksheet. Please ensure it exists.")
        return df
    except Exception as e:
        st.error(f"Failed to load content from Google Sheet. Error: {e}")
        return pd.DataFrame() # Return empty DataFrame on error

content_df = load_content()

if 'book_counter' not in st.session_state:
    st.session_state['book_counter'] = Counter()

# removed `recommended_tags = set()` as it's not used globally and `selected_tags` in session state handles it

def save_user_input(name, jobs, hobbies, decade, selected_topics):
    """Saves user input to the 'Logs' worksheet."""
    try:
        sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXJRXcfmxjoj5s')
        log_ws = sheet.worksheet('Logs')
        log_ws.append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), name, jobs, hobbies, decade, ", ".join(selected_topics)])
    except Exception as e:
        st.warning(f"Failed to save user data. Error: {e}")

def generate_pdf(name, topics, recs):
    """Generates a PDF with reading recommendations."""
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
        # Using multi_cell for potentially long summaries
        pdf.multi_cell(0, 10, txt=f"{r.get('Title', 'N/A')} ({r.get('Type', 'N/A')}): {r.get('Summary', 'N/A')}")
        pdf.ln(2)
    return pdf

# --- Streamlit UI ---
st.image("https://i.postimg.cc/0yVG4bhN/mindfullibrarieswhite-01.png", width=300)
st.title("Personalized Reading Recommendations")

# Admin mode for tag feedback summary
admin_mode = st.sidebar.checkbox("🔍 Show Tag Feedback Summary (Admin)")
if admin_mode:
    try:
        sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXJRXcfmxjoj5s')
        fb_ws = sheet.worksheet('Feedback')
        fb_data = pd.DataFrame(fb_ws.get_all_records())
        tag_scores = {}
        for _, row in fb_data.iterrows():
            # Ensure 'Tags' and 'Feedback' columns exist and are not empty
            tags_str = str(row.get('Tags', '')).strip()
            feedback_str = str(row.get('Feedback', '')).strip().lower()

            if tags_str and feedback_str:
                for tag in tags_str.split(','):
                    tag = tag.strip().lower()
                    if tag: # Ensure tag is not empty after stripping
                        tag_scores[tag] = tag_scores.get(tag, 0) + (1 if 'yes' in feedback_str else -1)
        sorted_scores = sorted(tag_scores.items(), key=lambda x: -x[1])
        st.sidebar.markdown("### 📊 Tag Effectiveness Scores")
        if sorted_scores:
            for tag, score in sorted_scores:
                st.sidebar.write(f"**{tag}**: {score:+d}")
        else:
            st.sidebar.info("No tag feedback data available yet.")
    except Exception as e:
        st.sidebar.warning(f"⚠️ Could not load feedback summary. Error: {e}")

st.write("Answer a few fun questions to get personalized tag suggestions for nostalgic reading material!")

name = st.text_input("Your Name")
jobs = st.text_input("What did you used to do for a living?")
hobbies = st.text_input("What are your hobbies or favorite activities?")
decade = st.text_input("What is your favorite decade or era?")

if 'selected_tags' not in st.session_state:
    st.session_state['selected_tags'] = []
selected_tags = st.session_state['selected_tags']

# Load tag scores for reweighting (from feedback sheet)
feedback_tag_scores = {}
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
                    feedback_tag_scores[tag] = feedback_tag_scores.get(tag, 0) + (1 if 'yes' in feedback_str else -1)
except Exception as e:
    st.info(f"Could not load feedback tag scores. Recommendations will not be reweighted by feedback. Error: {e}")

if st.button("Generate My Tags"):
    if name and (jobs or hobbies or decade):
        with st.spinner("Thinking deeply..."):
            # Ensure content_df is not empty before proceeding
            if not content_df.empty and 'tags' in content_df.columns:
                content_tags_list = sorted(set(tag for tags_set in content_df['tags'] for tag in tags_set))
                prompt = f"""
                    You are an expert librarian and therapist. Your job is to recommend 10 relevant and emotionally resonant tags for nostalgic content using the list below and this person's background.

                    Available tags:
                    {", ".join(content_tags_list)}

                    Person's background:
                    Name: {name}
                    Job: {jobs if jobs else 'Not provided'}
                    Hobbies: {hobbies if hobbies else 'Not provided'}
                    Favorite Decade: {decade if decade else 'Not provided'}

                    Only return 10 comma-separated tags from the list above. Do not include any additional text or formatting.
                """
                try:
                    response = client_ai.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    topic_output = response.choices[0].message.content.strip()
                    st.session_state['selected_tags'] = [t.strip().lower() for t in topic_output.split(',') if t.strip()]
                    st.success("Here are your personalized tags:")
                    st.write(", ".join(selected_tags))
                    save_user_input(name, jobs, hobbies, decade, selected_tags)
                except Exception as e:
                    st.error(f"Failed to generate tags using OpenAI. Please check your API key and try again. Error: {e}")
            else:
                st.warning("Cannot generate tags as content database is empty or 'tags' column is missing.")
    else:
        st.warning("Please enter your name and at least one detail about yourself (job, hobbies, or favorite decade) to generate tags.")

# --- Display Recommendations ---
if selected_tags:
    # Removed DEBUG lines

    search_term = st.text_input("Or, type a topic or interest you'd like us to search for")
    if search_term:
        st.markdown(f"### 🔍 Search Results for '{search_term}'")
        # Ensure 'Title' and 'Summary' columns exist for searching
        results = [
            item for item in content_df.to_dict('records')
            if (item.get('Title', '').lower() and search_term.lower() in item.get('Title', '').lower()) or
               (item.get('Summary
