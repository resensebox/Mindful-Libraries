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

@st.cache_data(ttl=3600)
def load_content():
    sheet_url = 'https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXJRXcfmxjoj5s'
    sheet = client.open_by_url(sheet_url)
    content_ws = sheet.worksheet('ContentDB')
    df = pd.DataFrame(content_ws.get_all_records())
    df['tags'] = df['Tags'].apply(lambda x: set(tag.strip().lower() for tag in str(x).split(',') if tag.strip().lower() != 'nostalgia'))
    return df

content_df = load_content()
if 'book_counter' not in st.session_state:
    st.session_state['book_counter'] = Counter()

recommended_tags = set()

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

st.image("https://i.postimg.cc/0yVG4bhN/mindfullibrarieswhite-01.png", width=300)
st.title("Personalized Reading Recommendations")

admin_mode = st.sidebar.checkbox("🔍 Show Tag Feedback Summary (Admin)")
if admin_mode:
    try:
        sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXJRXcfmxjoj5s')
        fb_ws = sheet.worksheet('Feedback')
        fb_data = pd.DataFrame(fb_ws.get_all_records())
        tag_scores = {}
        for _, row in fb_data.iterrows():
            for tag in str(row['Tags']).split(','):
                tag = tag.strip().lower()
                tag_scores[tag] = tag_scores.get(tag, 0) + (1 if 'yes' in row['Feedback'].lower() else -1)
        sorted_scores = sorted(tag_scores.items(), key=lambda x: -x[1])
        st.sidebar.markdown("### 📊 Tag Effectiveness Scores")
        for tag, score in sorted_scores:
            st.sidebar.write(f"**{tag}**: {score:+d}")
    except Exception as e:
        st.sidebar.warning("⚠️ Could not load feedback summary.")
st.write("Answer a few fun questions to get personalized tag suggestions for nostalgic reading material!")

name = st.text_input("Your Name")
jobs = st.text_input("What did you used to do for a living?")
hobbies = st.text_input("What are your hobbies or favorite activities?")
decade = st.text_input("What is your favorite decade or era?")
if 'selected_tags' not in st.session_state:
    st.session_state['selected_tags'] = []
selected_tags = st.session_state['selected_tags']

# Load tag scores for reweighting
feedback_tag_scores = {}
try:
    sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXJRXcfmxjoj5s')
    fb_ws = sheet.worksheet('Feedback')
    fb_data = pd.DataFrame(fb_ws.get_all_records())
    for _, row in fb_data.iterrows():
        for tag in str(row['Tags']).split(','):
            tag = tag.strip().lower()
            feedback_tag_scores[tag] = feedback_tag_scores.get(tag, 0) + (1 if 'yes' in row['Feedback'].lower() else -1)
except Exception:
    pass

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
            st.session_state['selected_tags'] = [t.strip().lower() for t in topic_output.split(',') if t.strip()]
            st.success("Here are your personalized tags:")
            st.write(", ".join(selected_tags))
            save_user_input(name, jobs, hobbies, decade, selected_tags)

if selected_tags:
    used_tags = set()
    books = []
    magazines = []
    matched_items = []
    shuffled_df = content_df.sample(frac=1, random_state=42)
    for item in shuffled_df.itertuples(index=False):
        tag_matches = set(item.tags) & set(selected_tags)
        tag_weight = sum(feedback_tag_scores.get(tag, 0) for tag in tag_matches)
        if item.Type.lower() == 'newspaper' and len(tag_matches) >= 3 and tag_weight >= -1:
                magazines.append(item._asdict())
                used_tags.update(tag_matches)
        elif item.Type.lower() == 'book' and len(tag_matches) >= 3 and tag_weight >= 0:
            books.append(item._asdict())
            used_tags.update(tag_matches)
        elif tag_matches:
            matched_items.append(item._asdict())

    matched_titles = [item['Title'] for item in matched_items]
    related_books = [
    item for item in content_df.to_dict('records')
    if item['Title'] not in matched_titles and
       item['Type'].lower() == 'book' and
       set(item['tags']) & set(selected_tags)
]

    if books or magazines:
    st.subheader(f"📚 Recommendations for {name}")
    for item in books[:3] + magazines[:3]:
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
            st.markdown(item['Summary'])
            st.markdown(f"_Why this was recommended: matched tags — {', '.join(set(item['tags']) & set(selected_tags))}_")
            feedback = st.radio(f"Was this recommendation helpful?", ["Select an option", "✅ Yes", "❌ No"], index=0, key=f"feedback_{item['Title']}")
            if feedback != "Select an option" and not st.session_state.get(f"feedback_submitted_{item['Title']}", False):
                try:
                    sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXJRXcfmxjoj5s')
                    feedback_ws = sheet.worksheet('Feedback')
                    feedback_ws.append_row([
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        name,
                        item['Title'],
                        item['Type'],
                        feedback,
                        ", ".join(item['tags'])
                    ])
                    st.session_state[f"feedback_submitted_{item['Title']}"] = True
                    st.success("✅ Feedback submitted!")
                except Exception as e:
                    st.warning("⚠️ Failed to save feedback.")
            if 'URL' in item and item['URL']:
                st.markdown(f"<a class='buy-button' href='{item['URL']}' target='_blank'>Buy Now</a>", unsafe_allow_html=True)

    if related_books:
        st.markdown("### 📖 You Might Also Like")
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
