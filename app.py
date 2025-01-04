import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime, timedelta
import secrets

app = Flask(__name__, static_folder="templates/static")  # Default static folder is used
# Generate a random secret key for session management
app.secret_key = secrets.token_hex(16)

DATABASE = "custom_links.db"
DEFAULT_PASSWORD = "link@rickroll"  # The fixed password

# Initialize the database
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        # Create the links table with the required columns
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                handle TEXT UNIQUE NOT NULL,
                target_url TEXT NOT NULL,
                expiration_date DATETIME NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

# Function to add a custom link to the database with expiration
def add_custom_link(handle, target_url, expiration_date):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO links (handle, target_url, expiration_date) VALUES (?, ?, ?)",
            (handle, target_url, expiration_date)
        )
        conn.commit()

# Function to retrieve a link by its handle
def get_link_by_handle(handle):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT target_url, expiration_date FROM links WHERE handle = ?", (handle,))
        result = cursor.fetchone()
        if result:
            target_url, expiration_date = result
            # Check if the link is expired
            if datetime.now() > datetime.strptime(expiration_date, "%Y-%m-%d %H:%M:%S"):
                return None  # Link is expired
            return target_url
        return None  # Link does not exist

@app.route("/")
def home():
    return render_template("create_link.html")

@app.route("/create", methods=["POST"])
def create_link():
    handle = request.form.get("handle")
    target_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Default Rickroll URL
    expiration_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")

    # Check if the link handle already exists
    if get_link_by_handle(handle):
        return render_template("create_link.html", error="Link handle already exists!")

    # Add the new link handle to the database
    add_custom_link(handle, target_url, expiration_date)
    sharable_url = url_for("redirect_to_rickroll", handle=handle, _external=True)
    return render_template("create_link.html", success=True, link=sharable_url)

@app.route("/<handle>")
def redirect_to_rickroll(handle):
    target_url = get_link_by_handle(handle)
    if target_url:
        return redirect(target_url)
    # Redirect to the home page if the link is invalid or expired
    return redirect(url_for("home"))

# Login route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # Check if the entered password matches the default
        if request.form['password'] == DEFAULT_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('view_links'))
        else:
            return render_template("login.html", error="Invalid password")
    return render_template("login.html")

# Logout route
@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("home"))

# View generated links - protected by authentication
@app.route("/view_links")
def view_links():
    if "logged_in" not in session:
        return redirect(url_for("login"))

    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, handle, target_url, expiration_date FROM links")
        links = cursor.fetchall()

    return render_template("view_links.html", links=links)

if __name__ == "__main__":
    # Initialize the database when the app starts
    init_db()
    app.run(debug=True)
