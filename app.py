import psycopg2
from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime, timedelta
import secrets

# Flask app initialization
app = Flask(__name__, static_folder="templates/static", template_folder="templates")
app.secret_key = secrets.token_hex(16)

# Security configurations
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = True

# PostgreSQL connection string
DATABASE_URL = "postgresql://neondb_owner:owK1qpUWr0Ck@ep-cold-glitter-a1vo1tgq-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

DEFAULT_PASSWORD = "link@rickroll"  # Default password for admin login

# Initialize the database
def init_db():
    try:
        with psycopg2.connect(DATABASE_URL) as conn:
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

# Add a custom link to the database with expiration
def add_custom_link(handle, target_url, expiration_date):
    try:
        with psycopg2.connect(DATABASE_URL) as conn:
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

# Retrieve a link by its handle
def get_link_by_handle(handle):
    try:
        with psycopg2.connect(DATABASE_URL) as conn:
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

# Delete a link by ID
def delete_link(link_id):
    try:
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM links WHERE id = %s", (link_id,))
                conn.commit()
    except Exception as e:
        print(f"Error deleting link: {e}")

# Update a link by ID
def update_link(link_id, handle, target_url, expiration_date):
    try:
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE links
                    SET handle = %s, target_url = %s, expiration_date = %s
                    WHERE id = %s
                """, (handle, target_url, expiration_date, link_id))
                conn.commit()
    except Exception as e:
        print(f"Error updating link: {e}")

# Fetch all links
def fetch_all_links():
    try:
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, handle, target_url, expiration_date FROM links")
                links = cursor.fetchall()
                return [
                    {
                        'id': link[0],
                        'handle': link[1],
                        'target_url': link[2],
                        'expiration_date': link[3],
                        'is_expired': datetime.now() > link[3]
                    }
                    for link in links
                ]
    except Exception as e:
        print(f"Error fetching links: {e}")
        return []

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
@app.route("/view_links", methods=["GET", "POST"])
def view_links():
    if "logged_in" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        action = request.form.get("action")
        link_id = request.form.get("link_id")

        if action == "delete":
            delete_link(link_id)
        elif action == "edit":
            return redirect(url_for("edit_link", link_id=link_id))

    try:
        links = fetch_all_links()
        return render_template("view_links.html", links=links)
    except Exception as e:
        print(f"Error fetching links: {e}")
        return "An error occurred while fetching links."

# Edit link route
@app.route("/edit/<int:link_id>", methods=["GET", "POST"])
def edit_link(link_id):
    if "logged_in" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        handle = request.form.get("handle", "").strip()
        target_url = request.form.get("target_url", "").strip()
        expiration_date = datetime.strptime(request.form.get("expiration_date", "").strip(), "%Y-%m-%d %H:%M:%S")

        if not handle or not target_url:
            return render_template("edit_link.html", error="All fields are required!", link_id=link_id)

        update_link(link_id, handle, target_url, expiration_date)
        return redirect(url_for("view_links"))

    # Retrieve current link data
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT handle, target_url, expiration_date FROM links WHERE id = %s", (link_id,))
            link = cursor.fetchone()
            if link:
                return render_template("edit_link.html", link={
                    "id": link_id,
                    "handle": link[0],
                    "target_url": link[1],
                    "expiration_date": link[2].strftime("%Y-%m-%d %H:%M:%S")
                })
            else:
                return "Link not found!"

# Initialize the database
init_db()