#Importtting files
import mysql.connector
from flask import Flask, render_template, request
import locale

app = Flask(__name__)

#Home route
@app.route("/")
def index():
    return render_template('index.html')

# -- Add the Contractor Login Route below --

@app.route('/contractor-login')
def contractor_login():
    """
    Renders the contractor login page template.
    """
    return render_template('contractor_login.html')

# You would add code here later to handle the form submission (POST)
# @app.route('/contractor-login', methods=['POST'])
# def login_submit():
#     # Logic to process username and password
#     pass

@app.route('/impact')
def impact():
    """
    Renders the Impact page template, showing project results and savings.
    """
    return render_template('impact.html')

# In your Web.py file, add these placeholder routes:

@app.route('/opportunities')
def opportunities():
    """Renders the Opportunities page."""
    # NOTE: You will need to create 'opportunities.html' later.
    return "<h1>Opportunities Page Coming Soon!</h1><p>This is where users can view available energy projects.</p>"

@app.route('/rebates')
def rebates():
    """Renders the Rebates page."""
    # NOTE: You will need to create 'rebates.html' later.
    return "<h1>Rebates Page Coming Soon!</h1><p>This is where users can find details on available rebates.</p>"

@app.route('/about')
def about():
    """Renders the About page."""
    # NOTE: You will need to create 'about.html' later.
    return "<h1>About Page Coming Soon!</h1><p>Information about the system and the University program.</p>"

@app.route('/user-login')
def user_login():
    """Placeholder for the User Login page."""
    # NOTE: You will need to create 'user_login.html' later.
    return "<h1>User Login Page</h1><p>Placeholder for standard user login.</p>"

@app.route('/logout')
def logout():
    """Placeholder for the Logout action."""
    # NOTE: This should handle session cleanup and redirect to the index page.
    return redirect(url_for('index'))

#Running application
if __name__ == "__main__":
    app.run(debug=True)