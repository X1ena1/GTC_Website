# Importing files
import os
import mysql.connector
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename

app = Flask(__name__)

# --- CONFIGURATION ---
app.secret_key = 'a_very_secret_key_for_contractor_app'

# Set the directory for uploaded files (e.g., inside the static folder)
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Ensure the directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# --- DATABASE CONFIGURATION ---
# >>>>>> !!! REPLACE THESE WITH YOUR ACTUAL MYSQL CREDENTIALS !!! <<<<<<
DB_CONFIG = {
    'host': '127.0.0.1',    # Default for local server (WAMP/XAMPP/MAMP)
    'user': 'root',         # Default user
    'password': '',         # Common default for 'root' if no password set
    'port': 3306,           # Standard MySQL/MariaDB port (Try 3307 if 3306 fails)
    'database': 'Rebates'   # <<< Use the database name you intend to use
}
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>


# Helper function to get DB connection (MUST be defined before it's called)
def get_db_connection():
    """Establishes a connection to the MySQL database."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Error connecting to MySQL: {err}")
        return None


# --- PUBLIC ROUTES ---

@app.route("/")
def index():
    return render_template('index.html')

@app.route('/impact')
def impact():
    """Renders the Impact page template."""
    return render_template('impact.html')

@app.route('/opportunities')
def opportunities():
    """Renders the Opportunities page."""
    return "<h1>Opportunities Page Coming Soon!</h1><p>This is where users can view available energy projects.</p>"

@app.route('/rebates')
def rebates():
    """Renders the Rebates page."""
    return "<h1>Rebates Page Coming Soon!</h1><p>This is where users can find details on available rebates.</p>"

@app.route('/about')
def about():
    """Renders the About page."""
    return "<h1>About Page Coming Soon!</h1><p>Information about the system and the University program.</p>"

@app.route('/forgot-password')
def forgot_password():
    """Placeholder route for the Forgot Password page."""
    return "<h1>Forgot Password Page</h1><p>Instructions for resetting the password will go here.</p>"


# --- UNIVERSAL LOGOUT (MODIFIED) ---

@app.route('/logout')
def logout():
    """Logs the user out by clearing all contractor and standard user sessions."""
    # Contractor session
    session.pop('contractor_logged_in', None)
    session.pop('username', None) 
    # Standard user session
    session.pop('user_logged_in', None)
    session.pop('user_username', None)
    
    return redirect(url_for('index'))


# --- CONTRACTOR AUTHENTICATION ROUTES ---

# 1. SHOW THE CONTRACTOR LOGIN FORM
@app.route('/contractor-login', methods=['GET'])
def contractor_login():
    """Renders the contractor login page template."""
    return render_template('contractor_login.html')

# 2. PROCESS THE CONTRACTOR LOGIN FORM (DEMO BYPASS)
@app.route('/login-submit', methods=['POST'])
def login_submit():
    """Handles form submission, bypassing authentication for the demo."""
    username = request.form.get('username')
    session['contractor_logged_in'] = True
    session['username'] = username if username else 'Demo Contractor'
    return redirect(url_for('contractor_dashboard'))

# 3. THE PROTECTED CONTRACTOR DASHBOARD ROUTE
@app.route('/contractor-dashboard')
def contractor_dashboard():
    """Renders the protected dashboard."""
    if 'contractor_logged_in' in session and session['contractor_logged_in']:
        return render_template('contractor_dashboard.html')
    else:
        return redirect(url_for('contractor_login'))


# --- STANDARD USER AUTHENTICATION ROUTES (NEW) ---

# 1. SHOW THE USER LOGIN FORM
@app.route('/user-login', methods=['GET'])
def user_login():
    """Renders the standard user login page template."""
    return render_template('user_login.html')

# 2. PROCESS THE USER LOGIN FORM (DEMO BYPASS)
@app.route('/user-login-submit', methods=['POST'])
def user_login_submit():
    """Handles standard user login submission, bypassing authentication for the demo."""
    username = request.form.get('username')
    
    session['user_logged_in'] = True
    session['user_username'] = username if username else 'Demo User'
    
    return redirect(url_for('user_dashboard'))

# 3. THE PROTECTED USER DASHBOARD ROUTE
@app.route('/user-dashboard')
def user_dashboard():
    """Renders the protected standard user dashboard."""
    if 'user_logged_in' in session and session['user_logged_in']:
        # This assumes you have created user_dashboard.html
        return render_template('user_dashboard.html', username=session.get('user_username', 'User'))
    else:
        return redirect(url_for('user_login'))


# --- APPLICATION/DATA ROUTES ---

# 5. NEW EIA APPLICATION FORM (GET)
@app.route('/new-eia-application')
def new_eia_application():
    """Renders the form for a New Energy Incentive Application."""
    if 'contractor_logged_in' in session and session['contractor_logged_in']:
        return render_template('new_eia_application.html')
    else:
        return redirect(url_for('contractor_login'))

# 6. VIEW ALL APPLICATIONS ROUTE (MODIFIED to show APPLICANT/UNIT data)
@app.route('/view-all-applications')
def view_all_applications():
    """Fetches all data from the APPLICANT table (which stores department/unit info)."""
    if 'contractor_logged_in' not in session or not session['contractor_logged_in']:
        return redirect(url_for('contractor_login'))
    
    conn = get_db_connection()
    departments = [] # Variable named for clarity, as it shows Department info
    
    if conn is None:
        return render_template('view_all_applications.html', departments=departments)

    try:
        cursor = conn.cursor(dictionary=True)
        
        # Selecting the five columns matching your APPLICANT table structure
        query = """
        SELECT Department_ID, Department_Name, Contact_Email, School, District
        FROM APPLICANT
        ORDER BY Department_Name ASC
        """
        cursor.execute(query)
        departments = cursor.fetchall()
        cursor.close()
        
    except mysql.connector.Error as err:
        print(f"Database query error in view_all_applications (APPLICANT table): {err}")
        
    finally:
        if conn and conn.is_connected():
            conn.close()

    return render_template('view_all_applications.html', departments=departments)


# 7. EIA FORM SUBMISSION (POST)
@app.route('/submit-eia', methods=['POST'])
def submit_eia():
    """Handles the submission of the New EIA Application form data, including file upload."""
    if 'contractor_logged_in' not in session:
        return redirect(url_for('contractor_login'))
    
    conn = get_db_connection()
    if conn is None:
        return "Database connection error. Application not saved.", 500

    try:
        cursor = conn.cursor()
        
        # 1. Get Form Data
        department = request.form.get('department')
        project_title = request.form.get('project_title')
        project_type = request.form.get('project_type')
        sponsor = request.form.get('sponsor')
        description = request.form.get('description')
        uploaded_file_path = "N/A"
        
        # 2. Handle File Upload
        if 'documents' in request.files:
            file = request.files['documents']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                full_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(full_path)
                uploaded_file_path = os.path.join('static/uploads', filename).replace('\\', '/')

        # 3. Prepare and Execute SQL INSERT
        sql = """
        INSERT INTO applications 
        (department, project_title, project_type, application_sponsor, project_description, supporting_documents_path, status, submitted_by)
        VALUES (%s, %s, %s, %s, %s, %s, 'Pending', %s)
        """
        data = (
            department,
            project_title,
            project_type,
            sponsor,
            description,
            uploaded_file_path,
            session.get('username', 'Unknown Contractor')
        )
        
        cursor.execute(sql, data)
        conn.commit()
        cursor.close()
        
        return redirect(url_for('contractor_dashboard'))

    except mysql.connector.Error as err:
        print(f"Database insertion error: {err}")
        conn.rollback()
        return "Error submitting application to database.", 500
        
    finally:
        if conn and conn.is_connected():
            conn.close()

# Running application
if __name__ == "__main__":
    app.run(debug=True)