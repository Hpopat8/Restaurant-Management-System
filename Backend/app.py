import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, render_template
from Database.db_connection import init_db

app = Flask(__name__,
            template_folder='../templates',
            static_folder='../static')

app.secret_key = "supersecretkey"

mysql = init_db(app)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login')
def login():
    return render_template('login.html')

if __name__ == "__main__":
    app.run(debug=True)