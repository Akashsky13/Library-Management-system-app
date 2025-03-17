from flask import Blueprint, request, jsonify, render_template
import sqlite3
from datetime import datetime

dashboard = Blueprint('dashboard', __name__)

@dashboard.route('/dashboard')
def board():
    # Connect to the database
    conn = sqlite3.connect('library.db')
    cursor = conn.cursor()

    # Fetch all requests from the requests table
    cursor.execute("SELECT * FROM Requests")
    requests = cursor.fetchall()
    
    # Fetch user emails
    user_emails = {}
    cursor.execute("SELECT id, email FROM users")
    users = cursor.fetchall()
    for user in users:
        user_emails[user[0]] = user[1]

    conn.close()

    # Create a list to store modified requests
    modified_requests = []

    # Calculate the number of days left for granted books and update status if necessary
    for req in requests:
        if req[7] == 'grant' and req[8]:
            issue_date = datetime.strptime(req[8], '%Y-%m-%d')
            return_date = datetime.strptime(req[9], '%Y-%m-%d')
            days_left = (return_date - datetime.now()).days+1
            # Check if days left is zero
            if days_left <= -3:
                # Update status to 'completed' if days left is zero
                conn = sqlite3.connect('library.db')
                cursor = conn.cursor()
                cursor.execute("UPDATE Requests SET status = ? WHERE request_id = ?", ('completed', req[0]))
                conn.commit()
                conn.close()
            # Convert the tuple to a list, append the days_left, then convert it back to a tuple
            modified_req = list(req)
            modified_req.append(days_left)
            modified_requests.append(tuple(modified_req))
        else:
            modified_requests.append(req)
    reversed_requests = list(reversed(modified_requests))
    return render_template("dashboard.html", requests=reversed_requests, user_emails=user_emails)

@dashboard.route('/update_status', methods=['POST'])
def update_status():
    # Get request data from the frontend
    request_data = request.json
    request_id = request_data.get('request_id')
    status = request_data.get('status')

    # Update the status of the request in the database
    conn = sqlite3.connect('library.db')
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE Requests SET status = ? WHERE request_id = ?", (status, request_id))
        conn.commit()
        return jsonify({'message': 'Status updated successfully'}), 200
    except sqlite3.Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@dashboard.route('/issue_book', methods=['POST'])
def issue_book():
    # Get request data from the frontend
    request_data = request.json
    request_id = request_data.get('request_id')
    issue_date = request_data.get('issue_date')
    return_date = request_data.get('return_date')

    # Update the issue date and return date in the database
    conn = sqlite3.connect('library.db')
    cursor = conn.cursor()
    try:
        # Update issue date and return date
        cursor.execute("UPDATE Requests SET issue_date = ?, return_date = ? WHERE request_id = ?", (issue_date, return_date, request_id))
        # Update status to 'grant'
        cursor.execute("UPDATE Requests SET status = ? WHERE request_id = ?", ('grant', request_id))
        conn.commit()
        return jsonify({'message': 'Issue book successful'}), 200
    except sqlite3.Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()
