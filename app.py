import os
from flask import Flask, render_template, request, redirect, session, flash, url_for
from flask_dance.contrib.google import make_google_blueprint, google
from db_connection import init_db

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR     = os.path.abspath(os.path.dirname(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR   = os.path.join(BASE_DIR, "static")

app = Flask(
    __name__,
    template_folder=TEMPLATE_DIR,
    static_folder=STATIC_DIR
)

app.secret_key = os.environ.get("SECRET_KEY", "change-me-in-production")

# ── Google OAuth ───────────────────────────────────────────────────────────
# Set these environment variables before running:
#   export GOOGLE_CLIENT_ID=your-client-id
#   export GOOGLE_CLIENT_SECRET=your-client-secret

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # Allow HTTP on localhost (dev only)

google_bp = make_google_blueprint(
    client_id     = os.environ.get("GOOGLE_CLIENT_ID"),
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET"),
    scope         = ["profile", "email"],
    redirect_url  = "/google-login/callback"
)
app.register_blueprint(google_bp, url_prefix="/google-login")

# ── DB ─────────────────────────────────────────────────────────────────────
mysql = init_db(app)


# ── Routes ─────────────────────────────────────────────────────────────────

@app.route("/")
def welcome():
    return render_template("welcome.html")


@app.route("/home")
def home():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user_id  = request.form.get("user_id",  "").strip()
        password = request.form.get("password", "").strip()

        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT id FROM users WHERE user_id = %s AND password = %s",
            (user_id, password)  # ⚠ use hashed passwords in production!
        )
        user = cur.fetchone()
        cur.close()

        if user:
            session["user_id"] = user_id
            return redirect("/home")
        else:
            flash("Invalid credentials. Please try again.")
            return redirect("/login")

    return render_template("login.html")


@app.route("/google-login/callback")
def google_callback():
    """
    Called by Google after the user grants permission.
    Fetches their profile, auto-creates an account if needed,
    then logs them in.
    """
    if not google.authorized:
        flash("Google login failed. Please try again.")
        return redirect(url_for("login"))

    # Fetch user info from Google
    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        flash("Could not fetch your Google profile. Please try again.")
        return redirect(url_for("login"))

    info      = resp.json()
    email     = info.get("email")
    name      = info.get("name", email)
    google_id = info.get("id")

    cur = mysql.connection.cursor()

    # Check if user already exists (by email)
    cur.execute("SELECT id, user_id FROM users WHERE email = %s", (email,))
    user = cur.fetchone()

    if user:
        # Existing user — just log in
        session["user_id"] = user[1]
    else:
        # New user — auto-register with Google info
        user_id = email.split("@")[0]   # e.g. "john.doe" from "john.doe@gmail.com"
        try:
            cur.execute(
                "INSERT INTO users (user_id, email, password, google_id) VALUES (%s, %s, %s, %s)",
                (user_id, email, "", google_id)
            )
            mysql.connection.commit()
            session["user_id"] = user_id
        except Exception as e:
            flash(f"Auto-registration failed: {e}")
            cur.close()
            return redirect(url_for("login"))

    cur.close()
    return redirect("/home")


@app.route("/register", methods=["POST"])
def register():
    user_id  = request.form.get("user_id",  "").strip()
    email    = request.form.get("email",    "").strip()
    password = request.form.get("password", "").strip()

    cur = mysql.connection.cursor()
    try:
        cur.execute(
            "INSERT INTO users (user_id, email, password) VALUES (%s, %s, %s)",
            (user_id, email, password)  # ⚠ hash passwords in production!
        )
        mysql.connection.commit()
        flash("Registered successfully! Please log in.")
    except Exception as e:
        flash(f"Registration failed: {e}")
    finally:
        cur.close()

    return redirect("/login")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ── Dev server ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True)
