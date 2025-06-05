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

st.set_option('client.showErrorDetails', True)

st.set_page_config(page_title="Mindful Libraries", layout="centered")

# --- Custom CSS for enhanced UI ---
st.markdown("""
    <style>
    body {
        background-color: #f0f2f6; /* Light gray background */
        font-family: 'Inter', sans-serif;
    }
    .buy-button {
        background-color: #FFA500; /* Orange */
        color: white;
        padding: 0.7em 1.5em;
        border: none;
        border-radius: 8px; /* More rounded */
        text-decoration: none;
        font-weight: bold;
        margin-top: 15px;
        display: inline-block;
        transition: background-color 0.3s ease;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
    }
    .buy-button:hover {
        background-color: #FF8C00; /* Darker orange on hover */
    }
    .stButton>button {
        background-color: #4CAF50; /* Green button for generation */
        color: white;
        padding: 0.8em 2em;
        border: none;
        border-radius: 8px;
        font-weight: bold;
        transition: background-color 0.3s ease, transform 0.2s ease;
        box-shadow: 3px 3px 8px rgba(0,0,0,0.3);
    }
    .stButton>button:hover {
        background-color: #45a049;
        transform: translateY(-2px);
    }
    .stTextInput>div>div>input {
        border-radius: 8px;
        padding: 10px;
        border: 1px solid #ccc;
    }
    .stRadio>label {
        font-weight: bold;
    }
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: #333333; /* Darker headings */
    }
    .stSpinner>div>div>span {
        color: #4CAF50 !important; /* Spinner color */
    }
    .stAlert {
        border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=True)


# --- Google Sheets and OpenAI Initialization ---
try:
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

    if "GOOGLE_SERVICE_JSON" not in st.secrets:
        st.error("❌ GOOGLE_SERVICE_JSON is missing from secrets.")
        st.stop()

    service_account_info = dict(st.secrets["GOOGLE_SERVICE_JSON"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
    client = gspread.authorize(creds)

    if "OPENAI_API_KEY" not in st.secrets:
        st.error("❌ OPENAI_API_KEY is missing from secrets.")
        st.stop()

    client_ai = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

except Exception as e:
    st.error(f"Failed to initialize Google Sheets or OpenAI client. Please check your `st.secrets` configuration. Error: {e}")
    st.stop()


@st.cache_data(ttl=3600)
def load_content():
    """Loads content data from Google Sheet and processes tags."""
    try:
        sheet_url = 'https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXJRXcfmxjoj5s'
        sheet = client.open_by_url(sheet_url)
        content_ws = sheet.worksheet('ContentDB')
        df = pd.DataFrame(content_ws.get_all_records())
        if 'Tags' in df.columns:
            # Convert tags to a set of lowercase, stripped strings, excluding 'nostalgia'
            df['tags'] = df['Tags'].apply(lambda x: set(tag.strip().lower() for tag in str(x).split(',') if tag.strip().lower() != 'nostalgia'))
        else:
            df['tags'] = [set() for _ in range(len(df))]
            st.warning(" 'Tags' column not found in 'ContentDB' worksheet. Please ensure it exists.")
        return df
    except Exception as e:
        st.error(f"Failed to load content from Google Sheet. Error: {e}")
        return pd.DataFrame()

content_df = load_content()

# Initialize session state variables if they don't exist
if 'book_counter' not in st.session_state:
    st.session_state['book_counter'] = Counter()
if 'selected_tags' not in st.session_state:
    st.session_state['selected_tags'] = []
# Ensure feedback submitted flags are reset on initial load if needed, or managed per item
# For this fix, we'll keep the feedback_submitted flag per item title/type.

def save_user_input(name, jobs, hobbies, decade, selected_topics):
    """Saves user input to the 'Logs' Google Sheet."""
    try:
        sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXJRXcfmxjoj5s')
        log_ws = sheet.worksheet('Logs')
        log_ws.append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), name, jobs, hobbies, decade, ", ".join(selected_topics)])
    except Exception as e:
        st.warning(f"Failed to save user data. Error: {e}")

# This function is not used in the current code, but kept for context if PDF generation is needed.
def generate_pdf(name, topics, recs):
    """Generates a PDF summary of recommendations (currently unused)."""
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

# --- Streamlit UI ---
st.image("https://i.postimg.cc/0yVG4bhN/mindfullibrarieswhite-01.png", width=300)
st.title("Discover Your Next Nostalgic Read!")
st.markdown("""
    Welcome to Mindful Libraries! Answer a few simple questions to get personalized tag suggestions and find reading material that resonates with your past.
    Let's find the perfect book or newspaper to transport you back in time!
""")

# Admin mode for tag feedback summary
admin_mode = st.sidebar.checkbox("🔍 Show Tag Feedback Summary (Admin)")
if admin_mode:
    try:
        sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXJRXcfmxjoj5s')
        fb_ws = sheet.worksheet('Feedback')
        fb_data = pd.DataFrame(fb_ws.get_all_records())
        tag_scores = {}
        for _, row in fb_data.iterrows():
            tags_str = str(row.get('Tags', '')).strip()
            feedback_str = str(row.get('Feedback', '')).strip().lower()

            if tags_str and feedback_str:
                for tag in tags_str.split(','):
                    tag = tag.strip().lower()
                    if tag:
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

st.header("Tell Us About Yourself:")
name = st.text_input("Your Name")
jobs = st.text_input("What did you used to do for a living?")
hobbies = st.text_input("What are your hobbies or favorite activities?")
decade = st.text_input("What is your favorite decade or era?")

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

if st.button("Generate My Personalized Tags & Recommendations"):
    if name and (jobs or hobbies or decade):
        with st.spinner("Our expert librarian AI is thinking deeply..."):
            if not content_df.empty and 'tags' in content_df.columns:
                # Get unique available tags from your content database
                content_tags_list = sorted(list(set(tag for tags_set in content_df['tags'] for tag in tags_set)))
                prompt = f"""
                    You are an expert librarian and therapist. Your job is to recommend 20 relevant and specific tags for reading content using the list below and this person's background. Make sure you really analyze each aspect of what they do, their hobbies, and come up with specific tags that match the list of tags in the google sheet. Be specific.

                    Available tags:
                    {", ".join(content_tags_list)}

                    Person's background:
                    Name: {name}
                    Job: {jobs if jobs else 'Not provided'}
                    Hobbies: {hobbies if hobbies else 'Not provided'}
                    Favorite Decade: {decade if decade else 'Not provided'}

                    Only return 20 comma-separated tags from the list above. Do not include any additional text or formatting.
                """
                try:
                    response = client_ai.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    topic_output = response.choices[0].message.content.strip()
                    # Update session state with generated tags
                    st.session_state['selected_tags'] = [t.strip().lower() for t in topic_output.split(',') if t.strip()]
                    st.success("✨ Tags generated!")
                except Exception as e:
                    st.error(f"Failed to generate tags using OpenAI. Please check your API key and try again. Error: {e}")
            else:
                st.warning("Cannot generate tags as content database is empty or 'tags' column is missing.")
    else:
        st.warning("Please enter your name and at least one detail about yourself (job, hobbies, or favorite decade) to generate tags.")


# --- Display Generated Tags (Persisted) ---
if st.session_state['selected_tags']:
    st.subheader("Your Personalized Tags:")
    st.info(f"Based on your input, here are the tags our AI suggests: **{', '.join(st.session_state['selected_tags'])}**")
    st.markdown("Now, scroll down to see your tailored recommendations!")

# --- Display Recommendations ---
if st.session_state['selected_tags']: # Only show recommendations section if tags exist
    st.markdown("---") # Visual separator
    st.subheader("🔍 Search for a Specific Topic:")
    search_term = st.text_input("Enter a keyword (e.g., 'adventure', 'history', 'science fiction', 'actor')")

    if search_term:
        st.markdown(f"### Results for '{search_term}'")
        generated_search_tags = set()
        if search_term:
            with st.spinner(f"Expanding search for '{search_term}' with AI..."):
                content_tags_list = sorted(list(set(tag for tags_set in content_df['tags'] for tag in tags_set)))
                search_prompt = f"""
                    Given the user's search query, provide up to 10 relevant and specific tags from the following list that would help find related reading content.
                    Ensure the tags you return are exactly from the 'Available tags' list.
                    Available tags:
                    {", ".join(content_tags_list)}

                    User search query: "{search_term}"

                    Only return comma-separated tags from the list above. Do not include any additional text or formatting.
                """
                try:
                    response = client_ai.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": search_prompt}]
                    )
                    ai_tags_output = response.choices[0].message.content.strip()
                    # Filter AI-generated tags to ensure they are actually in content_tags_list
                    ai_tags_from_response = {t.strip().lower() for t in ai_tags_output.split(',') if t.strip()}
                    generated_search_tags = ai_tags_from_response.intersection(set(content_tags_list))

                    if generated_search_tags:
                        st.info(f"AI-expanded your search to include tags: **{', '.join(generated_search_tags)}**")
                    else:
                        st.info("AI did not find specific tags for your search. Searching for direct keyword matches.")
                except Exception as e:
                    st.warning(f"Could not expand search with AI. Searching only for direct matches. Error: {e}")

        results = []
        search_term_lower = search_term.lower()

        for item in content_df.to_dict('records'):
            item_title_lower = item.get('Title', '').lower()
            item_summary_lower = item.get('Summary', '').lower()
            item_tags_set = item.get('tags', set())

            # Criteria 1: Direct keyword match in Title or Summary
            direct_text_match = search_term_lower in item_title_lower or \
                                search_term_lower in item_summary_lower

            # Criteria 2: Direct keyword match as an existing tag (e.g., if "actor" is itself a tag in the DB)
            direct_tag_match = search_term_lower in item_tags_set

            # Criteria 3: Match with any AI-generated tags (exact match against item's tags)
            ai_tag_found = False
            for ai_tag in generated_search_tags:
                if ai_tag in item_tags_set:
                    ai_tag_found = True
                    break

            if direct_text_match or direct_tag_match or ai_tag_found:
                results.append(item)

        if results:
            for item in results[:5]: # Display top 5 search results
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
                    else:
                        st.image(f"https://placehold.co/180x250/cccccc/333333?text=No+Image", width=180)
                with cols[1]:
                    st.markdown(f"### {item.get('Title', 'N/A')} ({item.get('Type', 'N/A')})")
                    st.markdown(item.get('Summary', 'N/A'))
                    item_tags_display = item.get('tags', set())
                    if item_tags_display:
                         st.markdown(f"_Tags: {', '.join(item_tags_display)}_")

                    if 'URL' in item and item['URL']:
                        st.markdown(f"<a class='buy-button' href='{item['URL']}' target='_blank'>Buy Now</a>", unsafe_allow_html=True)
            if len(results) > 5:
                st.info(f"Showing top 5 results. Found {len(results)} total matches for '{search_term}'.")
        else:
            st.info(f"No results found for '{search_term}' or its related tags. Try a different keyword or explore the personalized recommendations below.")

    st.markdown("---") # Visual separator
    st.subheader(f"📚 Personalized Recommendations for You!")

    books_candidates = []
    newspapers_candidates = []

    # Iterate through content to find matching items based on generated tags and feedback scores
    for item in content_df.itertuples(index=False):
        item_tags = getattr(item, 'tags', set())
        item_type = getattr(item, 'Type', '').lower()

        tag_matches = item_tags & set(st.session_state['selected_tags'])
        num_matches = len(tag_matches)
        # Calculate a weighted score based on feedback. Positive feedback increases weight, negative decreases.
        tag_weight = sum(feedback_tag_scores.get(tag, 0) for tag in tag_matches)

        if item_type == 'newspaper' and num_matches >= 2 and tag_weight >= -2:
            newspapers_candidates.append((num_matches, tag_weight, item._asdict()))
        elif item_type == 'book' and num_matches >= 2 and tag_weight >= 2:
            books_candidates.append((num_matches, tag_weight, item._asdict()))

    # Sort candidates by number of matches and then by feedback weight (descending)
    books_candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    newspapers_candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)

    # Select top 3 books and newspapers
    books = [item_dict for _, _, item_dict in books_candidates[:3]]
    newspapers = [item_dict for _, _, item_dict in newspapers_candidates[:3]]

    # Keep track of primary recommended titles to avoid duplicates in "You Might Also Like"
    primary_recommended_titles = {item.get('Title') for item in books + newspapers if item.get('Title')}

    related_books = []
    # Collect all relevant tags from selected_tags and primary recommendations
    all_relevant_tags = set(st.session_state['selected_tags'])
    for item in books + newspapers:
        all_relevant_tags.update(item.get('tags', set()))

    temp_related_books_candidates = []
    for item in content_df.to_dict('records'):
        # Exclude already recommended primary books and only consider other books
        if item.get('Title') not in primary_recommended_titles and item.get('Type', '').lower() == 'book':
            common_tags = set(item.get('tags', set())) & all_relevant_tags
            if len(common_tags) > 0: # Only add if there's at least one common tag
                temp_related_books_candidates.append((len(common_tags), item))

    # Sort related books by the number of common tags
    temp_related_books_candidates.sort(key=lambda x: x[0], reverse=True)
    related_books = [book_dict for _, book_dict in temp_related_books_candidates][:10]

    if books or newspapers:
        for item in books + newspapers:
            cols = st.columns([1, 2]) # Column layout for image and text
            with cols[0]:
                img_url = None
                if item.get('Image', '').startswith("http"):
                    img_url = item['Image']
                elif 'URL' in item and "amazon." in item['URL'] and "/dp/" in item['URL']:
                    try:
                        # Extract ASIN from Amazon URL to construct image URL
                        asin = item['URL'].split('/dp/')[-1].split('/')[0].split('?')[0]
                        img_url = f"https://images-na.ssl-images-amazon.com/images/P/{asin}.01._SL250_.jpg"
                    except IndexError:
                        pass
                if img_url:
                    st.image(img_url, width=180) # Display image
                else:
                    # Fallback if no image URL is found
                    st.image(f"https://placehold.co/180x250/cccccc/333333?text=No+Image", width=180)
            with cols[1]:
                st.markdown(f"### {item.get('Title', 'N/A')} ({item.get('Type', 'N/A')})")
                st.markdown(item.get('Summary', 'N/A'))
                original_tag_matches = set(item.get('tags', set())) & set(st.session_state['selected_tags'])
                if original_tag_matches:
                    st.markdown(f"**Why this was recommended:** Matched tags — **{', '.join(original_tag_matches)}**")
                else:
                    st.markdown("_No direct tag matches found for this recommendation._")

                # Unique key for each feedback radio button
                feedback_key = f"feedback_{item.get('Title', 'NoTitle')}_{item.get('Type', 'NoType')}"
                feedback = st.radio(
                    f"Was this recommendation helpful?",
                    ["Select an option", "✅ Yes", "❌ No"],
                    index=0, # Default to "Select an option"
                    key=feedback_key # Use a unique key
                )

                # Check if feedback has been submitted for this item in the current session
                if feedback != "Select an option" and not st.session_state.get(f"feedback_submitted_{feedback_key}", False):
                    try:
                        sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXJRXcfmxjoj5s')
                        feedback_ws = sheet.worksheet('Feedback')
                        feedback_ws.append_row([
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            name, # User's name
                            item.get('Title', 'N/A'),
                            item.get('Type', 'N/A'),
                            feedback,
                            ", ".join(item.get('tags', set())) # All tags associated with the item
                        ])
                        st.session_state[f"feedback_submitted_{feedback_key}"] = True # Mark as submitted
                        st.success("✅ Feedback submitted! Thank you for helping us improve.")
                    except Exception as e:
                        st.warning(f"⚠️ Failed to save feedback. Error: {e}")

                if 'URL' in item and item['URL']:
                    st.markdown(f"<a class='buy-button' href='{item['URL']}' target='_blank'>Buy Now</a>", unsafe_allow_html=True)
        if not (books or newspapers):
            st.markdown("_No primary recommendations found based on your current tags. Please try adjusting your input or generating new tags._")
    else:
        st.markdown("_No primary recommendations found based on your current tags. Please try adjusting your input or generating new tags._")

    # --- "You Might Also Like" Section ---
    if related_books:
        st.markdown("---")
        st.subheader("📖 You Might Also Like:")
        st.markdown("Based on your interests, here are a few more books you might enjoy.")
        num_cols = min(5, len(related_books)) # Max 5 columns
        cols = st.columns(num_cols)
        for i, book in enumerate(related_books):
            with cols[i % num_cols]: # Distribute books across columns
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
                else:
                    st.image(f"https://placehold.co/120x160/cccccc/333333?text=No+Image", width=120)
                st.caption(book.get('Title', 'N/A'))
                # Add the "Buy Now" link for related books
                if 'URL' in book and book['URL']:
                    st.markdown(f"<a class='buy-button' href='{book['URL']}' target='_blank'>Buy Now</a>", unsafe_allow_html=True)
    else:
        st.markdown("_No other related books found with your current tags. Try generating new tags or searching for a specific topic!_")
        st.markdown("---")
        st.subheader("✨ Or, explore some popular titles:")
        st.markdown("Here are some widely appreciated books to get you started.")
        if not content_df.empty and 'Type' in content_df.columns:
            fallback_books_df = content_df[content_df['Type'].str.lower() == 'book']
            if not fallback_books_df.empty:
                # Randomly sample up to 5 books for fallback
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
                        else:
                             st.image(f"https://placehold.co/120x160/cccccc/333333?text=No+Image", width=120)
                        st.caption(book.get('Title', 'N/A'))
                        # Add the "Buy Now" link for fallback books as well, for consistency
                        if 'URL' in book and book['URL']:
                            st.markdown(f"<a class='buy-button' href='{book['URL']}' target='_blank'>Buy Now</a>", unsafe_allow_html=True)
            else:
                st.markdown("_No books available in the database to recommend._")
        else:
            st.markdown("_No books available in the database to recommend._")
