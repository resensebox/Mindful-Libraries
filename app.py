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

# Expanded topic categories with full list
categories = {
    "Nature & Outdoors": ["Animals", "Animal Watching", "Birdwatching", "Gardening", "Hiking", "Nature", "Outdoors", "Seasons & Holidays", "Wildlife", "Turtles", "Hummingbirds", "Parrots", "Penguins", "Orcas"],
    "Crafts & Hobbies": ["Crocheting", "Painting", "Calligraphy", "Model Kits", "Crafts", "Plate Painting", "Terrarium", "Paper Fish", "Paper Flowers", "Wreath Craft", "Chair Exercises"],
    "Food & Cooking": ["Baking", "Candy Nostalgia", "Chocolate Chip Cookies", "Mac And Cheese", "Cupcakes", "Garlic Bread", "Brownies", "Salted Brownies", "Blueberry Muffins", "Brownie Kiss Cupcakes", "Oatmeal Raisin Cookies"],
    "Faith & Reflection": ["Faith", "Bible", "Spirituality", "Prayer", "Meditation", "Devotion", "Worship", "Reflection", "Quiet Time", "Psalms", "Proverbs", "Shabbat"],
    "History & Culture": ["Native American", "Egyptian Bread", "Roman Empire", "Founding Fathers", "George Washington", "Lewis And Clark", "Cleopatra", "Jfk", "Fdr", "Gandhi", "Stanton", "Women"],
    "Family & Community": ["Family", "Friendships", "Motherhood", "Community", "Togetherness", "Relationships", "Bond", "Care And Support", "Belonging"],
    "Nostalgia & Reminiscence": ["Drive-In Movies", "Childhood", "Retro Games", "Penny Candy", "Nostalgia", "Simpler Times", "Reminiscence & Nostalgia", "Life Before Tv", "Good Times"],
    "Seasons & Holidays": ["Christmas", "Thanksgiving", "Halloween", "Easter", "Valentine’S Day", "Winter", "Autumn", "Spring"],
    "Science & Learning": ["Aviation", "Space Race", "John Muir", "Museums", "Law", "Language", "Literature", "Education", "Nature & Outdoors", "Evolution Of Movies"],
    "Entertainment: Performing Arts & Music": ["Dancing", "Elvis Presley", "Jazzercise", "Singing", "Lawrence Welk", "Sound Of Music", "Music", "Instruments", "Spirituals", "Joyful Sounds"],
    "Entertainment: Games & Sports": ["Board Games", "Baseball", "Basketball", "Trivia", "Wheel Of Fortune", "Sports", "Super Bowl", "Dog Olympics", "Games"]
}

# Streamlit App UI
st.title("📰 Personalized Reading Recommendations")
st.write("Select categories and choose **at least 4 topics** total to receive custom reading material suggestions!")

name = st.text_input("Your Name")
college = st.text_input("College Chapter (Optional)")
selected_categories = st.multiselect("Choose 1 or more Categories", list(categories.keys()))

# Gather all topics from selected categories
selected_topics_pool = [topic for cat in selected_categories for topic in categories[cat]]
selected_topics = st.multiselect("Now choose at least 4 topics from your selected categories:", selected_topics_pool)

if st.button("Get Recommendations"):
    if name and len(selected_topics) >= 4:
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

            book_titles = [item['Title'] for item in unique_matches if item['Type'].lower() == 'book']
            st.session_state['book_counter'].update(book_titles)

            st.markdown("### 📈 Book Recommendation Count")
            for title, count in st.session_state['book_counter'].items():
                st.markdown(f"- {title}: {count} times")

            log_to_google_sheet(name, college, selected_topics, [item['Title'] for item in unique_matches])
        else:
            st.info("We didn't find any strong matches, but stay tuned for future updates!")
    elif len(selected_topics) < 4:
        st.warning("Please select at least 4 interests from the list.")
    else:
        st.warning("Please enter your name and select at least 4 in
