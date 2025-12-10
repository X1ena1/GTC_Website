#Importtting files
import mysql.connector
from flask import Flask, render_template, request
import locale

app = Flask(__name__)

#Home route
@app.route("/")
def index():
    return render_template('index.html')

#Running application
if __name__ == "__main__":
    app.run(debug=True)