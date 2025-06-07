import streamlit as st
import json
from fpdf import FPDF
from datetime import datetime, date
import os
import logging
import requests
import base64
import time

# --- Logging Setup ---
logging.basicConfig(filename='app_activity.log', level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

st.set_option('client.showErrorDetails', True)
st.set_page_config(page_title="History Hub", layout="wide", initial_sidebar_state="expanded")

# --- UI Tweaks Injection ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

html, body, .stApp {
    font-family: 'Inter', sans-serif;
    background: linear-gradient(to bottom, #e8f0fe, #ffffff);
    color: #2b2b2b;
    transition: background-color 0.3s ease;
}

@media (max-width: 768px) {
    .event-card {
        flex-direction: column;
        align-items: flex-start;
    }
    .event-card .year-avatar {
        width: 2.5rem;
        height: 2.5rem;
    }
}

.toggle-darkmode {
    position: absolute;
    top: 15px;
    right: 15px;
    background: #2d3748;
    color: white;
    border: none;
    padding: 0.4em 0.8em;
    border-radius: 8px;
    cursor: pointer;
    font-weight: bold;
    z-index: 999;
}

body.dark-mode, html.dark-mode, .stApp.dark-mode {
    background-color: #2e2e2e;
    color: #f1f1f1;
}

.dark-mode .event-card {
    background-color: #3b3b3b;
    color: #ffffff;
    border-color: #555;
}

.dark-mode .year-avatar {
    background-color: #d97706;
    color: white;
}
</style>
<script>
function toggleDarkMode() {
    const elements = [document.body, document.documentElement, ...document.getElementsByClassName('stApp')];
    elements.forEach(el => el.classList.toggle('dark-mode'));
}
</script>
""", unsafe_allow_html=True)

st.markdown('<button class="toggle-darkmode" onclick="toggleDarkMode()">🌓 Toggle Dark Mode</button>', unsafe_allow_html=True)

# --- Icon Mapping for Categories ---
CATEGORY_ICONS = {
    "Historical": "📜",
    "Births": "🎂",
    "Deaths": "🪦",
    "Holidays": "🎉",
    "Other": "🔎"
}

# --- PDF Creation Function ---
def create_pdf(content, date_str):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"This Day in History - {date_str}", ln=True, align='C')
    pdf.ln(10)
    pdf.multi_cell(0, 10, content)
    file_name = f"history_{date_str}.pdf"
    pdf.output(file_name)
    return file_name

# --- Email Link Generator ---
def generate_mailto_link(content, date_str):
    subject = f"This Day in History - {date_str}"
    body = f"Here are some historical facts for {date_str}:%0A%0A{content.replace(chr(10), '%0A')}"
    return f"mailto:?subject={subject}&body={body}"

# --- Event Generator (AI Simulation) ---
def generate_ai_history(date_obj):
    formatted_date = date_obj.strftime('%B %d')
    return f"On {formatted_date}, many incredible things happened in history.\n\n" \
           f"{CATEGORY_ICONS['Historical']} 1944: D-Day landings in Normandy.\n" \
           f"{CATEGORY_ICONS['Births']} 1971: Elon Musk was born.\n" \
           f"{CATEGORY_ICONS['Deaths']} 1968: Robert F. Kennedy passed away.\n" \
           f"{CATEGORY_ICONS['Holidays']} Flag Day is celebrated in the USA.\n" \
           f"{CATEGORY_ICONS['Other']} Did you know? June 6 is also National Yo-Yo Day!"

# --- Main UI ---
st.title("This Day in History")
st.write("Choose a date and explore events, fun facts, and trivia!")

selected_date = st.date_input("Select a date", datetime.today())
date_str = selected_date.strftime("%B %d, %Y")

if st.button("Generate History Report"):
    with st.spinner("Generating AI history content..."):
        result = generate_ai_history(selected_date)
        st.success("Here's what we found:")
        st.text_area("This Day in History:", result, height=250)

        # PDF Download
        pdf_file = create_pdf(result, selected_date.strftime('%Y%m%d'))
        with open(pdf_file, "rb") as f:
            st.download_button("📄 Download PDF", f, file_name=pdf_file, mime="application/pdf")
        os.remove(pdf_file)

        # Email Link
        mailto_link = generate_mailto_link(result, date_str)
        st.markdown(f"[📧 Share via Email]({mailto_link})", unsafe_allow_html=True)
