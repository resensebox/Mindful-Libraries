from flask import Flask, request, render_template_string
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

# Google Sheets Setup
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('perfect-pair-app-3524d0d0ffc0.json', scope)
client = gspread.authorize(creds)

# Replace with your actual Google Sheet URL
sheet_url = 'https://docs.google.com/spreadsheets/d/892416667'
sheet = client.open_by_url(sheet_url)

content_ws = sheet.worksheet('ContentDB')
content_df = pd.DataFrame(content_ws.get_all_records())
content_df['tags'] = content_df['Tags'].apply(lambda x: set(str(x).lower().split(',')))

# HTML form and result template
page_template = """
<!DOCTYPE html>
<html>
<head><title>Reading Recommendations</title></head>
<body>
    <h1>Get Your Reading Recommendations</h1>
    <form method="post">
        <label>Name: <input type="text" name="name" required></label><br>
        <label>Interests (comma separated):<br>
        <textarea name="interests" rows="4" cols="40" required></textarea></label><br>
        <input type="submit" value="Get Recommendations">
    </form>

    {% if results %}
        <h2>Recommendations for {{ name }}</h2>
        <ul>
        {% for item in results %}
            <li><strong>{{ item['Title'] }}</strong> ({{ item['Type'] }}) - <a href="{{ item['URL'] }}">Read</a></li>
        {% endfor %}
        </ul>
    {% endif %}
</body>
</html>
"""

def match_content(user_interests, content_df, top_n=3):
    interest_set = set(tag.strip().lower() for tag in user_interests.split(","))
    scored = []
    for _, row in content_df.iterrows():
        score = len(interest_set & row['tags'])
        if score > 0:
            scored.append((row, score))
    sorted_items = sorted(scored, key=lambda x: -x[1])
    return [item[0] for item in sorted_items[:top_n]]

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        name = request.form['name']
        interests = request.form['interests']
        results = match_content(interests, content_df)
        return render_template_string(page_template, name=name, results=results)
    return render_template_string(page_template, results=None, name=None)

if __name__ == '__main__':
    app.run(debug=True)
