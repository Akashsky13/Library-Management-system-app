import sqlite3
from flask import Blueprint, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
import os
from tempfile import TemporaryDirectory
import fitz  # PyMuPDF

add_new_section = Blueprint('add_new_section', __name__, static_folder="static", template_folder="templates")

DATABASE = 'library.db'

def create_database():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    try:
        c.execute('''CREATE TABLE IF NOT EXISTS sections (
                        id INTEGER PRIMARY KEY,
                        section_name TEXT,
                        date_created TEXT,
                        image TEXT,
                        description TEXT
                    )''')

        # Create a new table for books
        c.execute('''CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY,
        section_id INTEGER,
        name TEXT,
        author TEXT,
        pdf TEXT,  -- Changed from content to pdf path
        image TEXT,  
        FOREIGN KEY(section_id) REFERENCES sections(id)
                     )''')

        conn.commit()
    except sqlite3.Error as e:
        print("Error creating database:", e)
    finally:
        conn.close()

# Call create_database function when this script is executed
create_database()

# Function to insert data into the sections table
def insert_data(section_name, date_created, image, description):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    try:
        c.execute('''INSERT INTO sections (section_name, date_created, image, description)
                    VALUES (?, ?, ?, ?)''', (section_name, date_created, image, description))
        conn.commit()
    except sqlite3.Error as e:
        print("Error inserting data:", e)
    finally:
        conn.close()

# Function to insert book data into the books table
def insert_book(section_id, name, pdf, author, image_path):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    try:
        c.execute('''INSERT INTO books (section_id, name, pdf, author, image)
                    VALUES (?, ?, ?, ?, ?)''', (section_id, name, pdf, author, image_path))
        conn.commit()
    except sqlite3.Error as e:
        print("Error inserting book data:", e)
    finally:
        conn.close()



# Flask route to display the form and handle form submission for adding sections
@add_new_section.route('/add_new_section', methods=['GET', 'POST'])
def show_add_new_section():
    if request.method == 'POST':
        try:
            # Extract form data
            section_name = request.form['title']
            date_created = request.form['dateCreated']
            description = request.form['description']

            # Validate mandatory fields
            if not section_name or not date_created or not description:
                raise ValueError("Section name, date created, and description are mandatory")

            # Handle file upload for section image
            image_path = None
            if 'image' in request.files:
                image_file = request.files['image']
                if image_file.filename != '':
                    filename = secure_filename(image_file.filename)
                    upload_dir = os.path.join('static', 'uploads', 'sections')
                    os.makedirs(upload_dir, exist_ok=True)  # Create directory if it doesn't exist
                    image_path = os.path.join(upload_dir, filename)
                    image_file.save(image_path)
                else:
                    # If no image is uploaded, assign a default image path
                    default_image_path = 'static/uploads/download6.jpeg'
                    image_path = default_image_path

            # Insert data into the sections table
            insert_data(section_name, date_created, image_path, description)
            print("Data inserted successfully")
        except Exception as e:
            print("Error inserting data:", e)

        # Redirect to refresh page after insertion
        return redirect(url_for('add_new_section.show_add_new_section'))  

    # Retrieve all sections from the database
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM sections")
        sections = c.fetchall()
        total_sections = len(sections)
        c.execute("SELECT COUNT(*) FROM books")
        total_books = c.fetchone()[0]
    except sqlite3.Error as e:
        print("Error retrieving data:", e)
        sections = []
        total_sections = 0
        total_books = 0
    finally:
        conn.close()

    return render_template("add_new_section.html", sections=sections,total_sections=total_sections, total_books=total_books)



@add_new_section.route('/add_book/<int:section_id>', methods=['GET', 'POST'])
def add_book(section_id):
    if request.method == 'POST':
        try:
            # Extract form data
            name = request.form['name']
            author = request.form['author']

            # Handle file upload for PDF and image
            pdf_path = None
            if 'pdf' in request.files:
                pdf_file = request.files['pdf']
                if pdf_file.filename != '':
                    pdf_filename = secure_filename(pdf_file.filename)
                    upload_dir = os.path.join('static', 'uploads', 'books')

                    os.makedirs(upload_dir, exist_ok=True)  # Create directory if it doesn't exist
                    pdf_path = os.path.join(upload_dir, pdf_filename)
                    pdf_file.save(pdf_path)

            image_path = None
            if 'image' in request.files:
                image_file = request.files['image']
                if image_file.filename != '':
                    image_filename = secure_filename(image_file.filename)
                    upload_dir = os.path.join('static', 'uploads', 'books')

                    os.makedirs(upload_dir, exist_ok=True)  # Create directory if it doesn't exist
                    image_path = os.path.join(upload_dir, image_filename)
                    image_file.save(image_path)

            # Insert book data into the books table
            insert_book(section_id, name, pdf_path, author, image_path)
            print("Book inserted successfully")
        except Exception as e:
            print("Error inserting book:", e)

        # Redirect to the section page after adding the book
        return redirect(url_for('add_new_section.section_books', section_id=section_id))

    # Render the add book form template
    return render_template("add_book.html")

@add_new_section.route('/section_books/<int:section_id>', methods=['GET'])
def section_books(section_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    try:
        # Retrieve section name
        c.execute("SELECT section_name FROM sections WHERE id = ?", (section_id,))
        section_name = c.fetchone()[0]

        # Retrieve books of the specified section along with the section name
        c.execute("""
            SELECT books.*, sections.section_name 
            FROM books 
            INNER JOIN sections ON books.section_id = sections.id 
            WHERE books.section_id = ?
        """, (section_id,))
        books = c.fetchall()

        # Iterate through books and fetch feedback for each book
        book_list = []
        for book in books:
            book_id = book[0]  # Assuming book ID is stored in the first column
            # Retrieve feedbacks and ratings for the book from the Requests table
            c.execute("SELECT feedback, rating FROM Requests WHERE book_id = ?", (book_id,))
            feedback_data = c.fetchall()
            # Filter out None ratings and calculate average rating and total number of ratings
            valid_ratings = [rating for _, rating in feedback_data if rating is not None]
            avg_rating = sum(valid_ratings) / len(valid_ratings) if valid_ratings else 0
            num_ratings = len(valid_ratings)

            # Create a dictionary for the book and add feedback data, average rating, and number of ratings
            book_dict = {
                'id': book[0],
                'section_id': book[1],
                'name': book[2],
                'author': book[3],
                'pdf': book[4],
                'image': book[5],
                'feedback_data': feedback_data,
                'avg_rating': avg_rating,
                'num_ratings': num_ratings
            }
            book_list.append(book_dict)
             
    except sqlite3.Error as e:
        print("Error retrieving books:", e)
        book_list = []
        section_name = ""  # Set section name to empty string if not found
    finally:
        conn.close()

    # Render template with book details and feedback
    return render_template('section_books.html', section_name=section_name, books=book_list)



# Flask route to delete a section and associated books
@add_new_section.route('/delete_section/<int:section_id>', methods=['POST'])
def delete_section(section_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    try:
        # Delete the books associated with the section
        c.execute("DELETE FROM books WHERE section_id = ?", (section_id,))
        # Delete the section from the database
        c.execute("DELETE FROM sections WHERE id = ?", (section_id,))
        conn.commit()
    except sqlite3.Error as e:
        print("Error deleting section:", e)
    finally:
        conn.close()
    # Redirect to the section page after deletion
    return redirect(url_for('add_new_section.show_add_new_section')) 

# Flask route to delete a book
@add_new_section.route('/delete_book/<int:book_id>', methods=['POST'])
def delete_book(book_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    try:
        # Retrieve the section ID of the book to be deleted
        c.execute("SELECT section_id FROM books WHERE id = ?", (book_id,))
        section_id = c.fetchone()[0]
        
        # Delete the book from the database
        c.execute("DELETE FROM books WHERE id = ?", (book_id,))
        conn.commit()
    except sqlite3.Error as e:
        print("Error deleting book:", e)
    finally:
        conn.close()
    # Redirect to the section page after deletion
    return redirect(url_for('add_new_section.section_books', section_id=section_id))

@add_new_section.route('/update_section/<int:section_id>', methods=['GET', 'POST'])
def update_section(section_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    if request.method == 'POST':
        try:
            # Extract form data
            section_name = request.form['title']
            date_created = request.form['dateCreated']
            description = request.form['description']

            # Check if image file is uploaded
            if 'image' in request.files:
                image_file = request.files['image']
                if image_file.filename != '':
                    filename = secure_filename(image_file.filename)
                    upload_dir = os.path.join('static', 'uploads', 'sections')
                    os.makedirs(upload_dir, exist_ok=True)  # Create directory if it doesn't exist
                    image_path = os.path.join(upload_dir, filename)
                    image_file.save(image_path)
                else:
                    # Retain the existing image path if no new image is uploaded
                    c.execute("SELECT image FROM sections WHERE id = ?", (section_id,))
                    image_path = c.fetchone()[0]
            else:
                # Retain the existing image path if image field is not included in the request
                c.execute("SELECT image FROM sections WHERE id = ?", (section_id,))
                image_path = c.fetchone()[0]

            # Update the section details in the database
            c.execute("""
                UPDATE sections 
                SET section_name = ?, date_created = ?, description = ?, image = ? 
                WHERE id = ?
            """, (section_name, date_created, description, image_path, section_id))
            conn.commit()
            print("Section updated successfully")
        except sqlite3.Error as e:
            print("Error updating section:", e)
        finally:
            conn.close()
        return redirect(url_for('add_new_section.show_add_new_section')) 
    else:
        try:
            # Retrieve section details from the database
            c.execute("SELECT * FROM sections WHERE id = ?", (section_id,))
            section = c.fetchone()
        except sqlite3.Error as e:
            print("Error retrieving section details:", e)
            section = None
        finally:
            conn.close()
        return render_template("update_section.html", section=section)




@add_new_section.route('/update_book/<int:book_id>', methods=['POST'])
def update_book(book_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    try:
        # Extract form data
        name = request.form['title']
        author = request.form['author']
        
        # Check if PDF file is uploaded
        if 'pdf' in request.files:
            pdf_file = request.files['pdf']
            if pdf_file.filename != '':
                pdf_filename = secure_filename(pdf_file.filename)
                upload_dir = os.path.join('static', 'uploads', 'books')

                os.makedirs(upload_dir, exist_ok=True)  # Create directory if it doesn't exist
                pdf_path = os.path.join(upload_dir, pdf_filename)
                pdf_file.save(pdf_path)
            else:
                # If no PDF file is uploaded, retain the existing PDF path
                c.execute("SELECT pdf FROM books WHERE id = ?", (book_id,))
                pdf_path = c.fetchone()[0]
        else:
            # If PDF file field is not included in the request, retain the existing PDF path
            c.execute("SELECT pdf FROM books WHERE id = ?", (book_id,))
            pdf_path = c.fetchone()[0]
        
        # Check if image file is uploaded
        if 'image' in request.files:
            image_file = request.files['image']
            if image_file.filename != '':
                image_filename = secure_filename(image_file.filename)
                upload_dir = os.path.join('static', 'uploads', 'books')

                os.makedirs(upload_dir, exist_ok=True)  # Create directory if it doesn't exist
                image_path = os.path.join(upload_dir, image_filename)
                image_file.save(image_path)
            else:
                # If no image file is uploaded, retain the existing image path
                c.execute("SELECT image FROM books WHERE id = ?", (book_id,))
                image_path = c.fetchone()[0]
        else:
            # If image file field is not included in the request, retain the existing image path
            c.execute("SELECT image FROM books WHERE id = ?", (book_id,))
            image_path = c.fetchone()[0]
        
        # Retrieve the section ID of the book
        c.execute("SELECT section_id FROM books WHERE id = ?", (book_id,))
        section_id = c.fetchone()[0]
        
        # Update the book details in the database
        c.execute("UPDATE books SET name = ?, author = ?, pdf = ?, image = ? WHERE id = ?", (name, author, pdf_path, image_path, book_id))
        conn.commit()
        print("Book updated successfully")
    except sqlite3.Error as e:
        print("Error updating book:", e)
    finally:
        conn.close()
    # Redirect to the section books page after updating the book
    return redirect(url_for('add_new_section.section_books', section_id=section_id))





