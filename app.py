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

# Streamlit and styling setup
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

# Google Sheets authorization
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
service_account_info = json.load(StringIO(st.secrets["GOOGLE_SERVICE_JSON"]))
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)

# OpenAI client setup
client_ai = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Load content
@st.cache_data(ttl=300)
def load_content():
    sheet_url = 'https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXJRXcfmxjoj5s'
    sheet = client.open_by_url(sheet_url)
    content_ws = sheet.worksheet('ContentDB')
    df = pd.DataFrame(content_ws.get_all_records())
    df['tags'] = df['Tags'].apply(lambda x: set(tag.strip().lower() for tag in str(x).split(',')))
    return df

content_df = load_content()

if 'book_counter' not in st.session_state:
    st.session_state['book_counter'] = Counter()

def save_user_input(name, jobs, hobbies, decade, selected_topics):
    try:
        sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXJRXcfmxjoj5s')
        log_ws = sheet.worksheet('Logs')
        log_ws.append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), name, jobs, hobbies, decade, ", ".join(selected_topics)])
    except Exception:
        st.warning("Failed to save user data.")

def generate_pdf(name, topics, recs):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=14)
    pdf.cell(200, 10, txt=f"Reading Recommendations for {name}", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Top 10 Personalized Topics:", ln=True)
    for topic in topics:
        pdf.cell(200, 10, txt=f"- {topic}", ln=True)
    pdf.ln(10)
    pdf.cell(200, 10, txt="Recommended Reads:", ln=True)
    for r in recs:
        pdf.multi_cell(0, 10, txt=f"{r['Title']} ({r['Type']}): {r['Summary']}")
        pdf.ln(2)
    return pdf

# Topics List
all_topics = [topic for sublist in {
    "Nature & Outdoors": ["Animals", "Birdwatching", "Gardening", "Hiking", "Nature", "Outdoors", "Wildlife", "Turtles", "Hummingbirds", "Parrots", "Penguins", "Orcas", "Fishing", "Camping"],
    "Crafts & Hobbies": ["Crocheting", "Painting", "Calligraphy", "Model Kits", "Crafts", "Knitting", "Woodworking", "Origami", "Embroidery", "Scrapbooking", "Terrarium", "Paper Fish", "Paper Flowers", "Wreath Craft", "Chair Exercises"],
    "Food & Cooking": ["Baking", "Candy Nostalgia", "Chocolate Chip Cookies", "Mac And Cheese", "Cupcakes", "Garlic Bread", "Brownies", "Salted Brownies", "Blueberry Muffins", "Brownie Kiss Cupcakes", "Oatmeal Raisin Cookies", "Vintage Recipes", "Sunday Dinners"],
    "Faith & Reflection": ["Faith", "Bible", "Spirituality", "Prayer", "Meditation", "Devotion", "Worship", "Reflection", "Quiet Time", "Psalms", "Proverbs", "Shabbat", "Gratitude"],
    "History & Culture": ["Native American", "Egyptian Bread", "Roman Empire", "Founding Fathers", "George Washington", "Lewis And Clark", "Cleopatra", "JFK", "FDR", "Gandhi", "Stanton", "Women", "Civil Rights", "Presidents", "Historic Landmarks"],
    "Family & Community": ["Family", "Friendships", "Motherhood", "Community", "Togetherness", "Relationships", "Bond", "Care And Support", "Belonging", "Grandparenting", "Reunions", "Storytelling"],
    "Nostalgia & Reminiscence": ["Drive-In Movies", "Childhood", "Retro Games", "Penny Candy", "Nostalgia", "Simpler Times", "Reminiscence & Nostalgia", "Life Before TV", "Good Times", "Old-Fashioned Fun", "Radio Shows"],
    "Seasons & Holidays": ["Christmas", "Thanksgiving", "Halloween", "Easter", "Valentine's Day", "Winter", "Autumn", "Spring", "Summer", "New Year", "Fourth of July"],
    "Science & Learning": ["Aviation", "Space Race", "John Muir", "Museums", "Law", "Language", "Literature", "Education", "Nature & Outdoors", "Evolution Of Movies", "Inventions", "Dinosaurs"],
    "Entertainment: Performing Arts & Music": ["Dancing", "Elvis Presley", "Jazzercise", "Singing", "Lawrence Welk", "Sound Of Music", "Music", "Instruments", "Spirituals", "Joyful Sounds", "Classical Music", "Vaudeville"],
    "Entertainment: Games & Sports": ["Board Games", "Baseball", "Basketball", "Trivia", "Wheel Of Fortune", "Sports", "Super Bowl", "Dog Olympics", "Games", "Card Games", "Bowling", "Carnival Games"]
}.values() for topic in sublist]

# Streamlit UI
st.image("https://i.postimg.cc/0yVG4bhN/mindfullibrarieswhite-01.png", width=300)
st.title("Personalized Reading Recommendations")
st.write("Answer a few fun questions to get personalized topic suggestions for nostalgic reading material!")

name = st.text_input("Your Name")
jobs = st.text_input("What did you used to do for a living?")
hobbies = st.text_input("What are your hobbies or favorite activities?")
decade = st.text_input("What is your favorite decade or era?")
reroll = st.button("🎲 Reroll My Topics")

if st.button("Generate My Topics") or reroll:
    if name and (jobs or hobbies or decade):
        with st.spinner("Thinking deeply..."):
            prompt = f"""
            Based on this person's background:
            - Past job: {jobs}
            - Hobbies: {hobbies}
            - Favorite decade: {decade}
            Suggest 10 relevant and engaging topics from the following list:
            {all_topics}
            Just return the list of 10 topics, comma-separated.
            """
            response = client_ai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            topic_output = response.choices[0].message.content
            selected_topics = [t.strip() for t in topic_output.split(',') if t.strip()]

        st.success("Here are your personalized topics:")
        st.write(", ".join(selected_topics))
        save_user_input(name, jobs, hobbies, decade, selected_topics)

        interest_set = set(tag.strip().lower() for tag in selected_topics)
        scored = []
        for _, row in content_df.iterrows():
            score = len(interest_set.intersection(row['tags']))
            scored.append((row, score))

        sorted_items = sorted(scored, key=lambda x: -x[1])
        top_matches = [item[0] for item in sorted_items if item[1] > 0]

        unique_matches = []
        seen_titles = set()
        for item in top_matches:
            if item['Title'] not in seen_titles:
                unique_matches.append(item)
                seen_titles.add(item['Title'])
            if len(unique_matches) == 3:
                break

        st.subheader(f"📚 Recommendations for {name}")
        if unique_matches:
            for item in unique_matches:
                cols = st.columns([1, 2])
                with cols[0]:
                    if 'Image' in item and item['Image'] and item['Image'].startswith("http"):
                        st.image(item['Image'], width=180)
                    elif 'URL' in item and "amazon." in item['URL'] and "/dp/" in item['URL']:
                        try:
                            asin = item['URL'].split('/dp/')[-1].split('/')[0].split('?')[0]
                            image_url = f"https://images-na.ssl-images-amazon.com/images/P/{asin}.01._SL250_.jpg"
                            st.image(image_url, width=180)
                        except Exception:
                            pass

                with cols[1]:
                    st.markdown(f"### {item['Title']} ({item['Type']})")
                    st.markdown(f"{item['Summary']}")
                    if 'URL' in item and item['URL']:
                        st.markdown(f"<a class='buy-button' href='{item['URL']}' target='_blank'>Buy Now</a>", unsafe_allow_html=True)

            book_titles = [item['Title'] for item in unique_matches if item['Type'].lower() == 'book']
            st.session_state['book_counter'].update(book_titles)

            st.markdown("### 📊 Book Recommendation Count")
            for title, count in st.session_state['book_counter'].items():
                st.markdown(f"- {title}: {count} times")

            if st.download_button("📄 Download My PDF", data=generate_pdf(name, selected_topics, unique_matches).output(dest='S').encode('latin-1'), file_name=f"{name}_recommendations.pdf"):
                st.success("PDF ready!")
        else:
            st.info("We didn't find any strong matches, but stay tuned for future updates!")
    else:
        st.warning("Please enter your name and at least one answer to the questions above.")
