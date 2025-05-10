
from flask import Flask, render_template, request, redirect, flash, session, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta,date
from flask_mail import Mail, Message
# from datetime import date
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
import sys

from fpdf import FPDF
import bcrypt
from flask import jsonify


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
# app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@localhost/library_management_system'
app.config['SQLALCHEMY_DATABASE_URI'] ='sqlite:///rocky.db'



db = SQLAlchemy(app)



# Initialize Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Use your email service provider's SMTP server
app.config['MAIL_PORT'] = 587  # Port for outgoing email
app.config['MAIL_USE_TLS'] = True  # Use TLS encryption
app.config['MAIL_USERNAME'] = '####'  # Your email address
app.config['MAIL_PASSWORD'] = '####'  # Your email password

mail = Mail(app)



# Define admin credentials
ADMIN_EMAIL = "vish@gmail.com"
ADMIN_PASSWORD = "Vish@123"


class Books(db.Model):
    # srno = db.Column(db.Integer, primary_key=True)
    b_id = db.Column(db.Integer, nullable=False,primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    writer = db.Column(db.String(50), nullable=False)
    copy = db.Column(db.Integer)
    pdf = db.Column(db.LargeBinary)


class Students(db.Model):
    prn = db.Column(db.Integer, primary_key=True)
    s_name = db.Column(db.String(50), nullable=False)
    s_branch = db.Column(db.String(50), nullable=False)
    phone_num = db.Column(db.Integer, nullable=False)
    emai = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(100))



class Applys(db.Model):
    app_id = db.Column(db.Integer, primary_key=True)
    prn = db.Column(db.Integer, db.ForeignKey('students.prn'))
    b_id = db.Column(db.Integer, db.ForeignKey('books.b_id'))
    b_name = db.Column(db.String(50))
    i_date = db.Column(db.Date)
    r_date = db.Column(db.Date)
    due_date = db.Column(db.Date)
    late_return_charge = db.Column(db.Integer)

    def calculate_late_return_charge(self):
        # Calculate the due datetime by adding 7 days to the due_date
        due_datetime = datetime.combine(self.due_date, datetime.min.time()) + timedelta(days=7)

        if datetime.now() > due_datetime:
            # Calculate the number of days late
            days_late = (datetime.now() - due_datetime).days
            # Charge 2 rs per day late
            return 2 * days_late
        else:
            return 0






    student = db.relationship('Students', primaryjoin="Applys.prn == Students.prn", backref='book_applications')
    book = db.relationship('Books', primaryjoin="Applys.b_id == Books.b_id", backref='book_applications')





@app.route('/')
def home():
    if 'prn' in session:
        return render_template('index.html')
    else:
        flash('You must be logged in'
              ''
              ''
              ' to access the dashboard.', 'error')
        return redirect('/login')



@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            flash('Admin login successful', 'success')
            return redirect('/admin_dashboard')
        else:
            flash('Admin login failed. Please check your credentials.', 'error')

    return render_template('admin_login.html')


@app.route('/admin_dashboard')
def admin_dashboard():
    if 'admin_logged_in' in session:
        return render_template('admin_dashboard.html')
    return render_template('admin_login.html')



@app.route('/student_profile/<int:prn>', methods=['GET'])
def student_profile(prn):
    student = Students.query.filter_by(prn=prn).first()

    if student:
        # Retrieve the student's applied books
        applied_books = Applys.query.filter_by(prn=prn).all()

        return render_template('student_profile.html', student=student, applied_books=applied_books)

    # Handle the case where the student with the given PRN is not found
    return render_template('student_not_found.html')



PER_PAGE = 5  # Number of items per page

# Your models definition here

@app.route('/dashboard', methods=['GET', 'POST'])
def student_dashboard():
    if 'prn' in session:
        student_name = session['s_name']
        student_prn = session['prn']

        page = request.args.get('page', 1, type=int)
        search_query = request.form.get('search_query', '')

        if request.method == 'POST':
            # Modify the query to filter books by name or writer matching the search query
            books_query = Books.query.filter((Books.name.ilike(f"%{search_query}%")) | (Books.writer.ilike(f"%{search_query}%")))
        else:
            books_query = Books.query

        books_pagination = books_query.paginate(page=page, per_page=PER_PAGE)

        return render_template('dashboard.html', student_name=student_name, student_prn=student_prn, books=books_pagination, search_query=search_query)
    else:
        flash('You must be logged in to access the dashboard.', 'error')
        return redirect('/login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        prn = request.form['prn']
        branch = request.form['branch']
        email = request.form['email']
        password = request.form['password']
        phone_num = request.form['phone_num']

        # Check if the PRN or username already exists
        existing_student = Students.query.filter_by(prn=prn).first()
        if existing_student:
            flash('PRN already exists', 'error')
            return redirect('/register')

        # Create a new student with the provided fields
        new_student = Students(s_name=name, prn=prn, s_branch=branch, emai=email, password=password, phone_num=phone_num)
        db.session.add(new_student)
        db.session.commit()
        flash('Registration successful', 'success')
        return redirect('/login')
    return render_template('register.html')





@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        prn = request.form.get('prn')
        password = request.form.get('password')
        student = Students.query.filter_by(prn=prn).first()
        if student and student.password == password:
            session['prn'] = prn  # Store the PRN in the session
            session['s_name'] = student.s_name
            return redirect('/dashboard')
        flash('Login failed. Please check your PRN and password.')
    return render_template('login.html')



@app.route('/addbook', methods=['GET', 'POST'])
def addbook():
    if 'admin_logged_in' in session:
        if request.method == 'POST':
            book_id = request.form.get('book_id')
            name = request.form.get('name')
            writer = request.form.get('writer')
            copy = request.form.get('copy')
            pdf_file = request.files['pdf_file']  # Get the uploaded PDF file

            # Check if all fields are provided and the PDF file exists
            if book_id and name and writer and copy and pdf_file:
                # Read the PDF file content
                pdf_data = pdf_file.read()

                # Add entry to the database
                entry = Books(b_id=book_id, name=name, writer=writer, copy=copy, pdf=pdf_data)
                db.session.add(entry)
                db.session.commit()

                flash('Book added successfully.', 'success')
                return redirect('/addbook')
            else:
                flash('All fields are required, including the PDF file.', 'error')

        return render_template('addbook.html')
    return render_template('admin_login.html')



@app.route("/view", methods=['GET', 'POST'])
def view():
    if 'admin_logged_in' in session:
        if request.method == 'POST':
            search_query = request.form.get('search_query')
            books = Books.query.filter(
                (Books.name.ilike(f'%{search_query}%')) |
                (Books.writer.ilike(f'%{search_query}%'))
            ).all()
        else:
            books = Books.query.all()

        return render_template('view.html', books=books)

    return render_template('admin_login.html')


from flask import send_file, abort

@app.route("/view_pdf/<int:book_id>")
def view_pdf(book_id):
    # Fetch the book from the database based on the book_id
    book = Books.query.get_or_404(book_id)
    # Check if the book has a PDF file
    if book.pdf:
        # Return the PDF file for viewing
        return send_file(
            io.BytesIO(book.pdf),
            mimetype='application/pdf',
            as_attachment=False
        )
    else:
        # Handle the case where the book doesn't have a PDF file
        abort(404)






from flask import send_file
import os


@app.route("/download_pdf/<int:book_id>")
def download_pdf(book_id):
    # Fetch the book from the database based on the book_id
    book = Books.query.get_or_404(book_id)

    # Check if the book has a PDF file
    if book.pdf:
        # Define the path to the PDF file
        pdf_path = f"book_{book_id}.pdf"

        # Write the PDF content to a temporary file
        with open(pdf_path, "wb") as f:
            f.write(book.pdf)

        # Return the PDF file for downloading
        return send_file(pdf_path, as_attachment=True)
    else:
        # Handle the case where the book doesn't have a PDF file
        return "No PDF available for this book"


@app.route("/view_student" )
def view_student():
    students = Students.query.all()
    return render_template('view_student.html', students=students)



from flask import request
import io

@app.route("/edit/<string:b_id>", methods=['GET', 'POST'])
def edit(b_id):
    if 'admin_logged_in' in session:
        if request.method == 'POST':
            book_id = request.form.get('book_id')
            name = request.form.get('name')
            writer = request.form.get('writer')
            copy = request.form.get('copy')

            # Fetch the book from the database
            book = Books.query.filter_by(b_id=b_id).first()

            # Get the existing PDF data
            pdf_data = book.pdf if book else None

            # Check if a new PDF file is uploaded
            if 'pdf_file' in request.files:
                pdf_file = request.files['pdf_file']
                if pdf_file and pdf_file.filename:
                    # Read the PDF file content
                    pdf_data = pdf_file.read()

            # Update the book entry with the new data
            if book:
                book.b_id = book_id
                book.name = name
                book.writer = writer
                book.copy = copy

                # If new PDF data exists, update it
                if pdf_data:
                    book.pdf = pdf_data

                # Commit the changes to the database
                db.session.commit()

                # Redirect to the view page after editing the book
                return redirect('/view')

        # If the request method is GET, render the edit form
        book = Books.query.filter_by(b_id=b_id).first()
        return render_template('edit.html', book=book)

    # If the user is not logged in as admin, redirect to the admin login page
    return render_template('admin_login.html')




@app.route("/delete/<string:b_id>", methods=['GET', 'POST'])
def delete(b_id):
    if 'admin_logged_in' in session:
        book = Books.query.filter_by(b_id=b_id).first()

        if request.method == 'POST':
            action = request.form.get('action')

            if action == 'delete_book':
                # No try block, handle exceptions through implicit error handling
                db.session.delete(book)
                db.session.commit()  # Commit the deletion
                flash("Book deleted successfully.", 'success')
                return redirect('/view')  # Redirect to the view page after deleting the book

            elif action == 'delete_copies':
                copies_to_delete = int(request.form['copies'])
                if copies_to_delete <= book.copy:
                    book.copy -= copies_to_delete
                    db.session.commit()
                    flash(f"{copies_to_delete} copies deleted successfully.", 'success')
                    return redirect('/view')
                else:
                    error_message = "Invalid number of copies to delete."
                    flash(error_message, 'error')
                    return render_template('delete.html', book=book, error_message=error_message)

        return render_template('delete.html', book=book)

    return render_template('admin_login.html')




@app.route('/apply/<int:b_id>/<string:b_name>', methods=['GET', 'POST'])
def apply(b_id, b_name):
    # Check if the student is logged in
    if 'prn' in session:
        student_prn = session['prn']  # Get the student's PRN from the session

        # Check if the student has already applied for the same book and not returned it
        existing_application = Applys.query.filter_by(prn=student_prn, b_id=b_id, r_date=None).first()

        if existing_application:
            flash("You have already applied for this book and not returned it.", 'error')
            return redirect('/dashboard')

        book = Books.query.filter_by(b_id=b_id).first()
        if book is not None and book.copy > 0:
            # Render a confirmation page to confirm the book application
            return render_template('apply_confirmation.html', book=book, b_name=b_name)

    flash("Book copy count is 0 or you are not logged in. Application not allowed.", 'error')
    return redirect('/dashboard')



@app.route('/confirm_apply/<int:b_id>/<string:b_name>', methods=['POST'])
def confirm_apply(b_id, b_name):
    # Check if the student is logged in
    if 'prn' in session:
        book = Books.query.filter_by(b_id=b_id).first()
        if book is not None and book.copy > 0:
            student_prn = session['prn']  # Get the student's PRN from the session

            # Check if the student has already applied for the same book and not returned it
            existing_application = Applys.query.filter_by(prn=student_prn, b_id=b_id, r_date=None).first()

            if existing_application:
                flash("You have already applied for this book and not returned it.", 'error')
                return redirect('/dashboard')

            student = Students.query.filter_by(prn=student_prn).first()

            student_email = student.emai
            msg = Message('All Book Confirmations Done', sender='vk0984242@gmail.com', recipients=[student_email])
            msg.body = f'You have successfully applied {b_name} Book. Please return in 7 days. If you do not return, you will need to pay an extra charge of 15 rs/day.'
            mail.send(msg)

            # Get the current date and time
            current_datetime = datetime.now()
            issued_date = current_datetime.date()
            issued_time = current_datetime.time()

            due_date = issued_date + timedelta(days=7)  # Assuming the due date is 7 days from the issuing date

            # Calculate late return charge (initially set to 0)
            late_return_charge = 0

            # Reduce the copy count by 1
            book.copy -= 1

            # Insert a new entry into the "Applys" table
            new_application = Applys(
                prn=student_prn,
                b_id=b_id,
                b_name=b_name,
                i_date=issued_date,
                r_date=None,
                due_date=due_date,
                late_return_charge=late_return_charge
            )

            db.session.add(new_application)
            db.session.commit()

            # Generate PDF content
            pdf_content = BytesIO()
            pdf_canvas = canvas.Canvas(pdf_content, pagesize=letter)
            pdf_canvas.drawString(100, 650, f'Student PRN: {student_prn}')
            pdf_canvas.drawString(100, 630, f'Student Name: {student.s_name}')
            pdf_canvas.drawString(100, 750, f'Application ID: {new_application.app_id}')
            pdf_canvas.drawString(100, 730, f'Book Name: {b_name}')
            pdf_canvas.drawString(100, 710, f'Book ID: {book.b_id}')
            pdf_canvas.drawString(100, 690, f'Issued Date: {issued_date}')
            pdf_canvas.drawString(100, 670, f'Issued Time: {issued_time}')
            pdf_canvas.save()
            pdf_content.seek(0)

            # Attach the BytesIO object to the Flask response
            return send_file(pdf_content, as_attachment=True, download_name=f'receipt_{new_application.app_id}.pdf', mimetype='application/pdf')
            # return redirect('/dashboard')


        else:
            flash("Book copy count is 0. Application not allowed")
            return redirect('/dashboard')




@app.route('/issuebook', methods=['GET', 'POST'])
def issuebook():
    if 'admin_logged_in' in session:
        if request.method == 'POST':
            search_query = request.form.get('search_query')
            # Perform a query based on the search criteria
            applied_entries = Applys.query.filter(
                (Applys.b_name.ilike(f'%{search_query}%')) |  # Search by book name
                (Applys.prn.ilike(f'%{search_query}%')) |  # Search by PRN
                (Applys.b_id.ilike(f'%{search_query}%'))  # Search by book ID
            ).all()
        else:
            # If no search query is provided, get all applied entries
            applied_entries = Applys.query.all()

        return render_template('issuebook.html', applied_entries=applied_entries)

    # If not logged in as admin, redirect to the login page
    return render_template('admin_login.html')



@app.route('/applied_history', methods=['GET', 'POST'])
def applied_history():
    # Check if the student is logged in
    if 'prn' in session:
        student_prn = session['prn']  # Get the student's PRN from the session

        # Set default value for search_query
        search_query = ''

        # Check if the form is submitted
        if request.method == 'POST':
            search_query = request.form.get('search_query', '')
            # Modify the query to filter applied entries by book name matching the search query
            applied_entries = Applys.query.filter(Applys.prn == student_prn, Applys.b_name.ilike(f"%{search_query}%")).all()
        else:
            # Query all applied entries if the form is not submitted
            applied_entries = Applys.query.filter_by(prn=student_prn).all()

        return render_template('applied_history.html', applied_entries=applied_entries, search_query=search_query)
    else:
        flash('You must be logged in to view your applied book history.', 'error')
        return redirect('/login')


@app.route('/mark_returned/<int:app_id>', methods=['POST'])
def mark_returned(app_id):
    if 'admin_logged_in' in session:
        application = Applys.query.filter_by(app_id=app_id).first()

        if application:
            # Update the returned date for the application
            returned_date = datetime.now().date()
            application.r_date = returned_date


            # Increment the book's copy count
            book = Books.query.filter_by(b_id=application.b_id).first()
            if book:
                book.copy += 1

            db.session.commit()

            flash('Book marked as returned successfully', 'success')
        else:
            flash('Invalid book application or unauthorized access', 'error')

        return redirect('/issuebook')
    return render_template('admin_login.html')



@app.route('/logout')
def logout():
    if 'prn' in session:
        # Clear the session data for the logged-in student
        session.pop('prn', None)
        session.pop('s_name', None)

        flash('You have been successfully logged out', 'success')
        return redirect('/login')  # Redirect to the login page after logout
    elif 'admin_logged_in' in session and session['admin_logged_in']:
        # Clear the session data for the admin
        session.pop('admin_logged_in', None)

        flash('Admin logged out successfully', 'success')
        return redirect('/admin/login')  # Redirect to the admin login page after admin logout
    else:
        flash('You are not currently logged in', 'error')

    return redirect('/')  # Redirect to the home page if no user is logged in


@app.route('/admin_logout')
def admin_logout():
    if 'admin_logged_in' in session and session['admin_logged_in']:
        # Clear the admin session data
        session.pop('admin_logged_in', None)
        flash('Admin logged out successfully', 'success')
    else:
        flash('You are not currently logged in as an admin', 'error')

    return redirect('/admin_login')  # Redirect to the admin login page after admin logout





if __name__ == "__main__":
    with app.app_context():
        db.create_all()

        # Fetch all book applications that haven't been returned yet
        pending_applications = Applys.query.filter_by(r_date=None).all()

        # Iterate through each pending application and calculate late return charge
        for application in pending_applications:
            application.late_return_charge = application.calculate_late_return_charge()

        # Commit the changes to the database
        db.session.commit()

    # Run the Flask application
    app.run(debug=True)
