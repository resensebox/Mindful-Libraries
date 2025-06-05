import streamlit as st
import pandas as pd
import gspread
import json
from io import StringIO
from oauth2client.service_account import ServiceAccountCredentials

# Google Sheets Setup (using secrets)
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
service_account_info = json.load(StringIO(st.secrets["GOOGLE_SERVICE_JSON"]))
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)

# Load content from Google Sheet
sheet_url = 'https://docs.google.com/spreadsheets/d/892416667'
sheet = client.open_by_url(sheet_url)
content_ws = sheet.worksheet('ContentDB')
content_df = pd.DataFrame(content_ws.get_all_records())
content_df['tags'] = content_df['Tags'].apply(lambda x: set(str(x).lower().split(',')))

# Streamlit App UI
st.title("📰 Personalized Reading Recommendations")
st.write("Enter your interests below to receive custom reading material suggestions!")

name = st.text_input("Your Name")
interests_input = st.text_area("Enter your interests (comma-separated)", "")

if st.button("Get Recommendations"):
    if name and interests_input:
        interest_set = set(tag.strip().lower() for tag in interests_input.split(","))
        scored = []
        for _, row in content_df.iterrows():
            score = len(interest_set & row['tags'])
            if score > 0:
                scored.append((row, score))
        sorted_items = sorted(scored, key=lambda x: -x[1])
        top_matches = [item[0] for item in sorted_items[:3]]

        st.subheader(f"📚 Recommendations for {name}")
        for item in top_matches:
            st.markdown(f"**{item['Title']}** ({item['Type']})  ")
            st.markdown(f"[Read Here]({item['URL']})")
    else:
        st.warning("Please enter both your name and interests.")

