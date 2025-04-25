from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from scraper import start_scraping
# from questgen_interface import generate_mcqs
from questgen_interface import generate_mcqs, generate_bool, generate_faq, generate_paraphrase, generate_answers

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

# @app.route('/quiz/<int:article_id>')
# def quiz(article_id):
#     conn = sqlite3.connect(DB_NAME)
#     c = conn.cursor()
#     c.execute("SELECT content FROM articles WHERE id = ?", (article_id,))
#     content = c.fetchone()[0]
#     conn.close()
#     questions = generate_mcqs(content)
#     return render_template('quiz.html', questions=questions)

# @app.route('/generate_questions/<int:article_id>', methods=['POST'])
# @app.route('/generate_questions/<int:article_id>', methods=['POST'])
# def generate_questions(article_id):
#     method = request.form['method']
#     num_questions = int(request.form['num_questions'])

#     conn = sqlite3.connect(DB_NAME)
#     c = conn.cursor()
#     c.execute("SELECT content FROM articles WHERE id = ?", (article_id,))
#     content = c.fetchone()[0]
#     conn.close()

#     if method == 'mcq':
#         questions = generate_mcqs(content, num_questions)
#         return render_template('mcq.html', questions=questions)
#     elif method == 'bool':
#         questions = generate_bool(content, num_questions)
#         return render_template('bool.html', questions=questions)
#     elif method == 'faq':
#         questions = generate_faq(content, num_questions)
#         return render_template('faq.html', questions=questions)
#     elif method == 'paraphrase':
#         questions = generate_paraphrase(content)
#         return render_template('paraphrase.html', questions=questions)
#     elif method == 'qa':
#         # For QA, assume we ask it to answer the first few questions it generates
#         sample_questions = generate_faq(content, num_questions)  # or any other way to get input_question
#         questions = generate_answers(content, [q['Question'] for q in sample_questions])
#         return render_template('qa.html', questions=questions)
#     else:
#         questions = []
#         return render_template('quiz.html', questions=questions)

# @app.route('/generate_questions/<int:article_id>', methods=['POST'])
# def generate_questions(article_id):
#     method = request.form['method']
#     num_questions = int(request.form['num_questions'])

#     if article_id == 0:
#         # Handle combined article request
#         # Handle combined article request
#         selected_ids = request.form.get('selected_articles', '')
#         id_list = [int(id.strip()) for id in selected_ids.split(',') if id.strip().isdigit()]

#         if not id_list:
#             return "No articles selected", 400
        
#         conn = sqlite3.connect(DB_NAME)
#         c = conn.cursor()
#         placeholders = ','.join(['?'] * len(id_list))
#         query = f"SELECT content FROM articles WHERE id IN ({placeholders})"
#         c.execute(query, id_list)
#         contents = [row[0] for row in c.fetchall()]
#         conn.close()

#         combined_content = '\n\n'.join(contents)
#     else:
#         # Handle single article
#         conn = sqlite3.connect(DB_NAME)
#         c = conn.cursor()
#         c.execute("SELECT content FROM articles WHERE id = ?", (article_id,))
#         content = c.fetchone()[0]
#         conn.close()
#         combined_content = content

#     if method == 'mcq':
#         questions = generate_mcqs(combined_content, num_questions)
#         return render_template('mcq.html', questions=questions)
#     elif method == 'bool':
#         questions = generate_bool(combined_content, num_questions)
#         return render_template('bool.html', questions=questions)
#     elif method == 'faq':
#         questions = generate_faq(combined_content, num_questions)
#         return render_template('faq.html', questions=questions)
#     elif method == 'paraphrase':
#         questions = generate_paraphrase(combined_content)
#         return render_template('paraphrase.html', questions=questions)
#     elif method == 'qa':
#         sample_questions = generate_faq(combined_content, num_questions)
#         questions = generate_answers(combined_content, [q['Question'] for q in sample_questions])
#         return render_template('qa.html', questions=questions)
#     else:
#         return render_template('quiz.html', questions=[])


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
        return render_template('mcq.html', questions=questions)
    elif method == 'bool':
        questions = generate_bool(combined_content, num_questions)
        return render_template('bool.html', questions=questions)
    elif method == 'faq':
        questions = generate_faq(combined_content, num_questions)
        return render_template('faq.html', questions=questions)
    elif method == 'paraphrase':
        questions = generate_paraphrase(combined_content)
        return render_template('paraphrase.html', questions=questions)
    elif method == 'qa':
        sample_questions = generate_faq(combined_content, num_questions)
        questions = generate_answers(combined_content, [q['Question'] for q in sample_questions])
        return render_template('qa.html', questions=questions)
    else:
        return render_template('quiz.html', questions=[])



    # return render_template('quiz.html', questions=questions)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
