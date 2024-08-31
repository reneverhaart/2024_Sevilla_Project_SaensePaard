import os
import subprocess
import sys


# Function to download missing packages, needs to be at start of code:
def install_packages():
    try:
        # Try Pip to install packages
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
    except subprocess.CalledProcessError as e:
        print(f"Fout bij het installeren van packages: {e}")
        sys.exit(1)


# Call function for downloading missing packages
install_packages()

# Flask related imports
from flask import Flask, render_template
from flask_socketio import SocketIO

# Repository related imports
from Database.repository import init_db

# Flask app configuration settings
app = Flask(__name__)
app.config['DATABASE'] = './saensepaard.db'
app.config['TEMPLATES_AUTO_RELOAD'] = True
socketio = SocketIO(app)

# Only initialize a new database if there is no database present
if not os.path.isfile(app.config['DATABASE']):
    init_db()  # repository


### STARTING APP ROUTES ###

@app.route("/")
def home():
    return render_template('home.html')

# @app.route("/a", methods=["POST", "GET"])
# def a
# @app.route("/b", methods=["POST", "GET"])
# def b
# @app.route("/c", methods=["POST", "GET"])
# def c
# @app.route("/d", methods=["POST", "GET"])
# def d
# @app.route("/e", methods=["POST", "GET"])
# def e
# @app.route("/f", methods=["POST", "GET"])
# def f
