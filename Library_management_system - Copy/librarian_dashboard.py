import sqlite3
from flask import Blueprint, render_template

librarian_dashboards = Blueprint('librarian_dashboard', __name__)

DATABASE = 'library.db'

@librarian_dashboards.route('/librarian_dashboard')
def librarian_dashboard():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    # Total Number of Requests
    c.execute("SELECT COUNT(*) FROM Requests")
    total_requests = c.fetchone()[0]

    # Requests by Status
    c.execute("SELECT status, COUNT(*) FROM Requests GROUP BY status")
    requests_by_status = c.fetchall()

    # Top Requested Books
    c.execute("""
        SELECT book_name, COUNT(*) AS num_requests 
        FROM Requests 
        GROUP BY book_id 
        ORDER BY num_requests DESC 
        LIMIT 10
    """)
    top_requested_books = c.fetchall()

    # Requests Over Time
    c.execute("""
        SELECT strftime('%Y-%m', request_date) AS month, COUNT(*) AS num_requests 
        FROM Requests 
        GROUP BY month
    """)
    requests_over_time = c.fetchall()

    # Average Time to Fulfill Requests
    c.execute("""
        SELECT ROUND(AVG(julianday(issue_date) - julianday(request_date)), 2) AS avg_fulfillment_time 
        FROM Requests 
        WHERE status = 'grant'
    """)
    avg_fulfillment_time = c.fetchone()[0]

    # Requests by User
    c.execute("""
        SELECT substr(l.email, 1, instr(l.email, '@') - 1) AS email, COUNT(*) AS num_requests 
        FROM login AS l 
        JOIN Requests AS r ON r.user_id = l.id 
        GROUP BY email
    """)
    requests_by_user = c.fetchall()

    # Late Returns
    c.execute("""
        SELECT COUNT(*) 
        FROM Requests 
        WHERE status = 'grant' AND DATE('now') > return_date
    """)
    late_returns = c.fetchone()[0]

    # Popular Sections
    c.execute("""
        SELECT section_name, COUNT(*) AS num_requests 
        FROM Requests 
        JOIN books ON Requests.book_id = books.id 
        GROUP BY section_name
    """)
    popular_sections = c.fetchall()

    # User Engagement
    c.execute("SELECT COUNT(DISTINCT user_id) FROM Requests")
    active_users = c.fetchone()[0]

    # Feedback and Ratings
    c.execute("""
        SELECT feedback, rating 
        FROM Requests 
        WHERE feedback IS NOT NULL AND rating IS NOT NULL
    """)
    feedback_and_ratings = c.fetchall()

    # Top Rated Books
    c.execute("""
        SELECT book_name, AVG(rating) AS avg_rating
        FROM Requests 
        WHERE rating IS NOT NULL
        GROUP BY book_id
        ORDER BY avg_rating DESC
        LIMIT 10
    """)
    top_rated_books = c.fetchall()

    conn.close()

    return render_template('librarian_dashboard.html', 
                           total_requests=total_requests, 
                           requests_by_status=requests_by_status, 
                           top_requested_books=top_requested_books, 
                           requests_over_time=requests_over_time, 
                           avg_fulfillment_time=avg_fulfillment_time, 
                           requests_by_user=requests_by_user, 
                           late_returns=late_returns, 
                           popular_sections=popular_sections, 
                           active_users=active_users,
                           feedback_and_ratings=feedback_and_ratings,
                           top_rated_books=top_rated_books)
