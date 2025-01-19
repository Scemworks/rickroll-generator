import psycopg2
from psycopg2 import sql, pool
from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime, timedelta
import secrets

# Flask app initialization
app = Flask(__name__, static_folder="templates/static", template_folder="templates")
app.secret_key = secrets.token_hex(16)

# Security configurations
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = True

# PostgreSQL database connection pool
DATABASE_URL = "postgresql://neondb_owner:owK1qpUWr0Ck@ep-cold-glitter-a1vo1tgq-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
db_pool = psycopg2.pool.SimpleConnectionPool(1, 10, DATABASE_URL)

DEFAULT_PASSWORD = "link@rickroll"  # Default password for admin login

# Initialize the database
def init_db():
    try:
        with db_pool.getconn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS links (
                        id SERIAL PRIMARY KEY,
                        handle TEXT UNIQUE NOT NULL,
                        target_url TEXT NOT NULL,
                        expiration_date TIMESTAMP NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
    except Exception as e:
        print(f"Database initialization error: {e}")

# Function to add a custom link to the database with expiration
def add_custom_link(handle, target_url, expiration_date):
    try:
        with db_pool.getconn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO links (handle, target_url, expiration_date) VALUES (%s, %s, %s)",
                    (handle, target_url, expiration_date)
                )
                conn.commit()
    except psycopg2.IntegrityError:
        raise ValueError("Handle already exists!")
    except Exception as e:
        print(f"Error adding link: {e}")
        raise

# Function to retrieve a link by its handle
def get_link_by_handle(handle):
    try:
        with db_pool.getconn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT target_url, expiration_date FROM links WHERE handle = %s",
                    (handle,)
                )
                result = cursor.fetchone()
                if result:
                    target_url, expiration_date = result
                    if datetime.now() > expiration_date:
                        return None  # Link is expired
                    return target_url
                return None  # Link does not exist
    except Exception as e:
        print(f"Error retrieving link: {e}")
        return None

# Home route
@app.route("/")
def home():
    return render_template("create_link.html")

# Create link route
@app.route("/create", methods=["POST"])
def create_link():
    handle = request.form.get("handle", "").strip()
    target_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Default Rickroll URL
    expiration_date = datetime.now() + timedelta(days=7)

    if not handle:
        return render_template("create_link.html", error="Handle cannot be empty!")

    try:
        add_custom_link(handle, target_url, expiration_date)
        sharable_url = url_for("redirect_to_rickroll", handle=handle, _external=True)
        return render_template("create_link.html", success=True, link=sharable_url)
    except ValueError as ve:
        return render_template("create_link.html", error=str(ve))
    except Exception as e:
        print(f"Error: {e}")
        return render_template("create_link.html", error="An error occurred while creating the link!")

# Redirect route
@app.route("/<handle>")
def redirect_to_rickroll(handle):
    target_url = get_link_by_handle(handle)
    if target_url:
        return redirect(target_url)
    return redirect(url_for("home"))

# Login route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form['password'] == DEFAULT_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('view_links'))
        return render_template("login.html", error="Invalid password")
    return render_template("login.html")

# Logout route
@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("home"))

# View links route
@app.route("/view_links")
def view_links():
    if "logged_in" not in session:
        return redirect(url_for("login"))

    conn = db_pool.getconn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, handle, target_url, expiration_date FROM links")
            links = cursor.fetchall()

        links = [
            {
                'id': link[0],
                'handle': link[1],
                'target_url': link[2],
                'expiration_date': link[3],
                'is_expired': datetime.now() > link[3]
            }
            for link in links
        ]
        return render_template("view_links.html", links=links)
    except Exception as e:
        print(f"Error fetching links: {e}")
        return "An error occurred while fetching links."
    finally:
        if conn:
            db_pool.putconn(conn)

# Initialize the database when the app starts
init_db()
