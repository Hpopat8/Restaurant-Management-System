# GTL Utsav Dining — Setup Guide

## Project Structure
```
gtl_project/
├── app.py                  ← Main Flask app (FIXED)
├── db_connection.py        ← MySQL connection (FIXED)
├── requirements.txt        ← pip dependencies
├── schema.sql              ← Database setup (FIXED)
├── templates/
│   ├── welcome.html
│   ├── login.html          ← FIXED: flash messages, validation
│   └── index.html          ← FIXED: logout button, user display
└── static/
    ├── css/style.css       ← FIXED: flash styles, logout btn
    ├── js/theme.js
    └── images/
        ├── hero.jpg        ← Copy your hero.jpg here
        └── logo.png        ← Copy your logo.png here
```

## Step 1 — Install Dependencies
```bash
pip install -r requirements.txt
```

## Step 2 — Setup MySQL Database
```bash

```

## Step 3 — Set Environment Variables
```bash
export MYSQL_HOST=localhost
export MYSQL_USER=root
export MYSQL_PASSWORD=your_mysql_password
export MYSQL_DB=gtl_auth
export SECRET_KEY=some-random-secret-key
```

## Step 4 — Copy Your Images
```bash
cp hero.jpg  static/images/hero.jpg
cp logo.png  static/images/logo.png
```

## Step 5 — Run the App
```bash
python app.py
```

Visit: http://localhost:5000

---

## What Was Fixed

### 🔐 Security
- **Passwords are now hashed** using `werkzeug.security` (bcrypt). Plain-text passwords in DB is a serious vulnerability.
- Old plain-text passwords in DB will NOT work — users must re-register.
- Google OAuth only loads if `GOOGLE_CLIENT_ID` env var is set (no crash without it).

### 🐛 Bug Fixes
- **Flash messages now display** on the login page (were missing from the template).
- **Register form** now shows validation errors inline without losing context.
- **`show_register` flag** — if registration fails, the Register tab stays open.
- **Session protection** — `/home` redirects to login if not authenticated.
- **DictCursor** added to MySQL config for cleaner row access.
- **Duplicate user_id check** added to Google OAuth auto-registration.
- **Hardcoded MySQL password removed** from `db_connection.py`.

### ✨ UX Improvements
- Added "or" divider between Google login and form.
- Logout button visible in navbar when logged in.
- Logged-in username shown in navbar.
- Input fields have focus highlight.
- HTML5 `minlength` validation on forms.

---

## Google OAuth Setup (Optional)
```bash
export GOOGLE_CLIENT_ID=your-google-client-id
export GOOGLE_CLIENT_SECRET=your-google-client-secret
```
Then in Google Cloud Console:
- Authorized redirect URI: `http://localhost:5000/google-login/callback`
mysql -u root -p < schema.sql

