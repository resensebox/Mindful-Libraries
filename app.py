import streamlit as st
import pandas as pd
import gspread
import json
from io import StringIO
from oauth2client.service_account import ServiceAccountCredentials
from collections import Counter
from openai import OpenAI # Import the OpenAI class from the library
from fpdf import FPDF
from datetime import datetime

st.set_option('client.showErrorDetails', True)

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

st.write("✅ App is running")
st.write("🔍 Secrets found:", list(st.secrets.keys()))

# --- Google Sheets and OpenAI Initialization ---
try:
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    st.write("🔁 Initializing services...")

    if "GOOGLE_SERVICE_JSON" not in st.secrets:
        st.error("❌ GOOGLE_SERVICE_JSON is missing from secrets.")
        st.stop()

    service_account_info = dict(st.secrets["GOOGLE_SERVICE_JSON"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
    client = gspread.authorize(creds)

    if "OPENAI_API_KEY" not in st.secrets:
        st.error("❌ OPENAI_API_KEY is missing from secrets.")
        st.stop()

    # FIX: Initialize the OpenAI client correctly for the new library
    client_ai = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    st.write("✅ Successfully initialized Google Sheets and OpenAI clients")

except Exception as e:
    st.error(f"Failed to initialize Google Sheets or OpenAI client. Please check your `st.secrets` configuration. Error: {e}")
    st.stop()

# You no longer need this `generate_tags_with_openai` function since you're calling the client directly
# However, if you wanted to keep it, you'd pass `client_ai` into it.
# For simplicity, I'm removing it here and using the direct call where it's currently implemented.
# def generate_tags_with_openai(prompt):
#     try:
#         response = client_ai.chat.completions.create(
#             model="gpt-3.5-turbo",
#             messages=[{"role": "user", "content": prompt}]
#         )
#         return response.choices[0].message.content # Corrected access
#     except Exception as e:
#         st.error(f"Failed to generate tags using OpenAI. Error: {e}")
#         return ""


@st.cache_data(ttl=3600)
def load_content():
    try:
        sheet_url = 'https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXJRXcfmxjoj5s'
        sheet = client.open_by_url(sheet_url)
        content_ws = sheet.worksheet('ContentDB')
        df = pd.DataFrame(content_ws.get_all_records())
        if 'Tags' in df.columns:
            df['tags'] = df['Tags'].apply(lambda x: set(tag.strip().lower() for tag in str(x).split(',') if tag.strip().lower() != 'nostalgia'))
        else:
            df['tags'] = [set() for _ in range(len(df))]
            st.warning(" 'Tags' column not found in 'ContentDB' worksheet. Please ensure it exists.")
        return df
    except Exception as e:
        st.error(f"Failed to load content from Google Sheet. Error: {e}")
        return pd.DataFrame()

content_df = load_content()

if 'book_counter' not in st.session_state:
    st.session_state['book_counter'] = Counter()

def save_user_input(name, jobs, hobbies, decade, selected_topics):
    try:
        sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXJRXcfmxjoj5s')
        log_ws = sheet.worksheet('Logs')
        log_ws.append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), name, jobs, hobbies, decade, ", ".join(selected_topics)])
    except Exception as e:
        st.warning(f"Failed to save user data. Error: {e}")

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
        pdf.multi_cell(0, 10, txt=f"{r.get('Title', 'N/A')} ({r.get('Type', 'N/A')}): {r.get('Summary', 'N/A')}")
        pdf.ln(2)
    return pdf

# The rest of your code remains unchanged (Streamlit UI, tag generation, recommendations, etc.)

# --- Streamlit UI ---
st.image("https://i.postimg.cc/0yVG4bhN/mindfullibrarieswhite-01.png", width=300)
st.title("Personalized Reading Recommendations")

# Admin mode for tag feedback summary
admin_mode = st.sidebar.checkbox("🔍 Show Tag Feedback Summary (Admin)")
if admin_mode:
    try:
        sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXJRXcfmxjoj5s')
        fb_ws = sheet.worksheet('Feedback')
        fb_data = pd.DataFrame(fb_ws.get_all_records())
        tag_scores = {}
        for _, row in fb_data.iterrows():
            # Ensure 'Tags' and 'Feedback' columns exist and are not empty
            tags_str = str(row.get('Tags', '')).strip()
            feedback_str = str(row.get('Feedback', '')).strip().lower()

            if tags_str and feedback_str:
                for tag in tags_str.split(','):
                    tag = tag.strip().lower()
                    if tag: # Ensure tag is not empty after stripping
                        tag_scores[tag] = tag_scores.get(tag, 0) + (1 if 'yes' in feedback_str else -1)
        sorted_scores = sorted(tag_scores.items(), key=lambda x: -x[1])
        st.sidebar.markdown("### 📊 Tag Effectiveness Scores")
        if sorted_scores:
            for tag, score in sorted_scores:
                st.sidebar.write(f"**{tag}**: {score:+d}")
        else:
            st.sidebar.info("No tag feedback data available yet.")
    except Exception as e:
        st.sidebar.warning(f"⚠️ Could not load feedback summary. Error: {e}")

st.write("Answer a few fun questions to get personalized tag suggestions for nostalgic reading material!")

name = st.text_input("Your Name")
jobs = st.text_input("What did you used to do for a living?")
hobbies = st.text_input("What are your hobbies or favorite activities?")
decade = st.text_input("What is your favorite decade or era?")

if 'selected_tags' not in st.session_state:
    st.session_state['selected_tags'] = []
selected_tags = st.session_state['selected_tags']

# Load tag scores for reweighting (from feedback sheet)
feedback_tag_scores = {}
try:
    sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXJRXcfmxjoj5s')
    fb_ws = sheet.worksheet('Feedback')
    fb_data = pd.DataFrame(fb_ws.get_all_records())
    for _, row in fb_data.iterrows():
        tags_str = str(row.get('Tags', '')).strip()
        feedback_str = str(row.get('Feedback', '')).strip().lower()

        if tags_str and feedback_str:
            for tag in tags_str.split(','):
                tag = tag.strip().lower()
                if tag:
                    feedback_tag_scores[tag] = feedback_tag_scores.get(tag, 0) + (1 if 'yes' in feedback_str else -1)
except Exception as e:
    st.info(f"Could not load feedback tag scores. Recommendations will not be reweighted by feedback. Error: {e}")

if st.button("Generate My Tags"):
    if name and (jobs or hobbies or decade):
        with st.spinner("Thinking deeply..."):
            # Ensure content_df is not empty before proceeding
            if not content_df.empty and 'tags' in content_df.columns:
                content_tags_list = sorted(set(tag for tags_set in content_df['tags'] for tag in tags_set))
                prompt = f"""
                    You are an expert librarian and therapist. Your job is to recommend 10 relevant and emotionally resonant tags for nostalgic content using the list below and this person's background.

                    Available tags:
                    {", ".join(content_tags_list)}

                    Person's background:
                    Name: {name}
                    Job: {jobs if jobs else 'Not provided'}
                    Hobbies: {hobbies if hobbies else 'Not provided'}
                    Favorite Decade: {decade if decade else 'Not provided'}

                    Only return 10 comma-separated tags from the list above. Do not include any additional text or formatting.
                """
                try:
                    # FIX: Use the 'client_ai' object initialized earlier
                    response = client_ai.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    # FIX: Correctly access the content and call .strip()
                    topic_output = response.choices[0].message.content.strip()
                    st.session_state['selected_tags'] = [t.strip().lower() for t in topic_output.split(',') if t.strip()]
                    st.success("Here are your personalized tags:")
                    st.write(", ".join(selected_tags))
                    save_user_input(name, jobs, hobbies, decade, selected_tags)
                except Exception as e:
                    st.error(f"Failed to generate tags using OpenAI. Please check your API key and try again. Error: {e}")
            else:
                st.warning("Cannot generate tags as content database is empty or 'tags' column is missing.")
    else:
        st.warning("Please enter your name and at least one detail about yourself (job, hobbies, or favorite decade) to generate tags.")

# --- Display Recommendations ---
if selected_tags:
    search_term = st.text_input("Or, type a topic or interest you'd like us to search for")
    if search_term:
        st.markdown(f"### 🔍 Search Results for '{search_term}'")
        results = [
            item for item in content_df.to_dict('records')
            if (item.get('Title', '').lower() and search_term.lower() in item.get('Title', '').lower()) or \
               (item.get('Summary', '').lower() and search_term.lower() in item.get('Summary', '').lower()) or \
               any(search_term.lower() in tag for tag in item.get('tags', set()))
        ]
        if results:
            for item in results[:5]: # Display top 5 search results
                st.markdown(f"**{item.get('Title', 'N/A')}** ({item.get('Type', 'N/A')})")
                st.markdown(item.get('Summary', 'N/A'))
                st.markdown(f"_Tags: {', '.join(item.get('tags', set()))}_")
                if 'URL' in item and item['URL']:
                    st.markdown(f"<a class='buy-button' href='{item['URL']}' target='_blank'>Buy Now</a>", unsafe_allow_html=True)
            if len(results) > 5:
                st.info(f"Showing top 5 results. Found {len(results)} total matches for '{search_term}'.")
        else:
            st.info(f"No results found for '{search_term}'.")

    books_candidates = []
    newspapers_candidates = []

    for item in content_df.itertuples(index=False):
        item_tags = getattr(item, 'tags', set())
        item_type = getattr(item, 'Type', '').lower()

        tag_matches = item_tags & set(selected_tags)
        num_matches = len(tag_matches)
        tag_weight = sum(feedback_tag_scores.get(tag, 0) for tag in tag_matches)

        if item_type == 'newspaper' and num_matches >= 1 and tag_weight >= -1:
            newspapers_candidates.append((num_matches, tag_weight, item._asdict()))
        elif item_type == 'book' and num_matches >= 1 and tag_weight >= 0:
            books_candidates.append((num_matches, tag_weight, item._asdict()))

    books_candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    newspapers_candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)

    books = [item_dict for _, _, item_dict in books_candidates[:3]]
    newspapers = [item_dict for _, _, item_dict in newspapers_candidates[:3]]

    primary_recommended_titles = {item.get('Title') for item in books + newspapers if item.get('Title')}

    related_books = []
    all_relevant_tags = set(selected_tags)

    for item in books + newspapers:
        all_relevant_tags.update(item.get('tags', set()))

    temp_related_books_candidates = []
    for item in content_df.to_dict('records'):
        if item.get('Title') not in primary_recommended_titles and item.get('Type', '').lower() == 'book':
            common_tags = set(item.get('tags', set())) & all_relevant_tags
            if len(common_tags) > 0:
                temp_related_books_candidates.append((len(common_tags), item))

    temp_related_books_candidates.sort(key=lambda x: x[0], reverse=True)
    related_books = [book_dict for _, book_dict in temp_related_books_candidates][:10]

    if books or newspapers:
        st.subheader(f"📚 Recommendations for {name}")
        for item in books + newspapers:
            cols = st.columns([1, 2])
            with cols[0]:
                img_url = None
                if item.get('Image', '').startswith("http"):
                    img_url = item['Image']
                elif 'URL' in item and "amazon." in item['URL'] and "/dp/" in item['URL']:
                    try:
                        asin = item['URL'].split('/dp/')[-1].split('/')[0].split('?')[0]
                        img_url = f"https://images-na.ssl-images-amazon.com/images/P/{asin}.01._SL250_.jpg"
                    except IndexError:
                        pass
                if img_url:
                    st.image(img_url, width=180)
            with cols[1]:
                st.markdown(f"### {item.get('Title', 'N/A')} ({item.get('Type', 'N/A')})")
                st.markdown(item.get('Summary', 'N/A'))
                original_tag_matches = set(item.get('tags', set())) & set(selected_tags)
                if original_tag_matches:
                    st.markdown(f"_Why this was recommended: matched tags — {', '.join(original_tag_matches)}_")
                else:
                    st.markdown("_No direct tag matches found for this recommendation._")

                feedback_key = f"feedback_{item.get('Title', 'NoTitle')}_{item.get('Type', 'NoType')}"
                feedback = st.radio(
                    f"Was this recommendation helpful?",
                    ["Select an option", "✅ Yes", "❌ No"],
                    index=0,
                    key=feedback_key
                )
                if feedback != "Select an option" and not st.session_state.get(f"feedback_submitted_{feedback_key}", False):
                    try:
                        sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXJRXcfmxjoj5s')
                        feedback_ws = sheet.worksheet('Feedback')
                        feedback_ws.append_row([
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            name,
                            item.get('Title', 'N/A'),
                            item.get('Type', 'N/A'),
                            feedback,
                            ", ".join(item.get('tags', set()))
                        ])
                        st.session_state[f"feedback_submitted_{feedback_key}"] = True
                        st.success("✅ Feedback submitted!")
                    except Exception as e:
                        st.warning(f"⚠️ Failed to save feedback. Error: {e}")
                if 'URL' in item and item['URL']:
                    st.markdown(f"<a class='buy-button' href='{item['URL']}' target='_blank'>Buy Now</a>", unsafe_allow_html=True)
        if not (books or newspapers):
            st.markdown("_No primary recommendations found based on your current tags. Please try adjusting your input or generating new tags._")
    else:
        st.markdown("_No primary recommendations found based on your current tags. Please try adjusting your input or generating new tags._")

    if related_books:
        st.markdown("---")
        st.markdown("### 📖 You Might Also Like")
        num_cols = min(5, len(related_books))
        cols = st.columns(num_cols)
        for i, book in enumerate(related_books):
            with cols[i % num_cols]:
                img_url = None
                if book.get('Image', '').startswith("http"):
                    img_url = book['Image']
                elif 'URL' in book and "amazon." in book['URL'] and "/dp/" in book['URL']:
                    try:
                        asin = book['URL'].split('/dp/')[-1].split('/')[0].split('?')[0]
                        img_url = f"https://images-na.ssl-images-amazon.com/images/P/{asin}.01._SL250_.jpg"
                    except IndexError:
                        pass
                if img_url:
                    st.image(img_url, width=120)
                st.caption(book.get('Title', 'N/A'))
    else:
        st.markdown("_No other related books found with your current tags. Try generating new tags or searching for a specific topic!_")
        st.markdown("---")
        st.markdown("### ✨ Or, explore some popular titles:")
        if not content_df.empty and 'Type' in content_df.columns:
            fallback_books_df = content_df[content_df['Type'].str.lower() == 'book']
            if not fallback_books_df.empty:
                fallback_books = fallback_books_df.sample(min(5, len(fallback_books_df)), random_state=1).to_dict('records')
                num_cols_fallback = min(5, len(fallback_books))
                cols_fallback = st.columns(num_cols_fallback)
                for i, book in enumerate(fallback_books):
                    with cols_fallback[i % num_cols_fallback]:
                        img_url = None
                        if book.get('Image', '').startswith("http"):
                            img_url = book['Image']
                        elif 'URL' in book and "amazon." in book['URL'] and "/dp/" in book['URL']:
                            try:
                                asin = book['URL'].split('/dp/')[-1].split('/')[0].split('?')[0]
                                img_url = f"https://images-na.ssl-images-amazon.com/images/P/{asin}.01._SL250_.jpg"
                            except IndexError:
                                pass
                        if img_url:
                            st.image(img_url, width=120)
                        st.caption(book.get('Title', 'N/A'))
            else:
                st.markdown("_No books available in the database to recommend._")
        else:
            st.markdown("_No books available in the database to recommend._")
