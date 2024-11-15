from celery import Celery
from celery.schedules import crontab
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import sqlite3

app = Celery('tasks', broker='redis://redis:6379/0', backend='redis://redis:6379/0')

app.conf.beat_schedule = {
    'send-monthly-report': {
        'task': 'tasks.send_monthly_report',
        # 'schedule': 120.0,
        'schedule': crontab(minute=0, hour=0, day_of_month=1),
    },
    'send-reminder': {
        'task': 'tasks.send_reminder',
        'schedule':21600.0, 
        # 'schedule': crontab(hour=14, minute=38),
    },
}

app.conf.timezone = 'UTC' 

def send_email(to_email, subject, message, from_email='akashmauryapi007@gmail.com', password='hbwk sohj pvjp rwgl'):
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(message, 'html')) 

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(from_email, password)
        text = msg.as_string()
        server.sendmail(from_email, to_email, text)
        server.quit()
        return 'Email sent successfully'
    except Exception as e:
        return str(e)

def fetch_users_for_reminder():
    conn = sqlite3.connect('library.db')
    cursor = conn.cursor()
    last_login_threshold = datetime.utcnow() - timedelta(hours=18)
    
    cursor.execute("""
        SELECT DISTINCT l.email
        FROM login l
        WHERE l.last_login < ?
    """, (last_login_threshold,))
    
    users_for_reminder = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    return users_for_reminder

def fetch_user_requests():
    conn = sqlite3.connect('library.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT l.email, r.book_name, r.author_name, r.request_date, r.status, r.issue_date
        FROM Requests r
        JOIN login l ON r.user_id = l.id
    """)
    user_requests = {}
    for row in cursor.fetchall():
        email = row[0]
        book_details = {
            'book_name': row[1],
            'author_name': row[2],
            'request_date': row[3],
            'status': row[4],
            'issue_date': row[5]
        }
        if email not in user_requests:
            user_requests[email] = []
        user_requests[email].append(book_details)
    conn.close()
    return user_requests

@app.task
def send_reminder():
    users_for_reminder = fetch_users_for_reminder()
    subject = 'We Miss You!'
    message = """
    <h1>We Miss You!</h1>
    <p>It's been more than 24 hours since you last logged in. Come back and check out new books.</p>
    """
    for email in users_for_reminder:
        send_email(email, subject, message)

@app.task
def send_monthly_report():
    user_requests = fetch_user_requests()
    for email, requests in user_requests.items():
        subject = 'Monthly Report'
        message = '<h1>This is your monthly report.</h1>'
        for req in requests:
            message += f"""
            <p><strong>Book Name:</strong> {req['book_name']}</p>
            <p><strong>Author Name:</strong> {req['author_name']}</p>
            <p><strong>Request Date:</strong> {req['request_date']}</p>
            <p><strong>Status:</strong> {req['status']}</p>
            <p><strong>Issue Date:</strong> {req['issue_date']}</p>
            <hr>
            """
        send_email(email, subject, message)

