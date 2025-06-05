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

scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
service_account_info = json.load(StringIO(st.secrets["GOOGLE_SERVICE_JSON"]))
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)
client_ai = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

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
    pdf.cell(200, 10, txt="Top 10 Personalized Tags:", ln=True)
    for topic in topics:
        pdf.cell(200, 10, txt=f"- {topic}", ln=True)
    pdf.ln(10)
    pdf.cell(200, 10, txt="Recommended Reads:", ln=True)
    for r in recs:
        pdf.multi_cell(0, 10, txt=f"{r['Title']} ({r['Type']}): {r['Summary']}")
        pdf.ln(2)
    return pdf

all_tags = sorted(set(topic.strip() for sublist in content_df['tags'] for topic in sublist))

st.image("https://i.postimg.cc/0yVG4bhN/mindfullibrarieswhite-01.png", width=300)
st.title("Personalized Reading Recommendations")
st.write("Answer a few fun questions to get personalized tag suggestions for nostalgic reading material!")

name = st.text_input("Your Name")
jobs = st.text_input("What did you used to do for a living?")
hobbies = st.text_input("What are your hobbies or favorite activities?")
decade = st.text_input("What is your favorite decade or era?")

# Initialize selected_tags to avoid NameError
selected_tags = []

if st.button("Generate My Tags"):
    if name and (jobs or hobbies or decade):
        with st.spinner("Thinking deeply..."):
            content_tags_list = sorted(set(tag for tags in content_df['tags'] for tag in tags))
            prompt = f"""
                You are an expert librarian and therapist. Your job is to recommend 10 relevant and emotionally resonant tags for nostalgic content using the list below and this person's background.

                Available tags:
                {", ".join(content_tags_list)}

                Person's background:
                Job: {jobs}
                Hobbies: {hobbies}
                Favorite Decade: {decade}

                Only return 10 comma-separated tags from the list above.
            """
            response = client_ai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            topic_output = response.choices[0].message.content.strip()
            selected_tags = [t.strip().lower() for t in topic_output.split(',') if t.strip()]
            st.success("Here are your personalized tags:")
            st.write(", ".join(selected_tags))
            save_user_input(name, jobs, hobbies, decade, selected_tags)

tone_preferences = st.multiselect(
    "What kind of stories do you enjoy most?",
    ["Heartwarming", "Funny", "Historical", "Adventurous", "Inspirational", "Surprising"]
)

# Define actor_keywords (was undefined in original code)
actor_keywords = {
    "1940s": ["humphrey bogart", "ingrid bergman", "frank sinatra"],
    "1950s": ["marilyn monroe", "elvis presley", "james dean"],
    "1960s": ["audrey hepburn", "sidney poitier", "the beatles"],
    "1970s": ["robert de niro", "meryl streep", "john travolta"],
    "1980s": ["michael j. fox", "madonna", "harrison ford"],
    "1990s": ["leonardo dicaprio", "julia roberts", "brad pitt"]
}

normalized_tags = set(selected_tags)
scored = []

for _, row in content_df.iterrows():
    tags = row['tags']
    match_count = len(tags & normalized_tags)
    base_score = match_count * 2

    summary = row.get('Summary', '').lower()
    title = row.get('Title', '').lower()
    row_type = row['Type'].lower()

    # Generalize summary for scoring with AI assistance
    if row_type == 'newspaper':
        try:
            enhanced_prompt = f"Summarize and generalize this newspaper summary to highlight key themes and topics: {summary}"
            response = client_ai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": enhanced_prompt}]
            )
            summary = response.choices[0].message.content.strip().lower()
        except Exception:
            pass

    tone_boost = sum(2 for tone in tone_preferences if tone.lower() in summary) if row_type == 'book' else 0
    decade_boost = 2 if row_type == 'newspaper' and decade.lower() in summary + title else 0
    historical_boost = sum(1 for kw in ["eisenhower", "fdr", "civil rights", "world war", "apollo", "nixon", "kennedy", "vietnam", "rosa parks"] if kw in summary) if row_type == 'newspaper' else 0

    actor_boost = 0
    for decade_key, actors in actor_keywords.items():
        if decade_key in decade.lower():
            if any(actor in summary for actor in actors):
                actor_boost = 3
                break

    total_score = base_score + tone_boost + decade_boost + historical_boost + actor_boost
    scored.append((row, total_score))

sorted_items = sorted(scored, key=lambda x: -x[1])
top_matches = [item[0] for item in sorted_items if item[1] > 0]

books = []
newspapers = []
seen_titles = set()

for item in top_matches:
    if item['Title'] in seen_titles:
        continue
    if item['Type'].lower() == 'book':
        books.append(item)
    elif item['Type'].lower() == 'newspaper':
        newspapers.append(item)
    seen_titles.add(item['Title'])

books = books[:2]
newspapers = newspapers[:3]
unique_matches = books + newspapers

st.subheader(f"📚 Recommendations for {name}")
if unique_matches:
    for item in unique_matches:
        cols = st.columns([1, 2])
        with cols[0]:
            img_url = None
            if item.get('Image', '').startswith("http"):
                img_url = item['Image']
            elif 'URL' in item and "amazon." in item['URL'] and "/dp/" in item['URL']:
                try:
                    asin = item['URL'].split('/dp/')[-1].split('/')[0].split('?')[0]
                    img_url = f"https://images-na.ssl-images-amazon.com/images/P/{asin}.01._SL250_.jpg"
                except:
                    pass
            if img_url:
                st.image(img_url, width=180)
        with cols[1]:
            st.markdown(f"### {item['Title']} ({item['Type']})")
            st.markdown(f"{item['Summary']}")
            if 'URL' in item and item['URL']:
                st.markdown(f"<a class='buy-button' href='{item['URL']}' target='_blank'>Buy Now</a>", unsafe_allow_html=True)

    if st.download_button("📄 Download My PDF", data=generate_pdf(name, selected_tags, unique_matches).output(dest='S').encode('latin-1'), file_name=f"{name}_recommendations.pdf"):
        st.success("PDF ready!")

    st.markdown("### 📖 You Might Also Like")
    related_books = []
    for _, row in content_df.iterrows():
        if row['Title'] in [b['Title'] for b in unique_matches]:
            continue
        if row['Type'].lower() != 'book':
            continue
        if row['tags'] & normalized_tags:
            related_books.append(row)

    if related_books:
        cols = st.columns(min(5, len(related_books)))
        for i, book in enumerate(related_books[:10]):
            with cols[i % len(cols)]:
                img_url = None
                if book.get('Image', '').startswith("http"):
                    img_url = book['Image']
                elif 'URL' in book and "amazon." in book['URL'] and "/dp/" in book['URL']:
                    try:
                        asin = book['URL'].split('/dp/')[-1].split('/')[0].split('?')[0]
                        img_url = f"https://images-na.ssl-images-amazon.com/images/P/{asin}.01._SL250_.jpg"
                    except:
                        pass
                if img_url:
                    st.image(img_url, width=120)
                st.caption(book['Title'])
    else:
        st.markdown("_No other related books found._")
else:
    st.warning("Please enter your name and at least one answer to the questions above.")
