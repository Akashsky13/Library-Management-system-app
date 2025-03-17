from flask import Blueprint, render_template, request, session, redirect, url_for, flash
import datetime
import sqlite3

search = Blueprint('search', __name__, static_folder='static', template_folder='templates')

def query_book_db(query, args=(), one=False):
    with sqlite3.connect('library.db') as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        result = cursor.execute(query, args).fetchone() if one else cursor.execute(query, args).fetchall()
    return result
@search.route("/request_book", methods=['POST'])
def request_book():
    # Check if the user is logged in
    if 'user_id' not in session:
        flash("User not logged in", "error")
        return redirect(url_for('login'))

    user_id = session['user_id']
    
    # Get form data
    book_id = request.form.get('bookId')
    number_of_days = request.form.get('numberOfDays')

    # Get current date
    current_date = datetime.date.today().isoformat()

    try:
        # Retrieve book details from the database
        book_details = query_book_db('''
            SELECT books.*, sections.section_name
            FROM books
            INNER JOIN sections ON books.section_id = sections.id
            WHERE books.id = ?
        ''', (book_id,), one=True)

        if book_details:
            book_name = book_details['name']
            author_name = book_details['author']
            section_name = book_details['section_name']

            # Insert request into the database
            with sqlite3.connect('library.db') as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO Requests (user_id, book_id, book_name, author_name, section_name, request_date, status, days) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, book_id, book_name, author_name, section_name, current_date, 'Pending', number_of_days))
                conn.commit()

                # Log success
                print("Request successfully added to the database")

                flash("Request sent successfully", "success")
        else:
            flash("Book not found", "error")

    except sqlite3.Error as e:
        print("Error requesting book:", e)
        flash("Error sending request", "error")

    return redirect(url_for('home', user_id=user_id))  # Redirect to the homepage


        
@search.route("/search", methods=['GET', 'POST'])
def search_books():
    # Extract user_id from query parameters
    user_id = request.args.get('user_id')

    # Handle POST request for search
    if request.method == 'POST':
        # Extract search term and section name from form
        search_term = request.form.get('search_term')
        section_name = request.form.get('section_name')

        # Perform search based on search term and section name
        books_list = perform_search(search_term, section_name)

        # Render search results template with books list, search term, section name, and user_id
        return render_template('search.html', books_list=books_list, search_term=search_term, section_name=section_name, user_id=user_id)

    # Render search page template with user_id
    return render_template('search.html', user_id=user_id)

def perform_search(search_term, section_name):
    # Initialize books_list
    books_list = []

    # If both search_term and section_name are provided
    if search_term and section_name:
        section_id = get_section_id(section_name)
        if section_id:
            books_list = query_books_by_section_and_term(section_id, search_term)
    # If only search_term is provided
    elif search_term:
        books_list = query_books_by_term(search_term)
    # If only section_name is provided
    elif section_name:
        section_id = get_section_id(section_name)
        if section_id:
            books_list = query_books_by_section(section_id)

    return books_list

def get_section_id(section_name):
    section_query = "SELECT id FROM sections WHERE section_name = ?"
    section_id = query_book_db(section_query, (section_name,), one=True)
    return section_id

def query_books_by_section(section_id):
    query = "SELECT name, author, image FROM books WHERE section_id = ?"
    return query_book_db(f"{query} ORDER BY name", (section_id['id'],))

def query_books_by_term(search_term):
    query = "SELECT name, author, image FROM books WHERE name LIKE ? OR author LIKE ?"
    return query_book_db(f"{query} ORDER BY name", (f"%{search_term}%", f"%{search_term}%"))

def query_books_by_section_and_term(section_id, search_term):
    query = "SELECT name, author, image FROM books WHERE section_id = ? AND (name LIKE ? OR author LIKE ?)"
    return query_book_db(f"{query} ORDER BY name", (section_id['id'], f"%{search_term}%", f"%{search_term}%"))
