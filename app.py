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
all_topics = sorted(set(topic.strip() for sublist in content_df['tags'] for topic in sublist))

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
            You are an expert in nostalgic, therapeutic reading engagement for older adults and veterans. Based on this user's background, select 10 meaningful and emotionally resonant topics from the following list:

            Available topics:
            {all_topics}

            Person's background:
            - Job: {jobs}
            - Hobbies: {hobbies}
            - Favorite decade: {decade}

            If the person was a veteran or had a patriotic job, include patriotic or American history topics. If the user mentions faith, include spiritual topics. Focus on what would feel familiar, positive, or reminiscent to them.

            Return just a list of 10 topics, comma-separated.
            """
            try:
                response = client_ai.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}]
                )
                topic_output = response.choices[0].message.content
                selected_topics = [t.strip().lower() for t in topic_output.split(',') if t.strip()]
            except Exception as e:
                st.error("⚠️ Oops! We hit a limit with our AI provider or encountered an error. Please try again later.")
                st.stop()

        st.success("Here are your personalized topics:")
        st.write(", ".join(selected_topics))
        save_user_input(name, jobs, hobbies, decade, selected_topics)

        interest_set = set(selected_topics)
        scored = []
        for _, row in content_df.iterrows():
            tag_score = sum(2 if tag in interest_set else 0.5 for tag in row['tags'])
            total_score = tag_score
            scored.append((row, total_score))

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
