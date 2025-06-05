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

def save_user_input(name, jobs, hobbies, faith, decade, selected_topics):
    try:
        sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXJRXcfmxjoj5s')
        log_ws = sheet.worksheet('Logs')
        log_ws.append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), name, jobs, hobbies, faith, decade, ", ".join(selected_topics)])
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
faith = st.text_input("Do you have a faith background (e.g. Christian, Jewish, None)?")
decade = st.text_input("What is your favorite decade or era?")
reroll = st.button("🎲 Reroll My Topics")

if st.button("Generate My Topics") or reroll:
    if name and (jobs or hobbies or decade):
        with st.spinner("Thinking deeply..."):
            # Prepare content summary for AI to scan
            content_preview = "\n".join([
                f"- {row['Title']} ({row['Type']}): tags = {', '.join(row['tags'])}"
                for _, row in content_df.iterrows()
            ])

            prompt = f"""
            You are an expert librarian and therapist focused on nostalgic reading materials for older adults, veterans, and those living with memory loss.

            Your goal is to recommend 10 highly specific and emotionally resonant topics that align with this user's life experiences — especially jobs, hobbies, faith, and favorite decade.

            IMPORTANT: Review the following content library first. These are the only books and newspapers available, and your topics MUST align with what is tagged there so they can be matched directly to real content.

            Content Library:
            {content_preview}

            Examples:
            - If they loved 1960s TV, suggest "Betty White" or "Classic Sitcoms"
            - If they were a nurse, suggest "Healthcare History" or "Red Cross"
            - If the user is Christian, suggest faith-based topics only if tagged

            If you're unsure, ask a follow-up question instead of guessing.

            User Background:
            - Job: {jobs}
            - Hobbies: {hobbies}
            - Faith: {faith}
            - Favorite decade: {decade}

            Return a comma-separated list of 10 topics (only from what can be matched above), OR ask a follow-up question.
            """
            try:
                response = client_ai.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}]
                )
                topic_output = response.choices[0].message.content.strip()

                if "?" in topic_output and len(topic_output.split(',')) < 5:
                    st.warning("The AI needs more information before it can generate accurate topics.")
                    st.info(topic_output)
                    st.stop()

                selected_topics = [t.strip().lower() for t in topic_output.split(',') if t.strip()]
            except Exception as e:
                st.error("⚠️ Oops! We hit a limit with our AI provider or encountered an error. Please try again later.")
                st.stop()

        st.success("Here are your personalized topics:")
        st.write(", ".join(selected_topics))
        save_user_input(name, jobs, hobbies, faith, decade, selected_topics)

        normalized_topics = set(selected_topics)
        topic_aliases = {
            "military": "patriotic",
            "nature": "outdoors",
            "school": "education"
        }
        for alias, actual in topic_aliases.items():
            if alias in normalized_topics:
                normalized_topics.add(actual)

        scored = []
        for _, row in content_df.iterrows():
            tags = row['tags']
            match_count = len(tags & normalized_topics)
            base_score = match_count * 2

            if 'christian' in faith.lower() and 'faith' in tags:
                base_score += 2
            if 'jewish' in faith.lower() and 'jewish' in tags:
                base_score += 2

            penalty = st.session_state['book_counter'].get(row['Title'], 0)
            total_score = base_score - penalty

            scored.append((row, total_score))

        sorted_items = sorted(scored, key=lambda x: -x[1])
        top_matches = [item[0] for item in sorted_items]

        books = []
        newspapers = []
        seen_titles = set()

        for item in top_matches:
            if item['Title'] in seen_titles:
                continue

            tags = item['tags']
            type_lower = item['Type'].lower()

            if any(name in normalized_topics for name in ['betty white', 'lucille ball', 'doris day', 'judy garland']):
                if any(tag in tags for tag in ['famous women', 'hollywood', 'tv shows', 'actresses']):
                    pass

            if type_lower == 'book' and len(books) < 2:
                books.append(item)
                seen_titles.add(item['Title'])
            elif type_lower == 'newspaper' and len(newspapers) < 3:
                newspapers.append(item)
                seen_titles.add(item['Title'])

            if len(books) >= 2 and len(newspapers) >= 3:
                break

        # Fallback: fill if under target
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

            if st.download_button("📄 Download My PDF", data=generate_pdf(name, selected_topics, unique_matches).output(dest='S').encode('latin-1'), file_name=f"{name}_recommendations.pdf"):
                st.success("PDF ready!")
        else:
            st.info("We didn't find any strong matches, but stay tuned for future updates!")
    else:
        st.warning("Please enter your name and at least one answer to the questions above.")
