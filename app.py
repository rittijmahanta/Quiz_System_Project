from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from scraper import start_scraping
# from questgen_interface import generate_mcqs
from questgen_interface import generate_mcqs, generate_bool, generate_faq, generate_paraphrase, generate_answers
from flask import jsonify # <- `jsonify` instead of `json`
from AutoQuiz.encoding.options import arrange_options

app = Flask(__name__)
app.secret_key = 'your_secret_key'

DB_NAME = 'database.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT,
        title TEXT,
        content TEXT,
        date TEXT)''')
    
    conn.commit()
    conn.close()

init_db()

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uname = request.form['username']
        pwd = request.form['password']
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (uname, pwd))
        user = c.fetchone()
        conn.close()
        if user:
            session['username'] = uname
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        uname = request.form['username']
        pwd = request.form['password']
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (uname, pwd))
            conn.commit()
            flash('Signup successful. Please log in.')
            return redirect(url_for('login'))
        except:
            flash('Username already exists')
        finally:
            conn.close()
    return render_template('signup.html')

@app.route('/home', methods=['GET', 'POST'])
def home():
    if 'username' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        minutes = int(request.form['duration'])
        start_scraping(minutes)
        flash("Articles scraped successfully!")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM articles ORDER BY id DESC")
    articles = c.fetchall()
    conn.close()
    return render_template('home.html', articles=articles)

import google.generativeai as genai
import json

api_key = 'AIzaSyAiDrJ2Gee2TL9o5iZOxCFwp_FiTM4owfs'
genai.configure(api_key=api_key)

model = genai.GenerativeModel(model_name="gemini-1.5-flash")

# def arrange_options(questions, method):
#     if not questions:
#         return questions

#     # Prepare base prompts
#     prompts = {
#         'mcq': (
#             "You are an expert MCQ setter. Improve these MCQ questions and options. "
#             "Fix grammar, make distractors realistic, and ensure clarity. "
#             "Return ONLY a JSON array of dicts with keys: 'question', 'options', 'answer'.\n\n"
#         ),
#         'bool': (
#             "You are an expert at writing True/False questions. Improve clarity and correctness. "
#             "Return ONLY a JSON array of dicts with keys: 'question' and 'answer' (True/False).\n\n"
#         ),
#         'faq': (
#             "You are an expert FAQ editor. Improve the quality of these question-answer pairs. "
#             "Return ONLY a JSON array of dicts with keys: 'question' and 'answer'.\n\n"
#         ),
#     }

#     prompt = prompts.get(method)
#     if not prompt:
#         return questions

#     # Build the final prompt
#     full_prompt = prompt + json.dumps(questions, indent=2)

#     try:
#         response = model.generate_content(full_prompt)
#         if hasattr(response, 'text') and response.text:
#             cleaned_text = response.text.strip().strip('```json').strip('```').strip()
#             return json.loads(cleaned_text)
#         else:
#             return questions
#     except Exception as e:
#         print(f"Error refining questions with Gemini: {e}")
#         return questions


@app.route('/generate_questions/<int:article_id>', methods=['POST'])
def generate_questions(article_id):
    method = request.form['method']
    num_questions = int(request.form['num_questions'])
    custom_content = request.form.get('custom_content_hidden', '').strip()

    # Use custom content if available
    if custom_content:
        combined_content = custom_content
    elif article_id == 0:
        selected_ids = request.form.get('selected_articles', '')
        id_list = [int(id.strip()) for id in selected_ids.split(',') if id.strip().isdigit()]

        if not id_list:
            return "No articles selected and no custom content provided", 400
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        placeholders = ','.join(['?'] * len(id_list))
        query = f"SELECT content FROM articles WHERE id IN ({placeholders})"
        c.execute(query, id_list)
        contents = [row[0] for row in c.fetchall()]
        conn.close()

        combined_content = '\n\n'.join(contents)
    else:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT content FROM articles WHERE id = ?", (article_id,))
        row = c.fetchone()
        conn.close()
        if not row:
            return "Article not found", 404
        combined_content = row[0]

    # Generate based on method
    if method == 'mcq':
        questions = generate_mcqs(combined_content, num_questions)
       
    elif method == 'bool':
        questions = generate_bool(combined_content, num_questions)
        
    elif method == 'faq':
        questions = generate_faq(combined_content, num_questions)
        
    else:
        return render_template('quiz.html', questions=[])

    
    questions = arrange_options(questions, method)
    if method == 'faq':
        return render_template('faq.html', questions=questions)
    else:
        return render_template('quiz.html', questions=questions)

    # return render_template('quiz.html', questions=questions)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/paraphrase', methods=['GET', 'POST'])
def paraphrase_page():
    if request.method == 'POST':
        combined_content = request.form['input_question']
        num_questions = 1  # ← Fixed: only 1 paraphrase needed
        questions = generate_paraphrase(combined_content, num_questions)
        return render_template('paraphrase.html', questions=questions)
    return render_template('paraphrase.html')

@app.route('/question_answering', methods=['GET', 'POST'])
def question_answering():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM articles ORDER BY id DESC")
    articles = c.fetchall()
    conn.close()
    return render_template('qa.html', articles=articles)  # assuming you have a paraphrase.html

@app.route('/get_answer', methods=['POST'])
def get_answer():
    data = request.get_json()
    article_id = data.get('article_id')
    question = data.get('question')

    if article_id and question:
        try:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT content FROM articles WHERE id = ?", (article_id,))
            row = c.fetchone()
            conn.close()

            if not row:
                return jsonify({"success": False, "error": "Article not found."})

            content = row[0]

            # Now call your function
            answers = generate_answers(content, question)
            return jsonify({"success": True, "answer": answers})

        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    else:
        return jsonify({"success": False, "error": "Missing article_id or question."})




if __name__ == '__main__':
    app.run(debug=True)
