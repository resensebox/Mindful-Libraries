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
sheet_url = 'https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXJRXcfmxjoj5s'
sheet = client.open_by_url(sheet_url)
content_ws = sheet.worksheet('ContentDB')
content_df = pd.DataFrame(content_ws.get_all_records())
content_df['tags'] = content_df['Tags'].apply(lambda x: set(tag.strip().lower() for tag in str(x).split(',')))

# Define comprehensive topic categories
categories = {
    "Nature & Outdoors": [...],  # Unchanged for brevity
    "Crafts & Hobbies": [...],  # Unchanged for brevity
    "Food & Cooking": [...],  # Unchanged for brevity
    "Faith & Reflection": [...],  # Unchanged for brevity
    "History & Culture": [...],  # Unchanged for brevity
    "Family & Community": [...],  # Unchanged for brevity
    "Nostalgia & Reminiscence": [...],  # Unchanged for brevity
    "Seasons & Holidays": [...],  # Unchanged for brevity
    "Science & Learning": [...],  # Unchanged for brevity
    "Entertainment: Performing Arts & Music": ["Ballet", "Charlie Chaplin", "Dance", "Dancing", "Elvis", "Elvis Presley", "Entertainment", "Hollywood Stars", "James Dean", "James Stewart", "Lawrence Welk", "Media & Entertainment", "Michael Jackson", "Music", "Singing", "Songs", "Sound Of Music", "Theater"],
    "Entertainment: Games & Sports": ["Baseball", "Basketball", "Board Games", "Celebrities", "Days Of Our Lives", "Film", "Movies", "Rollerskating", "Sports", "TV", "Wheel Of Fortune"]
}

# Streamlit App UI
st.title("📰 Personalized Reading Recommendations")
st.write("Select a category and choose **4 topics** below to receive custom reading material suggestions!")

name = st.text_input("Your Name")
selected_category = st.selectbox("Choose a Category", list(categories.keys()))
selected_topics = st.multiselect("Now choose exactly 4 topics from that category:", categories[selected_category])

if st.button("Get Recommendations"):
    if name and len(selected_topics) == 4:
        interest_set = set(tag.strip().lower() for tag in selected_topics)
        scored = []
        for _, row in content_df.iterrows():
            score = len(interest_set.intersection(row['tags']))
            scored.append((row, score))

        sorted_items = sorted(scored, key=lambda x: -x[1])
        top_matches = [item[0] for item in sorted_items if item[1] > 0]

        # Guarantee at least one Book and one Newspaper
        book = next((item for item in top_matches if item['Type'].lower() == 'book'), None)
        newspaper = next((item for item in top_matches if item['Type'].lower() == 'newspaper'), None)

        unique_matches = []
        if book is not None:
            unique_matches.append(book)
        if newspaper is not None and (book is None or newspaper['Title'] != book['Title']):
            unique_matches.append(newspaper)

        for item in top_matches:
            if item['Title'] not in [m['Title'] for m in unique_matches] and len(unique_matches) < 3:
                unique_matches.append(item)

        st.subheader(f"📚 Recommendations for {name}")
        if unique_matches:
            for item in unique_matches:
                st.markdown(f"- **{item['Title']}** ({item['Type']})")
                st.markdown(f"  - {item['Summary']}")
        else:
            st.info("We didn't find any strong matches, but stay tuned for future updates!")
    elif len(selected_topics) != 4:
        st.warning("Please select exactly 4 interests from the list.")
    else:
        st.warning("Please enter your name and select 4 interests.")
