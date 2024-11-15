from flask import Blueprint, render_template, request, redirect, url_for
librarian_login = Blueprint('librarian_login', __name__)
librarian_credentials = {'username': 'librarian123@gmail.com', 'password': 'admin123'}
@librarian_login.route('/librarian_login', methods=['GET', 'POST'])
def librarian_login_page():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == librarian_credentials['username'] and password == librarian_credentials['password']:
            return redirect(url_for('add_new_section.show_add_new_section'))
        else:
            return render_template("librarian_login.html", error="Invalid username or password")
    else:
        return render_template("librarian_login.html")
@librarian_login.route('/librarian_dashboard')
def librarian_dashboard():
    return render_template("librarian_login.html")
