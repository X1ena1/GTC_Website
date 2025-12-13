# ==============================================================================
# 🚀 CORE IMPORTS
# ==============================================================================
import os
import mysql.connector
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash

# ==============================================================================
# ⚙️ APP & DATABASE CONFIGURATION
# ==============================================================================
app = Flask(__name__)

# --- APP CONFIG ---
app.secret_key = 'a_very_secret_key_for_contractor_app'

# --- UPLOAD CONFIG ---
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- DATABASE CONFIG ---
DB_CONFIG = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '',
    'port': 3306,
    'database': 'Rebates'
}

# --- DB CONNECTION HELPER ---
def get_db_connection():
    """Establishes a connection to the MySQL database."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Error connecting to MySQL: {err}")
        return None

# ==============================================================================
# 🔐 AUTHENTICATION & LOGIN ROUTES
# ==============================================================================

# --- UNIVERSAL LOGOUT ---
@app.route('/logout')
def logout():
    """Logs the user out by clearing all sessions."""
    session.pop('contractor_logged_in', None)
    session.pop('username', None) 
    session.pop('user_logged_in', None)
    session.pop('user_username', None)
    return redirect(url_for('index'))

# --- CONTRACTOR LOGIN FORM ---
@app.route('/contractor-login', methods=['GET'])
def contractor_login():
    """Renders the contractor login page template."""
    return render_template('contractor_login.html')

# --- CONTRACTOR LOGIN SUBMIT (PLAINTEXT BYPASS) ---
@app.route('/login-submit', methods=['POST'])
def login_submit():
    """
    Handles authentication using a TEMPORARY, NON-SECURE plaintext password check.
    (This uses '==' instead of check_password_hash).
    """
    
    email = request.form.get('username')
    password_attempt = request.form.get('password')
    
    conn = get_db_connection()
    if conn is None:
        flash('Could not connect to the database. Try again later.', 'error')
        return redirect(url_for('contractor_login'))

    user = None
    try:
        cursor = conn.cursor(dictionary=True)
        # Assumes your reviewer table is named 'REVIEWER'
        query = "SELECT Employee_ID, Employee_Name, Password_Hash FROM REVIEWER WHERE Email = %s"
        cursor.execute(query, (email,))
        user = cursor.fetchone()
        cursor.close()
        
    except mysql.connector.Error as err:
        print(f"Database query error during login: {err}")
        flash('A database error occurred during login.', 'error')
        return redirect(url_for('contractor_login'))
    finally:
        if conn and conn.is_connected():
            conn.close()

    if user:
        # ⚠️ NON-SECURE BYPASS: Checking plaintext against database value
        if user['Password_Hash'] == password_attempt:
            # --- SUCCESSFUL LOGIN ---
            session['contractor_logged_in'] = True
            session['employee_id'] = user['Employee_ID']
            session['username'] = user['Employee_Name']
            return redirect(url_for('contractor_dashboard'))
        else:
            # Password mismatch
            flash('Invalid username or password.', 'error')
            return redirect(url_for('contractor_login'))
    else:
        # User (Email) not found
        flash('Invalid username or password.', 'error')
        return redirect(url_for('contractor_login'))

# --- TEMPORARY HASH GENERATOR (DELETE ME AFTER SETUP) ---
@app.route('/temp-hash-generator')
def temp_hash_generator():
    """
    Generates and displays a hash for a demo password. 
    THE LOGIN PASSWORD IS: password123
    """
    test_password = 'password123' 
    hashed_password = generate_password_hash(test_password)
    
    # This output goes to your terminal
    print("\n--- COPY THIS REAL HASH STRING ---")
    print(f"PASSWORD: {test_password}")
    print(f"HASH:     {hashed_password}")
    print("----------------------------------\n")
    
    return jsonify({"message": "Hash generated. Check your console/terminal and copy the string."})

# --- USER LOGIN & SUBMIT (DEMO) ---
@app.route('/user-login', methods=['GET'])
def user_login():
    """Renders the standard user login page template."""
    return render_template('user_login.html')

@app.route('/user-login-submit', methods=['POST'])
def user_login_submit():
    """Handles standard user login submission, bypassing authentication for the demo."""
    username = request.form.get('username')
    session['user_logged_in'] = True
    session['user_username'] = username if username else 'Demo User'
    return redirect(url_for('user_dashboard'))

# ==============================================================================
# 🏠 DASHBOARD & CORE VIEW ROUTES
# ==============================================================================

# --- INDEX ROUTE ---
@app.route("/")
def index():
    """Renders the appropriate dashboard or the public homepage."""
    if session.get('user_logged_in'):
        return redirect(url_for('user_dashboard'))
    elif session.get('contractor_logged_in'):
        return redirect(url_for('contractor_dashboard'))
    else:
        return render_template('index.html')

# --- CONTRACTOR DASHBOARD ---
@app.route('/contractor-dashboard')
def contractor_dashboard():
    """Renders the protected contractor dashboard."""
    if 'contractor_logged_in' not in session:
        return redirect(url_for('contractor_login'))

    conn = get_db_connection()
    status_counts = {'Pending': 0, 'Approved': 0, 'Rejected': 0, 'Revision Requested': 0, 'Total': 0}
    status_feed_items = []

    if conn is None:
        return render_template('contractor_dashboard.html', counts=status_counts, feed_items=status_feed_items, username=session.get('username'))

    try:
        cursor = conn.cursor(dictionary=True)
        
        # 1. Query for Status Counts
        query_counts = """
        SELECT Status, COUNT(*)
        FROM REBATE
        GROUP BY Status;
        """
        cursor.execute(query_counts)
        results = cursor.fetchall()

        total = 0
        for row in results:
            status_key = row['Status'].strip()
            if status_key in status_counts:
                status_counts[status_key] = row['COUNT(*)']
            total += row['COUNT(*)']
            
        status_counts['Total'] = total
        
        # 2. Query for Status Feed Items (Last 5 Recent Rebates)
        query_feed = """
        SELECT SOP_Number, Building, Status
        FROM REBATE
        ORDER BY SOP_Number DESC
        LIMIT 5;
        """
        cursor.execute(query_feed)
        feed_results = cursor.fetchall()
        
        for item in feed_results:
            feed_message = f"Rebate ID #{item['SOP_Number']} ({item['Building']}) is currently: **{item['Status']}**"
            status_feed_items.append(feed_message)

        cursor.close()
        
    except mysql.connector.Error as err:
        print(f"Database query error fetching dashboard data from REBATE: {err}")
        
    finally:
        if conn and conn.is_connected():
            conn.close()

    return render_template('contractor_dashboard.html', 
                           counts=status_counts, 
                           feed_items=status_feed_items,
                           username=session.get('username', 'Demo Contractor'))

# --- USER DASHBOARD ---
@app.route('/user-dashboard')
def user_dashboard():
    """Renders the protected standard user dashboard."""
    if 'user_logged_in' not in session:
        return redirect(url_for('user_login'))

    username = session.get('user_username', 'Demo User') 
    user_applications = []
    
    conn = get_db_connection()
    if conn is None:
        return render_template('user_dashboard.html', username=username, applications=user_applications)

    try:
        cursor = conn.cursor(dictionary=True)
        
        query = """
        SELECT SOP_Number, Category, Status, Building, Submission_Date, Office_Notes
        FROM REBATE
        WHERE Department_ID = %s 
        ORDER BY Submission_Date DESC
        LIMIT 10;
        """
        cursor.execute(query, (username,)) 
        user_applications = cursor.fetchall()
        cursor.close()
        
    except mysql.connector.Error as err:
        print(f"Database query error fetching user dashboard applications from REBATE: {err}")
        
    finally:
        if conn and conn.is_connected():
            conn.close()

    return render_template('user_dashboard.html', 
                           username=username, 
                           applications=user_applications)

# --- VIEW ALL APPLICATIONS ---
@app.route('/view-all-applications')
def view_all_applications():
    """Fetches all applications data for the contractor view."""
    if 'contractor_logged_in' not in session:
        return redirect(url_for('contractor_login'))
    
    conn = get_db_connection()
    applications = []
    
    if conn is None:
        return render_template('view_all_applications.html', applications=applications)

    try:
        cursor = conn.cursor(dictionary=True)
        
        query = """
        SELECT SOP_Number, Category, Status, Building, Submission_Date, Department_ID, Sponsor_ID
        FROM REBATE
        ORDER BY Submission_Date DESC
        """
        cursor.execute(query)
        applications = cursor.fetchall()
        cursor.close()
        
    except mysql.connector.Error as err:
        print(f"Database query error in view_all_applications (REBATE table): {err}")
        
    finally:
        if conn and conn.is_connected():
            conn.close()

    return render_template('view_all_applications.html', applications=applications)

# --- SPONSOR APPROVALS VIEW --- (FUNCTIONAL ROUTE)
@app.route('/sponsor-approvals')
def sponsor_approvals():
    """Fetches and displays rebate records that have a Sponsor ID assigned and includes approval details."""
    if 'contractor_logged_in' not in session:
        return redirect(url_for('contractor_login'))
    
    conn = get_db_connection()
    approvals = []
    
    if conn is None:
        flash('Could not connect to the database.', 'error')
        return render_template('sponsor_approvals.html', approvals=approvals)

    try:
        cursor = conn.cursor(dictionary=True)
        
        # CHANGED TO LEFT JOIN to show all sponsored rebates, regardless of approval status
        query = """
        SELECT 
            R.SOP_Number,
            R.Sponsor_ID,
            RA.Approved_Amount,
            RA.Disbursed_Date,
            RA.Payment_Date,
            RA.Office_Notes
        FROM REBATE R
        LEFT JOIN REBATE_APPROVALS RA ON R.SOP_Number = RA.SOP_Number
        WHERE R.Sponsor_ID IS NOT NULL
        ORDER BY R.SOP_Number DESC;
        """
        cursor.execute(query)
        approvals = cursor.fetchall()
        cursor.close()
        
    except mysql.connector.Error as err:
        print(f"Database query error fetching sponsor approvals: {err}")
        flash('Error fetching sponsor approval data.', 'error')
        
    finally:
        if conn and conn.is_connected():
            conn.close()

    # Pass the data to the new template
    return render_template('sponsor_approvals.html', approvals=approvals)

# ==============================================================================
# 📝 APPLICATION SUBMISSION & REVIEW ROUTES
# ==============================================================================

# --- CONTRACTOR NEW EIA FORM (GET) ---
@app.route('/new-eia-application')
def new_eia_application():
    """Renders the form for a New Energy Incentive Application (Contractor access)."""
    if 'contractor_logged_in' in session and session['contractor_logged_in']:
        return render_template('new_eia_application.html', dashboard_url=url_for('contractor_dashboard'))
    else:
        return redirect(url_for('contractor_login'))
        
# --- USER NEW EIA FORM (GET) ---
@app.route('/user-new-eia-application')
def user_new_eia_application():
    """Renders the form for a New Energy Incentive Application (User/Department access)."""
    if 'user_logged_in' in session and session['user_logged_in']:
        return render_template('new_eia_application.html', dashboard_url=url_for('user_dashboard'))
    else:
        return redirect(url_for('user_login'))


# --- CONTRACTOR EIA FORM SUBMISSION (POST) ---
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
        
        category = request.form.get('project_type')
        building = request.form.get('building') 
        sponsor_id = request.form.get('sponsor_id') 
        department_id = request.form.get('department_id') 
        
        sql = """
        INSERT INTO REBATE
        (Category, Status, Building, Submission_Date, Department_ID, Sponsor_ID)
        VALUES (%s, %s, %s, NOW(), %s, %s) 
        """
        data = (category, 'Pending', building, department_id, sponsor_id)
        
        cursor.execute(sql, data)
        conn.commit()
        cursor.close()
        
        return redirect(url_for('contractor_dashboard'))

    except mysql.connector.Error as err:
        print(f"Database insertion error into REBATE: {err}")
        conn.rollback()
        return "Error submitting application to database.", 500
        
    finally:
        if conn and conn.is_connected():
            conn.close()

# --- USER EIA FORM SUBMISSION (POST) ---
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
        
        department = request.form.get('department')
        project_title = request.form.get('project_title')
        project_type = request.form.get('project_type')
        sponsor = request.form.get('sponsor')
        description = request.form.get('description')
        uploaded_file_path = "N/A"
        
        # NOTE: File Upload logic omitted here for brevity
        
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
            session.get('user_username', 'Unknown User')
        )
        
        cursor.execute(sql, data)
        conn.commit()
        cursor.close()
        
        return redirect(url_for('user_dashboard'))

    except mysql.connector.Error as err:
        print(f"Database insertion error into APPLICANT: {err}")
        conn.rollback()
        return "Error submitting application to database.", 500
        
    finally:
        if conn and conn.is_connected():
            conn.close()

# --- REVIEW APPLICATION (GET) ---
@app.route('/review-application/<string:application_id>', methods=['GET'])
def review_application(application_id):
    """Renders the review form for a single application."""
    if 'contractor_logged_in' not in session:
        return redirect(url_for('contractor_login'))

    conn = get_db_connection()
    application_details = None
    
    # ... (Database fetching logic remains the same) ...

    try:
        cursor = conn.cursor(dictionary=True)
        
        query = """
        SELECT SOP_Number, Category, Building, Department_ID, Status
        FROM REBATE
        WHERE SOP_Number = %s;
        """
        cursor.execute(query, (application_id,))
        application_details = cursor.fetchone()
        cursor.close()
        
        if not application_details:
            return "Application not found.", 404
        
    except mysql.connector.Error as err:
        print(f"Database query error fetching application details: {err}")
        return "Error fetching application details.", 500
        
    finally:
        if conn and conn.is_connected():
            conn.close()

    return render_template('application_review_form.html', details=application_details)

# --- PROCESS REVIEW DECISION (POST) ---
@app.route('/process-decision/<string:application_id>', methods=['POST'])
def process_decision(application_id):
    """
    Handles the contractor's decision (Approve/Reject/Revision), 
    capturing the approved amount and creating the REBATE_APPROVALS record.
    """
    if 'contractor_logged_in' not in session:
        return redirect(url_for('contractor_login'))

    conn = get_db_connection()
    if conn is None:
        flash("Database connection error. Decision not saved.", 'error')
        return redirect(url_for('view_all_applications'))

    try:
        cursor = conn.cursor()
        
        decision = request.form.get('action')
        notes = request.form.get('notes_to_applicant')
        
        # ⚠️ NEW: Capture the Approved Amount from the form
        approved_amount_str = request.form.get('approved_amount')
        
        if decision == 'Approve':
            new_status = 'Approved'
            
            # Convert amount to float, handle case where field might be empty if form was misclicked
            try:
                approved_amount = float(approved_amount_str)
            except (ValueError, TypeError):
                flash("Approval requires a valid Approved Amount.", 'error')
                return redirect(url_for('review_application', application_id=application_id))

        else:
            # For Reject/Revision, the amount is effectively zero
            new_status = decision.replace(' ', ' ')  # Replaces 'Request revision' with 'Revision Requested'
            approved_amount = 0.00


        # --- 1. Update the REBATE table (Status and Notes) ---
        sql_update_rebate = """
        UPDATE REBATE
        SET Status = %s, 
            Office_Notes = %s
        WHERE SOP_Number = %s
        """
        data_update_rebate = (new_status, notes, application_id)
        cursor.execute(sql_update_rebate, data_update_rebate)

        
        # --- 2. If Approved, Create a Record in REBATE_APPROVALS ---
        if decision == 'Approve':
            
            # Fetch Sponsor_ID and SOP_Number from the REBATE table
            cursor.execute("SELECT Sponsor_ID, SOP_Number FROM REBATE WHERE SOP_Number = %s", (application_id,))
            rebate_details = cursor.fetchone() # Fetch the first row as a tuple

            # Assuming the result is a tuple: (Sponsor_ID, SOP_Number)
            if rebate_details:
                sponsor_id = rebate_details[0]
                rebate_sop = rebate_details[1] 
            else:
                sponsor_id = None
                rebate_sop = application_id 
                
            # Insert into the REBATE_APPROVALS table
            sql_insert_approval = """
            INSERT INTO REBATE_APPROVALS
            (Approved_Amount, Office_Notes, Start_Date, Reviewer_ID, Sponsor_ID, SOP_Number)
            VALUES (%s, %s, CURDATE(), %s, %s, %s) 
            """
            data_insert_approval = (
                approved_amount, 
                f"Application approved: {notes}", 
                session.get('employee_id'), 
                sponsor_id,
                rebate_sop 
            )
            
            cursor.execute(sql_insert_approval, data_insert_approval)
            flash(f"Rebate {application_id} approved. Financial approval record created for ${approved_amount:.2f}.", 'success')
        
        conn.commit()
        cursor.close()
        
        return redirect(url_for('view_all_applications'))

    except mysql.connector.Error as err:
        print(f"Database update error in process_decision: {err}")
        conn.rollback()
        flash("Error processing application decision and financial record.", 'error')
        return redirect(url_for('view_all_applications'))
        
    finally:
        if conn and conn.is_connected():
            conn.close()


# ==============================================================================
# 📄 PUBLIC & MISC ROUTES
# ==============================================================================

@app.route('/impact')
def impact():
    """Renders the Impact page template."""
    return render_template('impact.html')

@app.route('/opportunities')
def opportunities():
    """Renders the Opportunities page template."""
    return render_template('opportunities.html')

@app.route('/rebates')
def rebates():
    """Renders the Rebates page."""
    return "<h1>Rebates Page Coming Soon!</h1><p>This is where users can find details on available rebates.</p>"

@app.route('/about')
def about():
    """Renders the About page."""
    return render_template('about.html')

@app.route('/forgot-password')
def forgot_password():
    """Placeholder route for the Forgot Password page."""
    return "<h1>Forgot Password Page</h1><p>Instructions for resetting the password will go here.</p>"

@app.route('/user-signup', methods=['GET'])
def user_signup():
    """Renders the standard user registration page template."""
    return render_template('user_signup.html')


# --- REPORT AND ADMIN ROUTES (PLACEHOLDERS) ---

# --- ENERGY REPORT VIEW ---
@app.route('/energy-report')
def energy_report():
    """Fetches key aggregate metrics for each campaign."""
    if 'contractor_logged_in' not in session:
        return redirect(url_for('contractor_login'))
    
    conn = get_db_connection()
    campaign_metrics = []
    
    if conn is None:
        flash('Could not connect to the database.', 'error')
        return render_template('energy_report.html', metrics=campaign_metrics)

    try:
        cursor = conn.cursor(dictionary=True)
        
        # SQL Query to join Campaign, Rebate, and Rebate_Approvals to calculate metrics
        query = """
        SELECT 
            C.Campaign_Name,
            C.Campaign_Type,
            COUNT(R.SOP_Number) AS Total_Applications,
            SUM(CASE WHEN R.Status = 'Approved' THEN 1 ELSE 0 END) AS Approved_Applications,
            COALESCE(SUM(RA.Approved_Amount), 0) AS Total_Approved_Rebates,
            COALESCE(SUM(RA.Energy_Savings_KWh), 0) AS Total_KWh_Savings
        FROM CAMPAIGN C
        LEFT JOIN REBATE R ON C.Campaign_ID = R.Campaign_ID
        LEFT JOIN REBATE_APPROVALS RA ON R.SOP_Number = RA.SOP_Number
        GROUP BY C.Campaign_ID, C.Campaign_Name, C.Campaign_Type
        ORDER BY C.Campaign_Date DESC;
        """
        cursor.execute(query)
        campaign_metrics = cursor.fetchall()
        cursor.close()
        
    except mysql.connector.Error as err:
        print(f"Database query error fetching energy report: {err}")
        flash('Error fetching energy report data.', 'error')
        
    finally:
        if conn and conn.is_connected():
            conn.close()

    # Pass the calculated metrics to the template
    return render_template('energy_report.html', metrics=campaign_metrics)

# --- PAYMENT REPORT VIEW ---
@app.route('/payment-report')
def payment_report():
    """Fetches and displays rebate records that have a final Payment_Date (disbursed funds)."""
    if 'contractor_logged_in' not in session:
        return redirect(url_for('contractor_login'))

    conn = get_db_connection()
    payments = []
    
    if conn is None:
        flash('Could not connect to the database.', 'error')
        return render_template('payment_report.html', payments=payments)

    try:
        cursor = conn.cursor(dictionary=True)
        
        # SQL Query to join REBATE and REBATE_APPROVALS tables
        # We filter where Payment_Date IS NOT NULL to show only disbursed funds.
        query = """
        SELECT 
            RA.SOP_Number AS App_ID,
            R.Department_ID AS Department,
            R.Category AS Project_Title,      -- Assuming Category acts as a brief Project Title
            R.Status,                         -- Include Status from REBATE
            RA.Approved_Amount AS Rebate_Paid,
            RA.Payment_Date AS Last_Updated   -- Use Payment_Date as the update date for the report
        FROM REBATE_APPROVALS RA
        JOIN REBATE R ON RA.SOP_Number = R.SOP_Number
        WHERE RA.Payment_Date IS NOT NULL
        ORDER BY RA.Payment_Date DESC;
        """
        
        cursor.execute(query)
        payments = cursor.fetchall()
        cursor.close()
        
    except mysql.connector.Error as err:
        print(f"Database query error fetching payment report data: {err}")
        flash('Error fetching payment report data.', 'error')
        
    finally:
        if conn and conn.is_connected():
            conn.close()

    # Pass the data to the new template using the variable 'payments'
    return render_template('payment_report.html', payments=payments)

@app.route('/project-report')
def project_report():
    if 'contractor_logged_in' not in session:
        return redirect(url_for('contractor_login'))
    return render_template('report_placeholder.html', report_name='Project Report')


# ==============================================================================
#  RUN APPLICATION
# ==============================================================================
if __name__ == "__main__":
    app.run(debug=True)