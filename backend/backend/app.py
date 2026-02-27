import os
from flask import Flask, render_template, request, redirect, session, flash, url_for
from flask_dance.contrib.google import make_google_blueprint, google
from db_connection import init_db
import smtplib
import ssl
import random
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
try:
    from twilio.rest import Client as TwilioClient
except Exception:
    TwilioClient = None

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
 
# Configuration: Provide these via environment variables in production
SMTP_HOST = os.environ.get("SMTP_HOST")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
FROM_EMAIL = os.environ.get("FROM_EMAIL", SMTP_USER)

TWILIO_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_FROM  = os.environ.get("TWILIO_FROM")


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
        send_via = request.form.get("send_via", "email")  # 'email' or 'sms'

        cur = mysql.connection.cursor()
        cur.execute("SELECT id, email, phone, password FROM users WHERE user_id = %s", (user_id,))
        user = cur.fetchone()
        cur.close()

        if not user:
            flash("Invalid credentials. Please try again.")
            return redirect("/login")

        stored_password = user[3]
        if not check_password_hash(stored_password, password):
            flash("Invalid credentials. Please try again.")
            return redirect("/login")

        # Password valid — generate OTP and send via chosen channel
        code = generate_otp()
        expires_at = datetime.utcnow() + timedelta(minutes=5)

        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO otps (user_id, code, channel, expires_at) VALUES (%s, %s, %s, %s)",
            (user_id, code, send_via, expires_at)
        )
        mysql.connection.commit()
        cur.close()

        # Send the OTP
        email = user[1]
        phone = user[2]
        try:
            if send_via == "sms" and phone:
                send_sms_otp(phone, code)
            else:
                send_email_otp(email, code)
        except Exception as e:
            flash(f"Failed to send OTP: {e}")
            return redirect("/login")

        # Store user_id in temporary session to complete OTP step
        session["preauth_user_id"] = user_id
        return redirect(url_for("verify_otp_view"))

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
    phone    = request.form.get("phone", None)

    cur = mysql.connection.cursor()
    try:
        hashed = generate_password_hash(password)
        cur.execute(
            "INSERT INTO users (user_id, email, password, phone) VALUES (%s, %s, %s, %s)",
            (user_id, email, hashed, phone)
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


# -------------------- OTP endpoints and helpers --------------------

def generate_otp(length: int = 6) -> str:
    rng = random.SystemRandom()
    return ''.join(rng.choice('0123456789') for _ in range(length))

def send_email_otp(to_email: str, code: str):
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASSWORD:
        raise RuntimeError("SMTP not configured")

    subject = "Your OTP code"
    body = f"Your verification code is: {code}\nIt expires in 5 minutes."
    message = f"Subject: {subject}\n\n{body}"

    context = ssl.create_default_context()
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls(context=context)
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(FROM_EMAIL, to_email, message)

def send_sms_otp(to_phone: str, code: str):
    if not TWILIO_SID or not TWILIO_TOKEN or not TWILIO_FROM:
        raise RuntimeError("Twilio not configured")
    if TwilioClient is None:
        raise RuntimeError("Twilio library not installed")

    client = TwilioClient(TWILIO_SID, TWILIO_TOKEN)
    client.messages.create(body=f"Your verification code: {code}", from_=TWILIO_FROM, to=to_phone)


@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp_view():
    if request.method == 'POST':
        user_id = session.get('preauth_user_id') or request.form.get('user_id')
        code = request.form.get('otp', '').strip()

        if not user_id:
            flash('No authentication in progress. Please login again.')
            return redirect('/login')

        cur = mysql.connection.cursor()
        cur.execute("SELECT id, code, expires_at, used FROM otps WHERE user_id = %s AND code = %s ORDER BY id DESC LIMIT 1", (user_id, code))
        row = cur.fetchone()
        if not row:
            cur.close()
            flash('Invalid or expired code.')
            return redirect('/login')

        otp_id, otp_code, expires_at, used = row[0], row[1], row[2], row[3]
        if used:
            cur.close()
            flash('This code has already been used.')
            return redirect('/login')

        if datetime.utcnow() > expires_at:
            cur.close()
            flash('Code expired. Please login again to receive a new code.')
            return redirect('/login')

        # Mark used and complete login
        cur.execute("UPDATE otps SET used = TRUE WHERE id = %s", (otp_id,))
        mysql.connection.commit()
        cur.close()

        session.pop('preauth_user_id', None)
        session['user_id'] = user_id
        return redirect('/home')

    # GET: show OTP entry form (templates should be added by user)
    return render_template('verify_otp.html')


# ── Dev server ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True)
