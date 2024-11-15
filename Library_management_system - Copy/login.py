from flask import Flask, render_template, request, session, redirect, url_for, jsonify, flash,json
import datetime
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import sqlite3
from librarian_dashboard import librarian_dashboards
from add_new_section import add_new_section
from librarian_login import librarian_login
from dashboard import dashboard
from search import search
from werkzeug.utils import secure_filename
import secrets
app = Flask(__name__)
app.secret_key = secrets.token_hex(16) 
app.register_blueprint(librarian_dashboards)
app.register_blueprint(add_new_section)
app.register_blueprint(librarian_login)
app.register_blueprint(dashboard)
app.register_blueprint(search, url_prefix='/search')

def row_to_dict(row):
    return dict(row)
class SQLiteRowEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, sqlite3.Row):
            return dict(obj)
        return super().default(obj)  

def create_login_table():
    with sqlite3.connect('library.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
                 CREATE TABLE IF NOT EXISTS login (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  email TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL,
                  last_login TIMESTAMP
                 )
                  ''')

        
        cursor.execute('''
    CREATE TABLE IF NOT EXISTS Requests (
        request_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        book_id INTEGER,
        book_name TEXT,
        author_name TEXT,
        section_name TEXT,
        request_date DATE,
        status TEXT,
        issue_date DATE,
        return_date DATE,
        days INTEGER,
        feedback TEXT,
        rating INTEGER,
        FOREIGN KEY (user_id) REFERENCES Users(id),
        FOREIGN KEY (book_id) REFERENCES Books(id)
    )
''')





def query_login_db(query, args=(), one=False):
    with sqlite3.connect('library.db') as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        result = cursor.execute(query, args).fetchone() if one else cursor.execute(query, args).fetchall()
    return result

def login_user(email, password):
    user = query_login_db('SELECT * FROM login WHERE email = ? AND password = ?', (email, password), one=True)
    if user:
        update_last_login(user['id'])
        return user
    else:
        return None

def update_last_login(user_id):
    current_datetime = datetime.datetime.now().isoformat()
    with sqlite3.connect('library.db') as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE login SET last_login = ? WHERE id = ?', (current_datetime, user_id))
        conn.commit()

def create_user(email, password):
    with sqlite3.connect('library.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO login (email, password) 
            VALUES (?, ?)
        ''', (email, password))
        conn.commit()


create_login_table()
def create_user_if_not_exists(email, password):
    with sqlite3.connect('library.db') as conn:
        cursor = conn.cursor()
        existing_user = query_login_db('SELECT * FROM login WHERE email = ?', (email,), one=True)
        if existing_user:
            return None
        else:
            cursor.execute('''
                INSERT INTO login (email, password) 
                VALUES (?, ?)
            ''', (email, password))
            conn.commit()
            new_user = query_login_db('SELECT * FROM login WHERE email = ?', (email,), one=True)
            return new_user
@app.route("/", methods=['GET', 'POST'])
def login_or_signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = login_user(email, password)
        if user:
            session['user_id'] = user['id']
            session['user_email'] = user['email']
            return redirect(url_for('home', user_id=user['id'])) 
        new_user = create_user_if_not_exists(email, password)
        if new_user:
            session['user_id'] = new_user['id']
            session['user_email'] = new_user['email']
            return redirect(url_for('home', user_id=new_user['id'])) 
        else:
            return render_template('login.html', error='Email already exists. Please choose a different email.')

    return render_template('login.html')

def get_all_books():
    with sqlite3.connect('library.db') as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM books")
        books = cursor.fetchall()
    return books

def get_completed_books(user_id):
    with sqlite3.connect('library.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Requests WHERE user_id = ? AND status = 'completed'", (user_id,))
        completed_books = cursor.fetchall()
    return completed_books

@app.route("/app/<int:user_id>")
def home(user_id):
    if 'user_id' in session and session['user_id'] == user_id:
        conn = sqlite3.connect('library.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        try:
            c.execute("SELECT * FROM books")
            books = c.fetchall()
        except sqlite3.Error as e:
            print("Error retrieving books:", e)
            books = []
        finally:
            conn.close()
        all_books = get_all_books()
        completed_books = get_completed_books(user_id)
        return render_template("app.html", user_id=user_id, books=all_books, completed_books=completed_books)
    else:
        return redirect(url_for('login_or_signup'))
    
@app.route("/request_book", methods=['POST'])
def request_book():
    if 'user_id' not in session:
        flash("User not logged in", "error")
        return redirect(url_for('login_or_signup'))

    user_id = session['user_id']
    book_id = request.form.get('bookId')
    number_of_days = request.form.get('numberOfDays')
    current_date = datetime.date.today().isoformat()

    with sqlite3.connect('library.db') as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT books.*, sections.section_name
                FROM books
                INNER JOIN sections ON books.section_id = sections.id
                WHERE books.id = ?
            ''', (book_id,))
            book_details = cursor.fetchone()
            if book_details:
                book_name = book_details[2]  
                author_name = book_details[3]  
                section_name = book_details[-1] 
                cursor.execute('''
                    INSERT INTO Requests (user_id, book_id, book_name, author_name, section_name, request_date, status, days) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, book_id, book_name, author_name, section_name, current_date, 'Pending', number_of_days))
                conn.commit()
                flash("Request sent successfully", "success")
                return redirect(url_for('home', user_id=user_id)) 
            else:
                flash("Book not found", "error")
                return redirect(url_for('home', user_id=user_id))
        except sqlite3.Error as e:
            print("Error requesting book:", e)
            flash("Error sending request", "error")
            return redirect(url_for('home', user_id=user_id))

import os
@app.route("/view_pdf/<path:filename>")
def view_pdf(filename):
    file_path = os.path.join('static', filename)
    if os.path.exists(file_path):
        response = send_file(file_path)
        response.headers['Content-Disposition'] = 'inline; filename=%s' % filename
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response
    else:
        return "File not found", 404

@app.route('/subscribe', methods=['POST'])
def subscribe():
    # Handle subscription logic here
    # For example, process subscription form data
    # and return a response
    return 'Subscription successful!'  # or redirect to a thank you page

@app.route("/mybook/<int:user_id>")
def mybook(user_id):
    if 'user_id' in session and session['user_id'] == user_id:
        with sqlite3.connect('library.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Requests WHERE user_id = ?", (user_id,))
            requested_books = cursor.fetchall()
            cursor.execute("SELECT * FROM Requests WHERE user_id = ? AND status = 'completed'", (user_id,))
            completed_books = cursor.fetchall()
            cursor.execute("SELECT * FROM Books WHERE id IN (SELECT book_id FROM Requests WHERE user_id = ? AND status = 'grant')", (user_id,))
            granted_books = cursor.fetchall()
            current_date = datetime.datetime.now().date()
            def parse_date(date_str, format_str):
                return datetime.datetime.strptime(date_str, format_str).date()
            
        return render_template("mybook.html", user_id=user_id, requested_books=requested_books, completed_books=completed_books, granted_books=granted_books,current_date=current_date,parse_date=parse_date)
    else:
        flash("You are not logged in.", "error")
        return redirect(url_for('login_or_signup'))

@app.route("/return_book/<int:request_id>", methods=['POST'])
def return_book(request_id):
    if 'user_id' not in session:
        flash("User not logged in", "error")
        return redirect(url_for('login_or_signup'))

    user_id = session['user_id']

    with sqlite3.connect('library.db') as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM Requests WHERE request_id = ? AND user_id = ?", (request_id, user_id))
            book = cursor.fetchone()
            if book:
                cursor.execute("UPDATE Requests SET status = 'completed' WHERE request_id = ?", (request_id,))
                conn.commit()
                flash("Book returned successfully", "success")
            else:
                flash("You are not authorized to return this book", "error")
        except sqlite3.Error as e:
            print("Error returning book:", e)
            flash("Error returning book", "error")

    return redirect(url_for('mybook', user_id=user_id))

@app.route("/post_feedback_and_rating/<int:request_id>", methods=['POST'])
def post_feedback_and_rating(request_id):
    if 'user_id' not in session:
        flash("User not logged in", "error")
        return redirect(url_for('login_or_signup'))

    user_id = session['user_id']
    feedback = request.form.get('feedback')
    rating = request.form.get('rating')

    with sqlite3.connect('library.db') as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE Requests SET feedback = ?, rating = ? WHERE request_id = ?", (feedback, rating, request_id))
            conn.commit()
            flash("Feedback and rating submitted successfully", "success")
        except sqlite3.Error as e:
            print("Error updating feedback and rating:", e)
            flash("Error submitting feedback and rating", "error")

    return redirect(url_for('mybook', user_id=user_id))


@app.route("/re_request_book/<int:request_id>", methods=['POST'])
def re_request_book(request_id):
    if 'user_id' not in session:
        flash("User not logged in", "error")
        return redirect(url_for('login_or_signup'))

    user_id = session['user_id']

    with sqlite3.connect('library.db') as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM Requests WHERE request_id = ? AND user_id = ? AND status = 'reject'", (request_id, user_id))
            book = cursor.fetchone()
            if book:
                current_date = datetime.date.today().isoformat()
                cursor.execute("UPDATE Requests SET status = 'Pending', request_date = ? WHERE request_id = ?", (current_date, request_id))
                conn.commit()
                flash("Book re-requested successfully", "success")
            else:
                flash("You are not authorized to re-request this book", "error")
        except sqlite3.Error as e:
            print("Error re-requesting book:", e)
            flash("Error re-requesting book", "error")

    return redirect(url_for('mybook', user_id=user_id))

@app.route("/user_dashboard/<int:user_id>")
def user_dashboard(user_id):
    if 'user_id' in session and session['user_id'] == user_id:
        with sqlite3.connect('library.db') as conn:
            conn.row_factory = sqlite3.Row  # Set row factory here
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM login WHERE id = ?", (user_id,))
            user = cursor.fetchone()

            if user:
                email = user['email']

            cursor.execute("SELECT COUNT(*) FROM Requests WHERE user_id = ?", (user_id,))
            num_books_requested = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM Requests WHERE user_id = ? AND status = 'completed'", (user_id,))
            num_completed_requests = cursor.fetchone()[0]

            cursor.execute("SELECT section_name, COUNT(*) as count FROM Requests WHERE user_id = ? GROUP BY section_name ORDER BY count DESC LIMIT 1", (user_id,))
            favorite_section = cursor.fetchone()

            cursor.execute("SELECT author_name, COUNT(*) as count FROM Requests WHERE user_id = ? GROUP BY author_name ORDER BY count DESC LIMIT 1", (user_id,))
            favorite_author = cursor.fetchone()

            today = datetime.date.today()
            start_of_month = today.replace(day=1)
            cursor.execute("SELECT COUNT(*) FROM Requests WHERE user_id = ? AND request_date >= ? AND request_date <= ?", (user_id, start_of_month, today))
            num_books_requested_month = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM Requests WHERE user_id = ? AND status = 'completed' AND issue_date >= ? AND issue_date <= ?", (user_id, start_of_month, today))
            num_completed_books_month = cursor.fetchone()[0]
            requested_books_data = get_requested_books_by_month(user_id)
            if favorite_section:
                favorite_section_dict = row_to_dict(favorite_section)
            else:
                favorite_section_dict = None

            if favorite_author:
                favorite_author_dict = row_to_dict(favorite_author)
            else:
                favorite_author_dict = None

        return render_template("user_dashboard.html", user_id=user_id, num_books_requested=num_books_requested,
                               num_completed_requests=num_completed_requests, favorite_section=favorite_section_dict,
                               favorite_author=favorite_author_dict, num_books_requested_month=num_books_requested_month,
                               num_completed_books_month=num_completed_books_month,
                               requested_books_data=requested_books_data)
    else:
        flash("You are not logged in.", "error")
        return redirect(url_for('login_or_signup'))


def get_requested_books_by_month(user_id):
    with sqlite3.connect('library.db') as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT strftime('%Y-%m', request_date) AS month, COUNT(*) AS num_requested_books
            FROM Requests
            WHERE user_id = ?
            GROUP BY month
            ORDER BY month
        """, (user_id,))
        requested_books_by_month = cursor.fetchall()
    
    return requested_books_by_month


def send_monthly_report(email, user_id, num_books_requested, num_completed_requests, favorite_section, favorite_author, num_books_requested_month, num_completed_books_month):
    sender_email = "akashmauryapi007@gmail.com"  
    sender_password = "hbwk sohj pvjp rwgl" 
    smtp_server = "smtp.gmail.com" 
    smtp_port = 587 

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = email
    message["Subject"] = "Monthly Report for Your Library Dashboard"

  
    body = f"""
    <h3>Monthly Report for Your Library Dashboard</h3>
    <p>User ID: {email}</p>
    <p>Total Number of Books Requested: <strong>{num_books_requested}</strong></p>
    <p>Total Number of Completed Requests: <strong>{num_completed_requests}</strong></p>
    """
    if favorite_section:
        body += f"<p>Favorite Section: <strong>{favorite_section['section_name']}</strong></p>"
    if favorite_author:
        body += f"<p>Favorite Author: <strong>{favorite_author['author_name']}</strong></p>"

    body += f"""
    <p>Number of Books Requested This Month: <strong>{num_books_requested_month}</strong></p>
    <p>Number of Books Completed This Month: <strong>{num_completed_books_month}</strong></p>

    """
    message.attach(MIMEText(body, "html"))
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()  
        server.login(sender_email, sender_password)
        server.send_message(message)
from flask import send_file

@app.route("/send_monthly_report/<int:user_id>", methods=['POST'])
def send_monthly_report_route(user_id):
    if 'user_id' in session and session['user_id'] == user_id:
        with sqlite3.connect('library.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM login WHERE id = ?", (user_id,))
            user = cursor.fetchone()

            if user:
                email = user['email']

            cursor.execute("SELECT COUNT(*) FROM Requests WHERE user_id = ?", (user_id,))
            num_books_requested = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM Requests WHERE user_id = ? AND status = 'completed'", (user_id,))
            num_completed_requests = cursor.fetchone()[0]

            cursor.execute("SELECT section_name, COUNT(*) as count FROM Requests WHERE user_id = ? GROUP BY section_name ORDER BY count DESC LIMIT 1", (user_id,))
            favorite_section = cursor.fetchone()

            cursor.execute("SELECT author_name, COUNT(*) as count FROM Requests WHERE user_id = ? GROUP BY author_name ORDER BY count DESC LIMIT 1", (user_id,))
            favorite_author = cursor.fetchone()

            today = datetime.date.today()
            start_of_month = today.replace(day=1)
            cursor.execute("SELECT COUNT(*) FROM Requests WHERE user_id = ? AND request_date >= ? AND request_date <= ?", (user_id, start_of_month, today))
            num_books_requested_month = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM Requests WHERE user_id = ? AND status = 'completed' AND issue_date >= ? AND issue_date <= ?", (user_id, start_of_month, today))
            num_completed_books_month = cursor.fetchone()[0]

            try:
                send_monthly_report(email, user_id, num_books_requested, num_completed_requests, favorite_section, favorite_author, num_books_requested_month, num_completed_books_month)
                return jsonify({'success': True})
            except Exception as e:
                print(f"Error sending monthly report: {e}")
                return jsonify({'success': False})
    else:
        return jsonify({'success': False, 'error': 'Unauthorized access'})

@app.route("/send_monthly_report_ajax", methods=['POST'])
def send_monthly_report_ajax():
    if 'user_id' in session:
        user_id = session['user_id']
        return redirect(url_for('user_dashboard', user_id=user_id))

if __name__ == "__main__":
    app.run(debug=True)