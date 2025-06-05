import streamlit as st
import pandas as pd
import gspread
import json
from io import StringIO
from oauth2client.service_account import ServiceAccountCredentials
import requests
from collections import Counter

# Google Sheets Setup (using secrets)
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
service_account_info = json.load(StringIO(st.secrets["GOOGLE_SERVICE_JSON"]))
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)

# Load content from Google Sheet with caching
@st.cache_data(ttl=300)
def load_content():
    sheet_url = 'https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXJRXcfmxjoj5s'
    sheet = client.open_by_url(sheet_url)
    content_ws = sheet.worksheet('ContentDB')
    df = pd.DataFrame(content_ws.get_all_records())
    df['tags'] = df['Tags'].apply(lambda x: set(tag.strip().lower() for tag in str(x).split(',')))
    return df

content_df = load_content()

# Track book recommendation counts
if 'book_counter' not in st.session_state:
    st.session_state['book_counter'] = Counter()
if 'selected_topics' not in st.session_state:
    st.session_state['selected_topics'] = []

# Logging function using Google Apps Script
def log_to_google_sheet(name, college, topics, recommendations):
    url = "https://script.google.com/macros/s/AKfycbyEjfmz_ngHiw4nTQ08oWfa83EOln2-ZASqqggtVDln2s9PROkXR3-Ejh5m2_WUzQoU/exec"
    payload = {
        "name": name,
        "college": college,
        "topics": topics,
        "recommendations": recommendations
    }
    try:
        response = requests.post(url, json=payload)
        st.write("Log status:", response.status_code)
        st.write("Log response:", response.text)
    except Exception as e:
        st.error(f"Logging failed: {e}")

# Streamlit UI
st.title("📰 Personalized Reading Recommendations")
st.write("Select **at least 4 topics** to receive custom reading material suggestions!")

with st.form("recommendation_form"):
    name = st.text_input("Your Name")
    college = st.text_input("College Chapter (Optional)")
    selected_topics = st.multiselect(
        "Choose at least 4 topics:",
        sorted(list(set(tag for tags in content_df['tags'] for tag in tags))),
        default=st.session_state['selected_topics']
    )

    submitted = st.form_submit_button("Get Recommendations")

if submitted:
    st.session_state['selected_topics'] = selected_topics

    if name and len(selected_topics) >= 4:
        interest_set = set(tag.strip().lower() for tag in selected_topics)
        scored = [(row, len(interest_set.intersection(row['tags']))) for _, row in content_df.iterrows()]
        sorted_items = sorted(scored, key=lambda x: -x[1])
        top_matches = [item[0] for item in sorted_items if item[1] > 0]

        book = next((item for item in top_matches if item['Type'].lower() == 'book'), None)
        newspaper = next((item for item in top_matches if item['Type'].lower() == 'newspaper'), None)

        unique_matches = []
        if book:
            unique_matches.append(book)
        if newspaper and (not book or newspaper['Title'] != book['Title']):
            unique_matches.append(newspaper)

        for item in top_matches:
            if item['Title'] not in [m['Title'] for m in unique_matches] and len(unique_matches) < 3:
                unique_matches.append(item)

        st.subheader(f"📚 Recommendations for {name}")
        for item in unique_matches:
            st.markdown(f"- **{item['Title']}** ({item['Type']})")
            st.markdown(f"  - {item['Summary']}")

        book_titles = [item['Title'] for item in unique_matches if item['Type'].lower() == 'book']
        st.session_state['book_counter'].update(book_titles)

        st.markdown("### 📈 Book Recommendation Count")
        for title, count in st.session_state['book_counter'].items():
            st.markdown(f"- {title}: {count} times")

        log_to_google_sheet(name, college, selected_topics, [item['Title'] for item in unique_matches])
    elif len(selected_topics) < 4:
        st.warning("Please select at least 4 interests from the list.")
    else:
        st.warning("Please enter your name and select at least 4 interests.")
