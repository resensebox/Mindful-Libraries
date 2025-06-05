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

# Topics List
all_tags = sorted(set(topic.strip() for sublist in content_df['tags'] for topic in sublist))

# Streamlit UI
st.image("https://i.postimg.cc/0yVG4bhN/mindfullibrarieswhite-01.png", width=300)
st.title("Personalized Reading Recommendations")
st.write("Answer a few fun questions to get personalized tag suggestions for nostalgic reading material!")

name = st.text_input("Your Name")
jobs = st.text_input("What did you used to do for a living?")
hobbies = st.text_input("What are your hobbies or favorite activities?")
decade = st.text_input("What is your favorite decade or era?")
reroll = st.button("🎲 Reroll My Tags")

if st.button("Generate My Tags") or reroll:
    if name and (jobs or hobbies or decade):
        with st.spinner("Thinking deeply..."):
            content_tags_list = sorted(set(tag for tags in content_df['tags'] for tag in tags))
            content_preview = ", ".join(content_tags_list)

            prompt = f"""
            You are an expert librarian and therapist focused on nostalgic reading materials for older adults, veterans, and those living with memory loss.

            You are given a list of available tags from real books and newspapers. Your job is to recommend 10 highly relevant and personalized tags based on the user's background. These tags will be used to score and select reading recommendations.

            DO NOT return book titles. Only use the provided tags.

            Available tags:
            {content_preview}

            User Background:
            - Job: {jobs}
            - Hobbies: {hobbies}
            - Favorite decade: {decade}

            Return only a comma-separated list of 10 existing tags (from above) that best match this user.
            """

            try:
                response = client_ai.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}]
                )
                topic_output = response.choices[0].message.content.strip()

                if "?" in topic_output or len(topic_output.split(',')) < 5:
                    st.warning("The AI needs more information before it can generate useful results.")
                    st.info(topic_output)
                    st.stop()

                selected_tags = [t.strip().lower() for t in topic_output.split(',') if t.strip()]
            except Exception as e:
                st.error("⚠️ AI error occurred.")
                st.stop()

        st.success("Here are your personalized tags:")
        st.write(", ".join(selected_tags))
        save_user_input(name, jobs, hobbies, decade, selected_tags)

        normalized_tags = set(selected_tags)

        scored = []
        for _, row in content_df.iterrows():
            tags = row['tags']
            match_count = len(tags & normalized_tags)
            base_score = match_count * 2

            penalty = st.session_state['book_counter'].get(row['Title'], 0)
            total_score = base_score - penalty

            scored.append((row, total_score))

        sorted_items = sorted(scored, key=lambda x: -x[1])
        top_matches = [item[0] for item in sorted_items if item[1] > 0]

        books = []
        newspapers = []
        seen_titles = set()

        for item in top_matches:
            if item['Title'] in seen_titles:
                continue

            type_lower = item['Type'].lower()
            if type_lower == 'book' and len(books) < 2:
                books.append(item)
                seen_titles.add(item['Title'])
            elif type_lower == 'newspaper' and len(newspapers) < 3:
                newspapers.append(item)
                seen_titles.add(item['Title'])

            if len(books) >= 2 and len(newspapers) >= 3:
                break

        # Fallback
        for item in sorted_items:
            if item[0]['Title'] in seen_titles:
                continue
            type_lower = item[0]['Type'].lower()
            if type_lower == 'book' and len(books) < 2:
                books.append(item[0])
                seen_titles.add(item[0]['Title'])
            elif type_lower == 'newspaper' and len(newspapers) < 3:
                newspapers.append(item[0])
                seen_titles.add(item[0]['Title'])
            if len(books) >= 2 and len(newspapers) >= 3:
                break

        unique_matches = books + newspapers

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

            if st.download_button("📄 Download My PDF", data=generate_pdf(name, selected_tags, unique_matches).output(dest='S').encode('latin-1'), file_name=f"{name}_recommendations.pdf"):
                st.success("PDF ready!")

        # ✅ Related Book Carousel
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
                    if book.get('Image', '').startswith("http"):
                        st.image(book['Image'], width=120)
                    st.caption(book['Title'])
        else:
            st.markdown("_No other related books found._")

    else:
        st.warning("Please enter your name and at least one answer to the questions above.")
