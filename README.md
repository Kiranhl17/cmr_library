# CMR — Computerized Library Record Management System
## Computer Science Department Library

Flask + PostgreSQL web application for managing a CS department library.

---

## 📁 Folder Structure

```
cmr_library/
├── app.py                    # Main Flask application
├── requirements.txt          # Python dependencies
├── static/
│   └── uploads/covers/       # Book cover image uploads
└── templates/
    ├── base.html             # Sidebar + topbar layout
    ├── login.html            # Login page
    ├── dashboard.html        # Dashboard with stats
    ├── books.html            # Books catalog + CRUD
    ├── issues.html           # Issue / Return / Records
    └── reports.html          # Reports + Export
```

---

## 🗄️ Database — PostgreSQL

### Tables

**users** — `id, username, password, role, name, created_at`
**books** — `id, accession_number, title, author, publisher, edition, year_of_publication, department, category, shelf_number, quantity, available_quantity, status, date_of_entry, cover_image, isbn`
**issues** — `id, book_id, accession_number, student_name, usn, issue_date, return_date, actual_return_date, status, fine, issued_by`

---

## ⚙️ Setup Instructions

### Step 1 — Install PostgreSQL
Download and install from: https://www.postgresql.org/download/windows/

During installation, set a password for the `postgres` user (remember it!).

### Step 2 — Create the Database
Open **pgAdmin** or **psql** and run:
```sql
CREATE DATABASE cmr_library;
```

### Step 3 — Configure DB credentials in app.py
Open `app.py` and update this section near the top:
```python
DB_CONFIG = {
    'host':     'localhost',
    'port':     '5432',
    'dbname':   'cmr_library',
    'user':     'postgres',
    'password': 'your_password_here',   # ← change this
}
```

### Step 4 — Create Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### Step 5 — Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 6 — Run the App
```bash
python app.py
```

Visit: **http://localhost:5000**

Tables are created automatically on first run. Seed data (12 books + sample issues) is inserted automatically.

---

## 🔑 Login Credentials

| Role      | Username   | Password |
|-----------|------------|----------|
| Librarian | librarian  | lib123   |

> ⚠️ Change the password after first login in production!

---

## 🌍 Environment Variables (Optional)
Instead of editing `app.py` directly, you can set environment variables:

```bash
# Windows PowerShell
$env:DB_HOST="localhost"
$env:DB_PORT="5432"
$env:DB_NAME="cmr_library"
$env:DB_USER="postgres"
$env:DB_PASSWORD="yourpassword"
```

```bash
# Linux / macOS
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=cmr_library
export DB_USER=postgres
export DB_PASSWORD=yourpassword
```

---

## 🚀 Deployment

### Render.com (Free Tier)
1. Push code to GitHub
2. New Web Service → connect repo
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Add environment variables for DB config
6. Use Render's managed PostgreSQL add-on

### Railway.app
1. New project → Deploy from GitHub
2. Add a PostgreSQL plugin
3. Railway auto-sets `DATABASE_URL` — update `app.py` to read it

### Production Checklist
- [ ] Change `app.secret_key` to a random 32-char string
- [ ] Change librarian password
- [ ] Set `debug=False`
- [ ] Use environment variables for DB credentials
- [ ] Configure HTTPS

---

## ✨ Features

| Feature                        | Status |
|-------------------------------|--------|
| Secure Login + Sessions        | ✅     |
| Single Librarian Role          | ✅     |
| Dashboard with Live Stats      | ✅     |
| Add / Edit / Delete Books      | ✅     |
| Book Cover Image Upload        | ✅     |
| Search + Filter + Sort + Page  | ✅     |
| Issue Book to Student          | ✅     |
| Return + Fine Calculation      | ✅     |
| Overdue Detection              | ✅     |
| Export to CSV                  | ✅     |
| Category-wise Reports          | ✅     |
| Responsive Design              | ✅     |
