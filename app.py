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
        box-shadow: 2px 2px 4px rgba(0,0,0,0.2); /* Reduced shadow */
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
    .stCheckbox span { /* Style for checkbox labels */
        font-size: 1.1em;
        margin-left: 5px;
    }
    .nav-button-link {
        background-color: #007bff; /* A nice blue for navigation */
        color: white !important; /* !important to override default link color */
        padding: 0.6em 1.2em;
        border: none;
        border-radius: 8px;
        text-decoration: none; /* Remove underline */
        font-weight: bold;
        transition: background-color 0.3s ease, transform 0.2s ease;
        box-shadow: 1px 1px 3px rgba(0,0,0,0.15); /* Reduced shadow */
        display: inline-block; /* Allows padding and margins */
        margin: 5px; /* Spacing between buttons */
        text-align: center;
        min-width: 120px; /* Ensure consistent width */
    }
    .nav-button-link:hover {
        background-color: #0056b3; /* Darker blue on hover */
        transform: translateY(-1px);
    }
    /* New style for sticky navigation */
    .sticky-navbar {
        position: sticky;
        top: 0;
        z-index: 1000; /* Ensures it stays on top of other content */
        background-color: #f0f2f6; /* Match body background or choose a contrasting one */
        padding: 10px 0; /* Add some padding around the buttons */
        border-bottom: 1px solid #e0e0e0; /* Optional: a subtle line at the bottom */
        box-shadow: 0 2px 5px rgba(0,0,0,0.1); /* Optional: subtle shadow */
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
# Initialize 'active_tags_for_filter' to an empty list at the start
if 'active_tags_for_filter' not in st.session_state:
    st.session_state['active_tags_for_filter'] = []
# New session state for managing individual checkbox states
if 'tag_checkbox_states' not in st.session_state:
    st.session_state['tag_checkbox_states'] = {}

if 'current_user_name' not in st.session_state:
    st.session_state['current_user_name'] = ""
if 'current_user_jobs' not in st.session_state:
    st.session_state['current_user_jobs'] = ""
if 'current_user_hobbies' not in st.session_state:
    st.session_state['current_user_hobbies'] = ""
if 'current_user_decade' not in st.session_state:
    st.session_state['current_user_decade'] = ""

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

# Function to save user input to Google Sheet
def save_user_input(name, jobs, hobbies, decade, selected_topics):
    """Saves user input to the 'Logs' Google Sheet."""
    try:
        sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1AmczPlmyc-TR1IZBOExqi1ur_dS7dSXJRXcfmxjoj5s')
        log_ws = sheet.worksheet('Logs')
        log_ws.append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), name, jobs, hobbies, decade, ", ".join(selected_topics)])
    except Exception as e:
        st.warning(f"Failed to save user data. Error: {e}")

@st.cache_data(ttl=3600) # Cache the explanation for an hour
def generate_recommendation_explanation(item, user_info, selected_tags_from_session, _ai_client):
    """Generates an AI-powered explanation for a specific recommendation."""
    prompt = f"""
    You are a helpful assistant for a student volunteer working with an individual living with dementia.
    Explain why the following reading material is a good recommendation for a session with their pair, given the user's background and the item's details. Focus on how it could spark positive memories, facilitate conversation, or provide a calming activity. Frame it as if you are giving advice to the student volunteer.

    User's Background:
    Name: {user_info['name']}
    Job: {user_info['jobs'] if user_info['jobs'] else 'Not provided'}
    Hobbies: {user_info['hobbies'] if user_info['hobbies'] else 'Not provided'}
    Favorite Decade: {user_info['decade'] if user_info['decade'] else 'Not provided'}

    Recommended Item:
    Title: {item.get('Title', 'N/A')}
    Type: {item.get('Type', 'N/A')}
    Summary: {item.get('Summary', 'N/A')}
    Tags: {', '.join(item.get('tags', set()))}

    The personalized tags for the user that led to this recommendation were: {', '.join(selected_tags_from_session)}

    Explain in 2-3 sentences.
    """
    try:
        response = _ai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Could not generate explanation at this time. Error: {e}"

@st.cache_data(ttl=3600) # Cache the historical context for an hour
def generate_historical_context(decade, _ai_client):
    """Generates a brief, positive historical overview for a given decade."""
    prompt = f"""
    You are a helpful assistant for a student volunteer working with an individual living with dementia.
    Given the decade "{decade}", provide a brief (2-3 sentences), positive, and gentle overview of what made that era special. Focus on aspects that could evoke pleasant memories, such as common pastimes, cultural trends, or general positive feelings associated with the period. This information will help the student volunteer understand the context for their pair. Avoid any potentially sensitive or negative historical events.
    """
    try:
        response = _ai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Could not retrieve historical context for {decade}. Error: {e}"

@st.cache_data(ttl=3600) # Cache the expanded search tags for an hour
def get_ai_expanded_search_tags(search_term, content_tags_list, _ai_client):
    """Uses AI to expand a search term into relevant content tags."""
    if not search_term:
        return set()

    search_prompt = f"""
        Given the user's search query, provide up to 10 relevant and specific tags from the following list that would help find related reading content.
        Ensure the tags you return are exactly from the 'Available tags' list.
        Available tags:
        {", ".join(content_tags_list)}

        User search query: "{search_term}"

        Only return comma-separated tags from the list above. Do not include any additional text or formatting.
    """
    try:
        response = _ai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": search_prompt}]
        )
        ai_tags_output = response.choices[0].message.content.strip()
        ai_tags_from_response = {t.strip().lower() for t in ai_tags_output.split(',') if t.strip()}
        return ai_tags_from_response.intersection(set(content_tags_list))
    except Exception as e:
        st.warning(f"Could not expand search with AI. Error: {e}")
        return set() # Return empty set on error

@st.cache_data(ttl=600) # Cache feedback scores for 10 minutes, can be adjusted based on update frequency
def load_feedback_tag_scores():
    """Loads tag scores from the 'Feedback' Google Sheet for reweighting."""
    feedback_scores = {}
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
                        feedback_scores[tag] = feedback_scores.get(tag, 0) + (1 if 'yes' in feedback_str else -1)
    except Exception as e:
        st.info(f"Could not load feedback tag scores. Recommendations will not be reweighted by feedback. Error: {e}")
    return feedback_scores

@st.cache_data(ttl=3600) # Cache the activity suggestions for an hour
def generate_activities(_ai_client, active_tags, recommended_titles):
    """Generates activity suggestions based on tags and recommended titles."""
    if not active_tags and not recommended_titles:
        return ["No specific tags or recommended titles to suggest activities for. Try generating personalized tags first!"]

    titles_str = ", ".join(recommended_titles) if recommended_titles else "No specific reading materials recommended yet."

    prompt = f"""
    You are a helpful assistant for a student volunteer working with an individual living with dementia.
    Given the following key interests (tags) and recommended reading materials, suggest 3-5 gentle and engaging activities that a student volunteer can do with their pair.
    Always include "Reading the recommended books/newspapers together and discussing them" as one of the suggestions.
    Focus on activities that can spark positive memories, facilitate conversation, and provide calming engagement, suitable for individuals with dementia.

    Key Interests (Tags): {', '.join(active_tags)}
    Recommended Reading Titles: {titles_str}

    Suggest activities in a numbered list format. Each activity should be a short, actionable sentence.
    """
    try:
        response = _ai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip().split('\n')
    except Exception as e:
        return [f"Could not generate activity suggestions at this time. Error: {e}"]


# --- Streamlit UI ---
st.image("https://i.postimg.cc/0yVG4bhN/mindfullibrarieswhite-01.png", width=300)
st.title("Discover Your Next Nostalgic Read!")
st.markdown("""
    Welcome to Mindful Libraries! This tool helps student volunteers curate personalized reading materials to engage individuals living with dementia.
    Answer a few simple questions about your "pair" to get tailored suggestions that can spark positive memories and facilitate meaningful interactions.
    Let's find the perfect book or newspaper to transport them back in time and create a shared experience!
""")

# --- Navigation Buttons (Sticky) ---
st.markdown('<div class="sticky-navbar">', unsafe_allow_html=True)
st.subheader("Quick Navigation:")
# Add a column for "Activities" button
nav_cols = st.columns(5) # Changed from 4 to 5 columns

with nav_cols[0]:
    st.markdown('<a href="#search_section" class="nav-button-link">Search</a>', unsafe_allow_html=True)
with nav_cols[1]:
    st.markdown('<a href="#personalized_recommendations" class="nav-button-link">My Recommendations</a>', unsafe_allow_html=True)
with nav_cols[2]:
    st.markdown('<a href="#activities_section" class="nav-button-link">Activities</a>', unsafe_allow_html=True) # New button
with nav_cols[3]:
    st.markdown('<a href="#you_might_also_like" class="nav-button-link">Related Books</a>', unsafe_allow_html=True)
with nav_cols[4]:
    if st.session_state['current_user_decade']: # Only show if decade is provided
        st.markdown('<a href="#decade_summary" class="nav-button-link">Decade Summary</a>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="nav-button-link" style="opacity: 0.5; cursor: not-allowed;">Decade Summary</div>', unsafe_allow_html=True) # Greyed out
st.markdown("</div>", unsafe_allow_html=True) # Close sticky-navbar div
st.markdown("---")


st.header("Tell Us About Your Pair:")
# Use session state to preserve input across reruns
name = st.text_input("Their Name (optional, for your reference)", value=st.session_state['current_user_name'], key="user_name_input")
jobs = st.text_input("What did they used to do for a living? (e.g., Teacher, Engineer, Homemaker)", value=st.session_state['current_user_jobs'], key="user_jobs_input")
hobbies = st.text_input("What are their hobbies or favorite activities? (e.g., Gardening, Reading, Music, Sports)", value=st.session_state['current_user_hobbies'], key="user_hobbies_input")
decade = st.text_input("What is their favorite decade or era? (e.g., 1950s, 1970s, Victorian era)", value=st.session_state['current_user_decade'], key="user_decade_input")

# Update session state with current input values
st.session_state['current_user_name'] = name
st.session_state['current_user_jobs'] = jobs
st.session_state['current_user_hobbies'] = hobbies
st.session_state['current_user_decade'] = decade

# User information dictionary to pass to AI functions
user_info = {
    'name': name,
    'jobs': jobs,
    'hobbies': hobbies,
    'decade': decade
}

# Load tag scores for reweighting (from feedback sheet) using cached function
feedback_tag_scores = load_feedback_tag_scores()


if st.button("Generate Personalized Tags & Recommendations"):
    if (jobs or hobbies or decade): # Name is optional now
        with st.spinner("Our expert librarian AI is thinking deeply..."):
            if not content_df.empty and 'tags' in content_df.columns:
                content_tags_list = sorted(list(set(tag for tags_set in content_df['tags'] for tag in tags_set)))
                prompt = f"""
                    You are an expert librarian and therapist assistant. Your job is to recommend 20 **extremely specific and granular** tags for reading content,
                    using **only** the available tags list.
                    These tags will help a student volunteer find appropriate materials for an individual living with dementia.
                    Instead of vague tags like "wellness" or "spirituality", aim for tags like "mindfulness meditation guides", "cognitive behavioral therapy", "historical fiction - roman empire", "sci-fi - cyberpunk", "vintage fashion", "classic Hollywood", "WWII memoirs", "1950s rock and roll".
                    Make sure you really analyze each aspect of what they do, their hobbies, and their favorite decade, and come up with specific tags that **exactly** match the list of tags in the google sheet.
                    The goal is to spark positive memories and facilitate engagement for the individual with dementia.

                    Available tags:
                    {", ".join(content_tags_list)}

                    Person's background:
                    Name: {name if name else 'Not provided'}
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
                    # Ensure uniqueness and sorting of tags from AI output
                    st.session_state['selected_tags'] = sorted(list(set([t.strip().lower() for t in topic_output.split(',') if t.strip()])))

                    # Initialize or reset tag_checkbox_states and active_tags_for_filter based on NEW selected_tags
                    st.session_state['tag_checkbox_states'] = {tag: True for tag in st.session_state['selected_tags']}
                    st.session_state['active_tags_for_filter'] = list(st.session_state['selected_tags']) # Immediately active
                    st.success("✨ Tags generated!")
                    save_user_input(name, jobs, hobbies, decade, st.session_state['selected_tags'])
                except Exception as e:
                    st.error(f"Failed to generate tags using OpenAI. Please check your API key and try again. Error: {e}")
            else:
                st.warning("Cannot generate tags as content database is empty or 'tags' column is missing.")
    else:
        st.warning("Please enter at least one detail about your pair (job, hobbies, or favorite decade) to generate tags.")


# --- Display Generated Tags (Persisted and Interactive) ---
if st.session_state['selected_tags']:
    st.subheader("Your Personalized Tags:")
    st.markdown("Here are the tags our AI suggests. **You can uncheck any tags you don't feel are relevant** for your pair.")

    # Ensure tag_checkbox_states is aligned with selected_tags for robust display
    # This loop ensures that any tag in selected_tags has an entry in tag_checkbox_states
    for tag in st.session_state['selected_tags']:
        if tag not in st.session_state['tag_checkbox_states']:
            st.session_state['tag_checkbox_states'][tag] = True # Default new tags to checked

    # Rebuild active_tags_for_filter based on current checkbox states
    current_active_tags = []
    cols = st.columns(min(len(st.session_state['selected_tags']), 5)) # Up to 5 columns for tags
    for i, tag in enumerate(st.session_state['selected_tags']):
        with cols[i % 5]:
            # Create checkbox, linking its value to the session state dictionary
            checked_status = st.checkbox(
                tag.capitalize(),
                # Use .get() with a default in case of unexpected state, though the preceding loop minimizes this risk
                value=st.session_state['tag_checkbox_states'].get(tag, True),
                key=f"interactive_tag_checkbox_{tag}" # Unique key for each tag
            )
            # Update the session state dictionary based on user interaction
            st.session_state['tag_checkbox_states'][tag] = checked_status

            if checked_status:
                current_active_tags.append(tag)

    # After rendering all checkboxes, update active_tags_for_filter from the collected active tags
    st.session_state['active_tags_for_filter'] = current_active_tags

    # The "Refine" button is now explicitly for triggering a re-run after checkbox changes
    if st.button("Apply Tag Filters & Update Recommendations"):
        st.success("Recommendations updated based on your selected tags!")


    st.markdown("Now, scroll down to see your tailored recommendations!")


# --- Display Historical Context (if decade provided) ---
if st.session_state['current_user_decade']:
    st.markdown('<a name="decade_summary"></a>', unsafe_allow_html=True) # Anchor for navigation
    st.markdown("---")
    st.subheader(f"🕰️ A Glimpse into the {st.session_state['current_user_decade']}:")
    with st.spinner(f"Generating context for the {st.session_state['current_user_decade']}..."):
        # Pass client_ai to the cached function
        historical_context = generate_historical_context(st.session_state['current_user_decade'], client_ai)
        st.info(historical_context)


# --- Display Recommendations ---
# Recommendations only display if there are active tags to filter by
if st.session_state['active_tags_for_filter']:
    st.markdown('<a name="search_section"></a>', unsafe_allow_html=True) # Anchor for navigation
    st.markdown("---") # Visual separator
    st.subheader("🔍 Search for a Specific Topic:")
    search_term = st.text_input("Enter a keyword (e.g., 'adventure', 'history', 'science fiction', 'actor')", key="search_input")

    if search_term:
        st.markdown(f"### Results for '{search_term}'")
        generated_search_tags = set()
        with st.spinner(f"Expanding search for '{search_term}' with AI..."):
            content_tags_list = sorted(list(set(tag for tags_set in content_df['tags'] for tag in tags_set)))
            # Use cached function for AI search tag expansion
            generated_search_tags = get_ai_expanded_search_tags(search_term, content_tags_list, client_ai)

            if generated_search_tags:
                st.info(f"AI-expanded your search to include tags: **{', '.join(generated_search_tags)}**")
            else:
                st.info("AI did not find specific tags for your search. Searching for direct keyword matches.")


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

    st.markdown('<a name="personalized_recommendations"></a>', unsafe_allow_html=True) # Anchor for navigation
    st.markdown("---") # Visual separator
    st.subheader(f"📚 Personalized Recommendations for You!")

    books_candidates = []
    newspapers_candidates = []

    # Iterate through content to find matching items based on GENERATED and ACTIVE tags and feedback scores
    for item in content_df.itertuples(index=False):
        item_tags = getattr(item, 'tags', set())
        item_type = getattr(item, 'Type', '').lower()

        # Use st.session_state['active_tags_for_filter'] for filtering
        tag_matches = item_tags & set(st.session_state['active_tags_for_filter'])
        num_matches = len(tag_matches)
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

    # Store titles of recommended books/newspapers for activity generation
    recommended_titles_for_activities = [item.get('Title', 'N/A') for item in books + newspapers]


    related_books = []
    # Collect all relevant tags from selected_tags and primary recommendations
    all_relevant_tags = set(st.session_state['active_tags_for_filter']) # Use active tags
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
                    st.image(f"https://placehold.co/180x250/cccccc/333333?text=No+Image", width=180)
            with cols[1]:
                st.markdown(f"### {item.get('Title', 'N/A')} ({item.get('Type', 'N/A')})")
                st.markdown(item.get('Summary', 'N/A'))
                original_tag_matches = item.get('tags', set()) & set(st.session_state['active_tags_for_filter'])
                if original_tag_matches:
                    st.markdown(f"**Why this was recommended:** Matched tags — **{', '.join(original_tag_matches)}**")
                else:
                    st.markdown("_No direct tag matches found for this recommendation._")

                # "Why This Book?" explanation
                with st.expander("Why this recommendation is great for your pair:"):
                    with st.spinner("Generating personalized insights..."):
                        # Pass client_ai to the cached function
                        explanation = generate_recommendation_explanation(item, user_info, st.session_state['active_tags_for_filter'], client_ai)
                        st.markdown(explanation)

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

    # --- Recommended Activities Section ---
    st.markdown('<a name="activities_section"></a>', unsafe_allow_html=True) # Anchor for navigation
    st.markdown("---")
    st.subheader("💡 Recommended Activities:")
    with st.spinner("Generating activity suggestions..."):
        activities = generate_activities(client_ai, st.session_state['active_tags_for_filter'], recommended_titles_for_activities)
        for activity in activities:
            st.markdown(activity)


    st.markdown('<a name="you_might_also_like"></a>', unsafe_allow_html=True) # Anchor for navigation
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

                # "Why This Book?" explanation for related books
                with st.expander("Why this recommendation is great for your pair:"):
                    with st.spinner("Generating personalized insights..."):
                        # Pass client_ai to the cached function
                        explanation = generate_recommendation_explanation(book, user_info, st.session_state['active_tags_for_filter'], client_ai)
                        st.markdown(explanation)

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
