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

# --- ADMIN PASSWORD SETTER ROUTE (NON-SECURE PLAINTEXT) ---
@app.route('/admin/set-password', methods=['POST'])
def admin_set_password():
    """
    ⚠️ NON-SECURE: Saves the plaintext password directly into the DEPARTMENT_USERS.Password_ID column.
    This route assumes an admin form posts to it with 'department_id' and 'new_password'.
    """
    if 'contractor_logged_in' not in session:
        flash('Authorization required to set passwords.', 'warning')
        return redirect(url_for('contractor_login'))
        
    dept_id = request.form.get('department_id')
    new_password_plaintext = request.form.get('new_password')

    if not dept_id or not new_password_plaintext:
        flash('Missing Department ID or new password.', 'danger')
        return redirect(url_for('contractor_dashboard'))

    conn = get_db_connection()
    if conn is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('contractor_dashboard'))
        
    cursor = conn.cursor()
    
    try:
        # ⚠️ WARNING: Saving plaintext password directly!
        update_query = "UPDATE DEPARTMENT_USERS SET Password_ID = %s WHERE Department_ID = %s"
        cursor.execute(update_query, (new_password_plaintext, dept_id))
        conn.commit()
        
        flash(f"Password successfully set (plaintext) for Department ID {dept_id}.", 'success')
        
    except mysql.connector.Error as e:
        flash(f'Database error setting password: {e}', 'danger')
        conn.rollback()
        
    finally:
        cursor.close()
        if conn and conn.is_connected():
            conn.close()
            
    return redirect(url_for('contractor_dashboard'))

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

# --- CONTRACTOR LOGIN SUBMIT (PLAINTEXT COMPARISON) ---
@app.route('/login-submit', methods=['POST'])
def login_submit():
    """
    ⚠️ NON-SECURE: Handles contractor authentication by comparing the plaintext password
    against the value stored in the REVIEWER.Password_ID column.
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
        # 🚨 FIX: Changed Password_Hash to Password_ID to match your database change.
        query = "SELECT Employee_ID, Employee_Name, Password_ID FROM REVIEWER WHERE Email = %s"
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
        # ⚠️ NON-SECURE CHECK: Plaintext comparison against database value
        if user['Password_ID'] == password_attempt: # <--- NOTE: Uses Password_ID here too
            # --- SUCCESSFUL LOGIN ---
            session['contractor_logged_in'] = True
            session['employee_id'] = user['Employee_ID']
            session['username'] = user['Employee_Name']
            flash(f"Welcome back, {user['Employee_Name']}.", 'success')
            return redirect(url_for('contractor_dashboard'))
        else:
            # Password mismatch
            flash('Invalid username or password.', 'error')
            return redirect(url_for('contractor_login'))
    else:
        # User (Email) not found
        flash('Invalid username or password.', 'error')
        return redirect(url_for('contractor_login'))

# --- USER LOGIN & SUBMIT (DEMO) ---
@app.route('/user-login', methods=['GET'])
def user_login():
    """Renders the standard user login page template."""
    return render_template('user_login.html')

@app.route('/user-login-submit', methods=['POST'])
def user_login_submit():
    """
    ⚠️ NON-SECURE: Handles user (department) authentication by comparing the plaintext password
    against the value stored in the Department_Users.Password_ID column.
    """
    login_id = request.form.get('username') # User inputs Department_ID here
    password_attempt = request.form.get('password')
    
    try:
        dept_id = int(login_id)
    except (ValueError, TypeError):
        flash('Invalid login ID format. Please use your Department ID.', 'danger')
        return redirect(url_for('user_login'))

    conn = get_db_connection()
    if conn is None:
        flash('Could not connect to the database. Try again later.', 'error')
        return redirect(url_for('user_login'))

    user = None
    try:
        cursor = conn.cursor(dictionary=True)
        # Query the DEPARTMENT_USERS table using Department_ID
        query = "SELECT Department_ID, Department_Name, Password_ID FROM APPLICANT WHERE Department_ID = %s"        
        cursor.execute(query, (dept_id,))
        user = cursor.fetchone()
        cursor.close()
        
    except mysql.connector.Error as err:
        print(f"Database query error during user login: {err}")
        flash('A database error occurred during login.', 'error')
        return redirect(url_for('user_login'))
    finally:
        if conn and conn.is_connected():
            conn.close()

    if user:
        # ⚠️ NON-SECURE CHECK: Plaintext comparison
        # NOTE: We assume the user table is named DEPARTMENT_USERS
        if user['Password_ID'] == password_attempt: 
            # --- SUCCESSFUL LOGIN ---
            session['user_logged_in'] = True
            session['user_id'] = user['Department_ID'] # Store ID for later lookup
            session['user_username'] = user['Department_Name']
            flash(f"Welcome, {user['Department_Name']}.", 'success')
            return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid login ID or password.', 'danger')
            return redirect(url_for('user_login'))
    else:
        flash('Invalid login ID or password.', 'danger')
        return redirect(url_for('user_login'))

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
    # Use the numeric ID for database lookup, which is stored in 'user_id'
    department_id = session.get('user_id') 

    user_applications = []
    
    # Check if we have the Department_ID before proceeding
    if department_id is None:
         flash("Error: User ID not found in session.", 'error')
         return render_template('user_dashboard.html', username=username, applications=user_applications)
    
    conn = get_db_connection()
    if conn is None:
        return render_template('user_dashboard.html', username=username, applications=user_applications)

    try:
        cursor = conn.cursor(dictionary=True)
        
        # NOTE: Status filtering is omitted because we want ALL records for this user (Draft, Pending, Approved, etc.)
        query = """
        SELECT SOP_Number, Category, Status, Building, Submission_Date, Office_Notes
        FROM REBATE
        WHERE Department_ID = %s 
        ORDER BY Submission_Date DESC
        LIMIT 10;
        """
        # --- FIX 1: Pass the numeric 'department_id' instead of the string 'username' ---
        cursor.execute(query, (department_id,)) 
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

# --- DELETE DRAFT APPLICATION ---
@app.route('/delete-draft/<int:sop_number>')
def delete_draft(sop_number):
    """
    Handles the deletion of a draft application (REBATE record) 
    using the SOP_Number. Only allows deletion if Status is 'Draft'.
    """
    if 'user_logged_in' not in session:
        return redirect(url_for('user_login'))
    
    # Get the user ID to ensure the user can only delete their own drafts
    department_id = session.get('user_id')
    
    conn = get_db_connection()
    if conn is None:
        flash("Database connection error. Could not delete draft.", 'error')
        return redirect(url_for('user_dashboard'))

    try:
        cursor = conn.cursor()
        
        # --- CRITICAL: Delete Query ---
        # Ensures that only records with the 'Draft' status AND the correct Department_ID are deleted.
        sql = """
        DELETE FROM REBATE
        WHERE SOP_Number = %s AND Status = 'Draft' AND Department_ID = %s
        """
        cursor.execute(sql, (sop_number, department_id))
        conn.commit()
        
        # Check if any rows were actually deleted
        if cursor.rowcount == 1:
            flash(f"Draft application {sop_number} has been deleted.", 'success')
        else:
            # This handles attempts to delete a submitted or approved application, or another user's draft.
            flash(f"Could not delete draft {sop_number}. It may no longer be a draft or belongs to another user.", 'warning')
            
        cursor.close()

    except mysql.connector.Error as err:
        print(f"Database deletion error: {err}")
        conn.rollback()
        flash("An error occurred during deletion.", 'error')
        
    finally:
        if conn and conn.is_connected():
            conn.close()

    return redirect(url_for('user_dashboard'))

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
        
        query = """
        SELECT 
            R.SOP_Number,
            R.Sponsor_ID,
            RA.Approved_Amount,
            RA.Approved_Amount AS Disbursed_Amount_Display,
            RA.Disbursed_Date,
            RA.Payment_Date,
            RA.Office_Notes
        FROM REBATE R
        LEFT JOIN REBATE_APPROVALS RA ON R.SOP_Number = RA.SOP_Number
        WHERE 
            R.Sponsor_ID IS NOT NULL -- This is the current, less-strict filter
        ORDER BY R.SOP_Number DESC;
        """

        cursor.execute(query)
        approvals = cursor.fetchall()
        cursor.close()
        
    except mysql.connector.Error as err:
        # 🛑 FIX: This block handles the database error
        print(f"Database query error fetching sponsor approvals: {err}")
        flash('Error fetching sponsor approval data.', 'error')
        
    finally:
        # 🛑 FIX: This block ensures the connection is closed
        if conn and conn.is_connected():
            conn.close()

    # Pass the data to the new template (This line is now correctly outside the try/except/finally block)
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
    """
    Handles the submission of the New EIA Application form data from a standard user, 
    inserting the record into the REBATE table for contractor review.
    """
    if 'user_logged_in' not in session:
        return redirect(url_for('user_login'))
    
    conn = get_db_connection()
    if conn is None:
        flash("Database connection error. Application not saved.", 'error')
        return redirect(url_for('user_dashboard'))

    try:
        cursor = conn.cursor()
        
        # --- 1. GATHER FORM DATA ---
        department_name = request.form.get('department')
        category = request.form.get('project_type') # Map to REBATE.Category
        building = request.form.get('building')      # Assuming you added a building field to the user form
        sponsor_id = request.form.get('sponsor')    # Map to REBATE.Sponsor_ID
        
        # Retrieve the user's Department_ID from the session
        department_id = session.get('user_id') 
        
        # NOTE: File Upload and Description/Title logic omitted here for database matching
        
        # --- 2. INSERT INTO REBATE TABLE ---
        sql = """
        INSERT INTO REBATE
        (Category, Status, Building, Submission_Date, Department_ID, Sponsor_ID, Office_Notes)
        VALUES (%s, %s, %s, NOW(), %s, %s, %s) 
        """
        data = (
            category,
            'Pending',
            building,
            department_id,
            sponsor_id,
            f"Submitted by {department_name}." # Initial note
        )
        
        cursor.execute(sql, data)
        conn.commit()
        cursor.close()
        
        flash("Your application has been submitted and is pending review.", 'success')
        return redirect(url_for('user_dashboard'))

    except mysql.connector.Error as err:
        print(f"Database insertion error into REBATE: {err}")
        conn.rollback()
        flash("Error submitting application to database.", 'error')
        return redirect(url_for('user_dashboard'))
        
    finally:
        if conn and conn.is_connected():
            conn.close()

# --- USER EIA FORM SAVE DRAFT (POST) ---
@app.route('/user-save-draft', methods=['POST'])
def user_save_draft():
    """
    Handles saving the EIA Application form data as a 'Draft' record.
    If the record already exists (e.g., has an SOP_Number), it should update it.
    For simplicity, we'll implement initial creation only for now.
    """
    if 'user_logged_in' not in session:
        return redirect(url_for('user_login'))
    
    conn = get_db_connection()
    if conn is None:
        flash("Database connection error. Draft not saved.", 'error')
        return redirect(url_for('user_dashboard'))

    try:
        cursor = conn.cursor()
        
        # --- GATHER FORM DATA ---
        department_name = request.form.get('department')
        category = request.form.get('project_type') # Maps to REBATE.Category
        building = request.form.get('building')
        sponsor_id = request.form.get('sponsor')
        description = request.form.get('description') # Capturing the description now
        
        department_id = session.get('user_id') 
        
        # --- INSERT INTO REBATE TABLE WITH 'Draft' STATUS ---
        # Note: We are using NOW() for Submission_Date, but for a draft, you might
        # prefer to use a NULLable column for Draft_Save_Date instead.
        sql = """
        INSERT INTO REBATE
        (Category, Status, Building, Submission_Date, Department_ID, Sponsor_ID, Office_Notes)
        VALUES (%s, %s, %s, NOW(), %s, %s, %s) 
        """
        data = (
            category,
            'Draft', # Key difference: Setting status to 'Draft'
            building,
            department_id,
            sponsor_id,
            f"Draft saved by {department_name}: {description[:200]}..." # Use part of description
        )
        
        cursor.execute(sql, data)
        conn.commit()
        cursor.close()
        
        # NOTE: A critical next step would be to get the new SOP_Number and redirect 
        # the user back to the edit page for that specific draft, but for now:
        flash("Your application draft has been saved. You can continue editing later.", 'success')
        return redirect(url_for('user_dashboard'))

    except mysql.connector.Error as err:
        print(f"Database insertion error saving draft: {err}")
        conn.rollback()
        flash("Error saving draft to database.", 'error')
        return redirect(url_for('user_dashboard'))
        
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
        # Use a dictionary cursor for reliable data fetching
        cursor = conn.cursor(dictionary=True)
        
        decision = request.form.get('action')
        notes = request.form.get('notes_to_applicant')
        approved_amount_str = request.form.get('approved_amount')
        
        # --- 1. Determine Status and Amount ---
        if decision == 'Approve':
            new_status = 'Approved'
            try:
                approved_amount = float(approved_amount_str)
            except (ValueError, TypeError):
                flash("Approval requires a valid Approved Amount.", 'error')
                return redirect(url_for('review_application', application_id=application_id))
        else:
            new_status = decision.replace(' ', ' ')
            approved_amount = 0.00 # Set to zero for non-approved actions

        # --- 2. Update the REBATE table (Status and Notes) ---
        sql_update_rebate = "UPDATE REBATE SET Status = %s, Office_Notes = %s WHERE SOP_Number = %s"
        data_update_rebate = (new_status, notes, application_id)
        cursor.execute(sql_update_rebate, data_update_rebate)

        
        # --- 3. If Approved, Create a Record in REBATE_APPROVALS ---
        if decision == 'Approve':
            
            # Fetch Sponsor_ID for the approval record
            cursor.execute("SELECT Sponsor_ID FROM REBATE WHERE SOP_Number = %s", (application_id,))
            
            # Since we used dictionary=True, this returns a dictionary or None
            rebate_details = cursor.fetchone() 
            
            sponsor_id = rebate_details.get('Sponsor_ID') if rebate_details else None
            
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
                sponsor_id, # Safely uses the fetched Sponsor_ID (can be NULL)
                application_id 
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
    """Fetches key aggregate metrics for each campaign by joining Campaign, Rebate, and Approvals."""
    if 'contractor_logged_in' not in session:
        return redirect(url_for('contractor_login'))
    
    conn = get_db_connection()
    campaign_metrics = []
    
    if conn is None:
        flash('Could not connect to the database.', 'error')
        return render_template('energy_report.html', metrics=campaign_metrics)

    try:
        cursor = conn.cursor(dictionary=True)
        
# SQL Query: Starts with CAMPAIGN and LEFT JOINs to REBATE and REBATE_APPROVALS
        query = """
        SELECT 
            C.Campaign_Name,
            C.Category, -- Use the new, renamed column
            COUNT(R.SOP_Number) AS Total_Applications,
            SUM(CASE WHEN R.Status = 'Approved' THEN 1 ELSE 0 END) AS Approved_Applications,
            COALESCE(SUM(RA.Approved_Amount), 0) AS Total_Approved_Rebates
        FROM CAMPAIGN C
        -- ✅ FINAL FIXED JOIN: Joining Category to Category
        LEFT JOIN REBATE R ON C.Category = R.Category
        LEFT JOIN REBATE_APPROVALS RA ON R.SOP_Number = RA.SOP_Number
        GROUP BY C.Campaign_ID, C.Campaign_Name, C.Category
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

# --- PROJECT REPORT VIEW ---
@app.route('/project-report')
def project_report():
    """Fetches a detailed list of all projects, joining application and financial data."""
    if 'contractor_logged_in' not in session:
        return redirect(url_for('contractor_login'))
    
    conn = get_db_connection()
    projects = []
    
    if conn is None:
        flash('Could not connect to the database.', 'error')
        return render_template('project_report.html', projects=projects)

    try:
        cursor = conn.cursor(dictionary=True)
        
        # SQL Query to join REBATE (R), APPLICANT (D), and REBATE_APPROVALS (RA)
        query = """
        SELECT 
            R.SOP_Number,
            D.Department_Name AS Department,
            R.Category,
            R.Building,
            R.Submission_Date,
            R.Status,
            COALESCE(RA.Approved_Amount, 0.00) AS Approved_Amount,
            RA.Disbursed_Date
        FROM REBATE R
        -- Using APPLICANT table name based on your successful troubleshooting:
        LEFT JOIN APPLICANT D ON R.Department_ID = D.Department_ID
        LEFT JOIN REBATE_APPROVALS RA ON R.SOP_Number = RA.SOP_Number
        ORDER BY R.Submission_Date DESC;
        """
        
        cursor.execute(query)
        projects = cursor.fetchall()
        cursor.close()
        
    except mysql.connector.Error as err:
        print(f"Database query error fetching project report data: {err}")
        flash('Error fetching project report data.', 'error')
        
    finally:
        if conn and conn.is_connected():
            conn.close()

    # NOTE: The template name is now 'project_report.html'
    return render_template('project_report.html', projects=projects)

# ==============================================================================
#  RUN APPLICATION
# ==============================================================================
if __name__ == "__main__":
    app.run(debug=True)