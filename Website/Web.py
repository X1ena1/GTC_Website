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
    # Check if a user is logged in and redirect them to their respective dashboard
    if session.get('user_logged_in'):
        return redirect(url_for('user_dashboard'))
    elif session.get('contractor_logged_in'):
        return redirect(url_for('contractor_dashboard'))
    else:
        # If no one is logged in, show the public homepage
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

# 3. THE PROTECTED CONTRACTOR DASHBOARD ROUTE (UPDATED FOR DYNAMIC COUNTS AND FEED)
@app.route('/contractor-dashboard')
def contractor_dashboard():
    """
    Renders the protected dashboard, fetching summary counts 
    of applications (Pending, Approved, Rejected) and the Status Feed.
    """
    if 'contractor_logged_in' not in session or not session['contractor_logged_in']:
        return redirect(url_for('contractor_login'))

    conn = get_db_connection()
    status_counts = {'Pending': 0, 'Approved': 0, 'Rejected': 0, 'Total': 0}
    status_feed_items = []  # Initialize the list for the feed

    if conn is None:
        # Pass the empty list to the template in case of error
        return render_template('contractor_dashboard.html', counts=status_counts, feed_items=status_feed_items, username=session.get('username'))

    try:
        cursor = conn.cursor(dictionary=True)  # Use dictionary=True for easy access by column name
        
        # 1. Query for Status Counts (USING APPLICANT)
        query_counts = """
        SELECT status, COUNT(*)
        FROM APPLICANT
        GROUP BY status;
        """
        cursor.execute(query_counts)
        results = cursor.fetchall()

        total = 0
        for row in results:
            status_key = row['status'].strip().capitalize()
            if status_key in status_counts:
                status_counts[status_key] = row['COUNT(*)']
            total += row['COUNT(*)']
            
        status_counts['Total'] = total
        
        # 2. Query for Status Feed Items (Last 5 Recent Applications/Updates) (USING APPLICANT)
        query_feed = """
        SELECT id, project_title, status
        FROM APPLICANT
        ORDER BY id DESC
        LIMIT 5;
        """
        cursor.execute(query_feed)
        feed_results = cursor.fetchall()
        
        # Process results into a simple list of strings for the template
        for item in feed_results:
            # Note: Assuming APPLICANT has 'id', 'project_title', and 'status' columns
            feed_message = f"EIA #{item['id']} ({item['project_title']}) is currently: **{item['status']}**"
            status_feed_items.append(feed_message)

        cursor.close()
        
    except mysql.connector.Error as err:
        print(f"Database query error fetching dashboard data from APPLICANT: {err}")
        
    finally:
        if conn and conn.is_connected():
            conn.close()

    # Pass BOTH counts and feed_items to the template
    return render_template('contractor_dashboard.html', 
                           counts=status_counts, 
                           feed_items=status_feed_items,
                           username=session.get('username', 'Demo Contractor'))


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

# 3. THE PROTECTED USER DASHBOARD ROUTE (UPDATED TO FETCH USER'S APPLICATIONS)
@app.route('/user-dashboard')
def user_dashboard():
    """Renders the protected standard user dashboard, showing their applications."""
    if 'user_logged_in' not in session or not session['user_logged_in']:
        return redirect(url_for('user_login'))

    username = session.get('user_username', 'Demo User')
    user_applications = []
    
    conn = get_db_connection()
    if conn is None:
        return render_template('user_dashboard.html', username=username, applications=user_applications)

    try:
        cursor = conn.cursor(dictionary=True)
        
        # Query to get the user's specific applications (USING APPLICANT)
        query = """
        SELECT id, project_title, status, application_sponsor, submitted_by
        FROM APPLICANT
        WHERE submitted_by = %s 
        ORDER BY id DESC
        LIMIT 10;
        """
        cursor.execute(query, (username,)) 
        user_applications = cursor.fetchall()
        cursor.close()
        
    except mysql.connector.Error as err:
        print(f"Database query error fetching user dashboard applications from APPLICANT: {err}")
        
    finally:
        if conn and conn.is_connected():
            conn.close()

    return render_template('user_dashboard.html', 
                           username=username, 
                           applications=user_applications)

# 4. SHOW THE USER SIGNUP/REGISTRATION FORM
@app.route('/user-signup', methods=['GET'])
def user_signup():
    """Renders the standard user registration page template."""
    return render_template('user_signup.html')


# --- APPLICATION/DATA ROUTES ---

# 5. CONTRACTOR'S NEW EIA APPLICATION FORM (GET) - NOW PASSES DYNAMIC DASHBOARD URL
@app.route('/new-eia-application')
def new_eia_application():
    """Renders the form for a New Energy Incentive Application (Contractor access)."""
    if 'contractor_logged_in' in session and session['contractor_logged_in']:
        return render_template('new_eia_application.html', 
                               dashboard_url=url_for('contractor_dashboard'))
    else:
        return redirect(url_for('contractor_login'))
        
# 5A. USER'S NEW EIA APPLICATION FORM (GET) - NOW PASSES DYNAMIC DASHBOARD URL
@app.route('/user-new-eia-application')
def user_new_eia_application():
    """Renders the form for a New Energy Incentive Application (User/Department access)."""
    if 'user_logged_in' in session and session['user_logged_in']:
        return render_template('new_eia_application.html', 
                               dashboard_url=url_for('user_dashboard'))
    else:
        return redirect(url_for('user_login'))


# 6. VIEW ALL APPLICATIONS ROUTE (Contractor View) - FIXED TO QUERY 'APPLICANT' TABLE
@app.route('/view-all-applications')
def view_all_applications():
    """Fetches all applications data for the contractor view (from APPLICANT table)."""
    if 'contractor_logged_in' not in session or not session['contractor_logged_in']:
        return redirect(url_for('contractor_login'))
    
    conn = get_db_connection()
    applications = [] 
    
    if conn is None:
        return render_template('view_all_applications.html', applications=applications)

    try:
        cursor = conn.cursor(dictionary=True)
        
        # FIXED: Querying the 'APPLICANT' table to get project data
        query = """
        SELECT id, department, project_title, status, application_sponsor, submitted_by
        FROM APPLICANT
        ORDER BY id DESC
        """
        cursor.execute(query)
        applications = cursor.fetchall()
        cursor.close()
        
    except mysql.connector.Error as err:
        # NOTE: This error will occur if the APPLICANT table is missing columns like 'project_title' or 'status'
        print(f"Database query error in view_all_applications (APPLICANT table): {err}")
        
    finally:
        if conn and conn.is_connected():
            conn.close()

    return render_template('view_all_applications.html', applications=applications)


# 7. CONTRACTOR'S EIA FORM SUBMISSION (POST) (USING APPLICANT)
@app.route('/submit-eia', methods=['POST'])
def submit_eia():
    """Handles the submission of the New EIA Application form data (Contractor submits)."""
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
        
        # 2. Handle File Upload (Code omitted for brevity, but remains in the actual file)
        if 'documents' in request.files:
            file = request.files['documents']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                full_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(full_path)
                uploaded_file_path = os.path.join('static/uploads', filename).replace('\\', '/')

        # 3. Prepare and Execute SQL INSERT (INTO APPLICANT)
        sql = """
        INSERT INTO APPLICANT
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
            session.get('username', 'Unknown Contractor') # Tracks Contractor username
        )
        
        cursor.execute(sql, data)
        conn.commit()
        cursor.close()
        
        return redirect(url_for('contractor_dashboard'))

    except mysql.connector.Error as err:
        print(f"Database insertion error into APPLICANT: {err}")
        conn.rollback()
        return "Error submitting application to database.", 500
        
    finally:
        if conn and conn.is_connected():
            conn.close()

# 7A. USER'S EIA FORM SUBMISSION (POST) (USING APPLICANT)
@app.route('/user-submit-eia', methods=['POST'])
def user_submit_eia():
    """Handles the submission of the New EIA Application form data from a standard user."""
    if 'user_logged_in' not in session:
        return redirect(url_for('user_login'))
    
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
        
        # 2. Handle File Upload (Code omitted for brevity, but remains in the actual file)
        if 'documents' in request.files:
            file = request.files['documents']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                full_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(full_path)
                uploaded_file_path = os.path.join('static/uploads', filename).replace('\\', '/')

        # 3. Prepare and Execute SQL INSERT (INTO APPLICANT)
        sql = """
        INSERT INTO APPLICANT
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
            session.get('user_username', 'Unknown User') # Tracks User/Department username
        )
        
        cursor.execute(sql, data)
        conn.commit()
        cursor.close()
        
        # Redirect back to the user's dashboard
        return redirect(url_for('user_dashboard'))

    except mysql.connector.Error as err:
        print(f"Database insertion error into APPLICANT: {err}")
        conn.rollback()
        return "Error submitting application to database.", 500
        
    finally:
        if conn and conn.is_connected():
            conn.close()


# --- REPORT AND ADMIN ROUTES (NEWLY ADDED PLACEHOLDERS) ---

@app.route('/energy-report')
def energy_report():
    if 'contractor_logged_in' not in session:
        return redirect(url_for('contractor_login'))
    return render_template('report_placeholder.html', report_name='Energy Report')

@app.route('/payment-report')
def payment_report():
    if 'contractor_logged_in' not in session:
        return redirect(url_for('contractor_login'))
    return render_template('report_placeholder.html', report_name='Payment Report')

@app.route('/sponsor-approvals')
def sponsor_approvals():
    if 'contractor_logged_in' not in session:
        return redirect(url_for('contractor_login'))
    return render_template('report_placeholder.html', report_name='Sponsor Approvals')

@app.route('/project-report')
def project_report():
    if 'contractor_logged_in' not in session:
        return redirect(url_for('contractor_login'))
    return render_template('report_placeholder.html', report_name='Project Report')


# Running application
if __name__ == "__main__":
    app.run(debug=True)