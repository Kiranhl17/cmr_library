"""
CMR — Computerized Library Record Management System
Flask + PostgreSQL (psycopg2)
"""

from flask import (Flask, render_template, request, jsonify,
                   session, redirect, url_for, send_file, g)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import date, timedelta
from functools import wraps
from urllib.parse import urlparse
import psycopg2, psycopg2.extras, os, io, csv

app = Flask(__name__)
app.secret_key = 'cmr-library-secret-key-change-in-production-2024!'

# ── PostgreSQL connection config ─────────────────────────────────────────────
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    parsed = urlparse(DATABASE_URL)
    DB_CONFIG = {
        'host':     parsed.hostname,
        'port':     parsed.port or 5432,
        'dbname':   parsed.path[1:],
        'user':     parsed.username,
        'password': parsed.password,
    }
else:
    DB_CONFIG = {
        'host':     os.environ.get('DB_HOST', 'localhost'),
        'port':     os.environ.get('DB_PORT', '5432'),
        'dbname':   os.environ.get('DB_NAME', 'cmr_library'),
        'user':     os.environ.get('DB_USER', 'postgres'),
        'password': os.environ.get('DB_PASSWORD', 'Love@123'),
    }

UPLOAD_DIR  = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static', 'uploads', 'covers')
ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ── DB helpers ───────────────────────────────────────────────────────────────

def get_db():
    if 'db' not in g:
        g.db = psycopg2.connect(**DB_CONFIG)
        g.db.autocommit = False
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db: db.close()

def qry(sql, params=(), one=False, commit=False):
    db = get_db()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(sql, params)
    if commit:
        db.commit()
        try:
            row = cur.fetchone()
            return row['id'] if row else None
        except Exception:
            return None
    return (cur.fetchone() if one else cur.fetchall())

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


# ── Schema ───────────────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id         SERIAL PRIMARY KEY,
    username   VARCHAR(80) UNIQUE NOT NULL,
    password   VARCHAR(255) NOT NULL,
    role       VARCHAR(20) DEFAULT 'librarian',
    name       VARCHAR(120),
    created_at DATE DEFAULT CURRENT_DATE
);

CREATE TABLE IF NOT EXISTS books (
    id                   SERIAL PRIMARY KEY,
    accession_number     VARCHAR(50) UNIQUE NOT NULL,
    title                VARCHAR(255) NOT NULL,
    author               VARCHAR(255) NOT NULL,
    publisher            VARCHAR(255),
    edition              VARCHAR(50),
    year_of_publication  INTEGER,
    department           VARCHAR(100) DEFAULT 'CSE',
    category             VARCHAR(100),
    shelf_number         VARCHAR(50),
    quantity             INTEGER DEFAULT 1,
    available_quantity   INTEGER DEFAULT 1,
    status               VARCHAR(20) DEFAULT 'Available',
    date_of_entry        DATE DEFAULT CURRENT_DATE,
    cover_image          VARCHAR(255),
    isbn                 VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS issues (
    id                 SERIAL PRIMARY KEY,
    book_id            INTEGER NOT NULL REFERENCES books(id),
    accession_number   VARCHAR(50),
    student_name       VARCHAR(255) NOT NULL,
    usn                VARCHAR(50) NOT NULL,
    issue_date         DATE NOT NULL,
    return_date        DATE NOT NULL,
    actual_return_date DATE,
    status             VARCHAR(20) DEFAULT 'Issued',
    fine               FLOAT DEFAULT 0.0,
    issued_by          VARCHAR(80)
);
"""

def init_db():
    with app.app_context():
        db = get_db()
        cur = db.cursor()
        cur.execute(SCHEMA)
        db.commit()
        seed_data(db)

def seed_data(db):
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("SELECT COUNT(*) as cnt FROM users")
    if cur.fetchone()['cnt'] == 0:
        cur.execute(
            "INSERT INTO users (username, password, role, name) VALUES (%s, %s, %s, %s)",
            ('librarian', generate_password_hash('lib123'), 'librarian', 'Ms. Shruthi')
        )

    cur.execute("SELECT COUNT(*) as cnt FROM books")
    if cur.fetchone()['cnt'] == 0:
        books = [
            ('CSE001','Introduction to Algorithms','Thomas H. Cormen','MIT Press','4th',2022,'CSE','Algorithms','A1',3,3),
            ('CSE002','Clean Code','Robert C. Martin','Prentice Hall','1st',2008,'CSE','Programming','B2',2,2),
            ('CSE003','Artificial Intelligence: A Modern Approach','Stuart Russell','Pearson','4th',2020,'CSE','AI/ML','C1',4,3),
            ('CSE004','Database System Concepts','Abraham Silberschatz','McGraw-Hill','7th',2019,'CSE','DBMS','D1',5,5),
            ('CSE005','Computer Networks','Andrew S. Tanenbaum','Pearson','5th',2010,'CSE','Networks','E1',3,2),
            ('CSE006','Operating System Concepts','Abraham Silberschatz','Wiley','10th',2018,'CSE','OS','F1',4,4),
            ('CSE007','Python Crash Course','Eric Matthes','No Starch Press','3rd',2023,'CSE','Programming','B3',6,6),
            ('CSE008','Deep Learning','Ian Goodfellow','MIT Press','1st',2016,'CSE','AI/ML','C2',2,2),
            ('CSE009','The Pragmatic Programmer','David Thomas','Addison-Wesley','2nd',2019,'CSE','Programming','B1',3,3),
            ('CSE010','Design Patterns','Gang of Four','Addison-Wesley','1st',1994,'CSE','Software Engineering','G1',2,2),
            ('CSE011','Computer Organization and Architecture','William Stallings','Pearson','11th',2019,'CSE','Computer Architecture','H1',3,3),
            ('CSE012','Cryptography and Network Security','William Stallings','Pearson','7th',2017,'CSE','Networks','E2',2,1),
        ]
        cur.executemany(
            """INSERT INTO books (accession_number,title,author,publisher,edition,year_of_publication,
               department,category,shelf_number,quantity,available_quantity)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            books)

        today = date.today()
        cur.execute("SELECT id, accession_number FROM books WHERE accession_number IN ('CSE003','CSE005','CSE012')")
        id_map = {r['accession_number']: r['id'] for r in cur.fetchall()}

        issues = [
            (id_map['CSE003'],'CSE003','Arjun Mehta','1CS21CS001',today-timedelta(5), today+timedelta(9),'Issued','librarian'),
            (id_map['CSE005'],'CSE005','Sneha Reddy','1CS21CS042',today-timedelta(15),today-timedelta(1), 'Issued','librarian'),
            (id_map['CSE012'],'CSE012','Vikram Singh','1CS21CS077',today-timedelta(20),today-timedelta(6), 'Issued','librarian'),
        ]
        cur.executemany(
            """INSERT INTO issues (book_id,accession_number,student_name,usn,issue_date,return_date,status,issued_by)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
            issues)

    db.commit()

# ⭐ ADD THIS BLOCK
with app.app_context():
    init_db()


# ── Auth ─────────────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def dec(*a, **kw):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*a, **kw)
    return dec


# ── Dict helpers ─────────────────────────────────────────────────────────────

def book_dict(row):
    d = dict(row)
    for k in ['date_of_entry']:
        if d.get(k) and not isinstance(d[k], str):
            d[k] = str(d[k])
    return d

def issue_dict(row):
    d = dict(row)
    today = date.today()
    ret = d.get('return_date')
    if ret and not isinstance(ret, date):
        ret = date.fromisoformat(str(ret))
    elif isinstance(ret, date):
        pass
    overdue = d['status'] == 'Issued' and ret and ret < today
    d['overdue'] = overdue
    d['days_overdue'] = (today - ret).days if overdue else 0
    d['book_title'] = d.get('book_title', '')
    for k in ['issue_date', 'return_date', 'actual_return_date']:
        if d.get(k) and not isinstance(d[k], str):
            d[k] = str(d[k])
        elif not d.get(k):
            d[k] = ''
    return d


# ── Page routes ──────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return redirect(url_for('dashboard') if 'user_id' in session else url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        d = request.get_json()
        row = qry("SELECT * FROM users WHERE username=%s", (d.get('username'),), one=True)
        if row and check_password_hash(row['password'], d.get('password', '')):
            session.update(user_id=row['id'], username=row['username'],
                           role=row['role'], name=row['name'])
            return jsonify({'success': True, 'role': row['role']})
        return jsonify({'success': False}), 401
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard(): return render_template('dashboard.html')

@app.route('/books')
@login_required
def books(): return render_template('books.html')

@app.route('/issues')
@login_required
def issues(): return render_template('issues.html')

@app.route('/reports')
@login_required
def reports(): return render_template('reports.html')

@app.route('/api/session-info')
@login_required
def session_info():
    return jsonify({'username': session['username'], 'name': session['name'], 'role': session['role']})


# ── API: Stats ────────────────────────────────────────────────────────────────

@app.route('/api/stats')
@login_required
def api_stats():
    total   = qry("SELECT COUNT(*) as cnt FROM books", one=True)['cnt']
    issued  = qry("SELECT COUNT(*) as cnt FROM issues WHERE status='Issued'", one=True)['cnt']
    avail   = qry("SELECT COALESCE(SUM(available_quantity),0) as s FROM books", one=True)['s']
    today   = date.today()
    overdue = qry("SELECT COUNT(*) as cnt FROM issues WHERE status='Issued' AND return_date<%s",
                  (today,), one=True)['cnt']
    recent_books  = [book_dict(r) for r in qry(
        "SELECT * FROM books ORDER BY date_of_entry DESC LIMIT 5")]
    recent_issues = [issue_dict(r) for r in qry(
        """SELECT i.*,b.title as book_title FROM issues i
           LEFT JOIN books b ON i.book_id=b.id ORDER BY i.issue_date DESC LIMIT 5""")]
    cats = qry("SELECT category, COUNT(*) as cnt FROM books WHERE category IS NOT NULL GROUP BY category")
    return jsonify({
        'total_books': total, 'issued_books': issued,
        'available_books': int(avail), 'overdue_books': overdue,
        'recent_books': recent_books, 'recent_issues': recent_issues,
        'category_distribution': [{'category': r['category'], 'count': r['cnt']} for r in cats]
    })


# ── API: Books ────────────────────────────────────────────────────────────────

@app.route('/api/books', methods=['GET'])
@login_required
def api_books():
    q        = request.args.get('q', '')
    category = request.args.get('category', '')
    status   = request.args.get('status', '')
    page     = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    sort_by  = request.args.get('sort_by', 'date_of_entry')
    sort_dir = request.args.get('sort_dir', 'desc')

    allowed = {'accession_number','title','author','date_of_entry','year_of_publication'}
    if sort_by not in allowed: sort_by = 'date_of_entry'
    order = f"{sort_by} {'DESC' if sort_dir=='desc' else 'ASC'}"

    where, params = [], []
    if q:
        where.append("(title ILIKE %s OR author ILIKE %s OR accession_number ILIKE %s OR isbn ILIKE %s)")
        params += [f'%{q}%'] * 4
    if category:
        where.append("category=%s"); params.append(category)
    if status:
        where.append("status=%s"); params.append(status)

    clause = ("WHERE " + " AND ".join(where)) if where else ""
    total  = qry(f"SELECT COUNT(*) as cnt FROM books {clause}", params, one=True)['cnt']
    rows   = qry(f"SELECT * FROM books {clause} ORDER BY {order} LIMIT %s OFFSET %s",
                 params + [per_page, (page-1)*per_page])
    return jsonify({
        'books': [book_dict(r) for r in rows], 'total': total,
        'page': page, 'pages': max(1, (total + per_page - 1) // per_page)
    })

@app.route('/api/books', methods=['POST'])
@login_required
def api_add_book():
    f = request.form
    if qry("SELECT id FROM books WHERE accession_number=%s", (f.get('accession_number'),), one=True):
        return jsonify({'error': 'Accession number already exists'}), 400

    qty = int(f.get('quantity', 1))
    cover = None
    if 'cover' in request.files:
        file = request.files['cover']
        if file and allowed_file(file.filename):
            fname = secure_filename(f"{f['accession_number']}_{file.filename}")
            file.save(os.path.join(UPLOAD_DIR, fname))
            cover = fname

    bid = qry("""INSERT INTO books
        (accession_number,title,author,publisher,edition,year_of_publication,
         department,category,shelf_number,quantity,available_quantity,isbn,cover_image)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
        (f['accession_number'], f['title'], f['author'], f.get('publisher'), f.get('edition'),
         int(f['year_of_publication']) if f.get('year_of_publication') else None,
         f.get('department', 'CSE'), f.get('category'), f.get('shelf_number'),
         qty, qty, f.get('isbn'), cover), commit=True)
    return jsonify({'success': True, 'book': book_dict(
        qry("SELECT * FROM books WHERE id=%s", (bid,), one=True))})

@app.route('/api/books/<int:bid>', methods=['PUT'])
@login_required
def api_update_book(bid):
    row = qry("SELECT * FROM books WHERE id=%s", (bid,), one=True)
    if not row: return jsonify({'error': 'Not found'}), 404
    f = request.form if request.form else request.get_json()
    old_qty   = row['quantity']
    new_qty   = int(f.get('quantity', old_qty))
    new_avail = max(0, row['available_quantity'] + (new_qty - old_qty))
    new_status = 'Available' if new_avail > 0 else 'Issued'
    cover = row['cover_image']
    if request.files and 'cover' in request.files:
        file = request.files['cover']
        if file and allowed_file(file.filename):
            fname = secure_filename(f"{row['accession_number']}_{file.filename}")
            file.save(os.path.join(UPLOAD_DIR, fname))
            cover = fname
    qry("""UPDATE books SET title=%s,author=%s,publisher=%s,edition=%s,year_of_publication=%s,
        department=%s,category=%s,shelf_number=%s,quantity=%s,available_quantity=%s,
        status=%s,isbn=%s,cover_image=%s WHERE id=%s""",
        (f.get('title', row['title']), f.get('author', row['author']), f.get('publisher'),
         f.get('edition'),
         int(f['year_of_publication']) if f.get('year_of_publication') else row['year_of_publication'],
         f.get('department', row['department']), f.get('category'), f.get('shelf_number'),
         new_qty, new_avail, new_status, f.get('isbn'), cover, bid), commit=True)
    return jsonify({'success': True, 'book': book_dict(
        qry("SELECT * FROM books WHERE id=%s", (bid,), one=True))})

@app.route('/api/books/<int:bid>', methods=['DELETE'])
@login_required
def api_delete_book(bid):
    active = qry("SELECT COUNT(*) as cnt FROM issues WHERE book_id=%s AND status='Issued'",
                 (bid,), one=True)['cnt']
    if active: return jsonify({'error': 'Cannot delete — book has active issues'}), 400
    qry("DELETE FROM books WHERE id=%s", (bid,), commit=True)
    return jsonify({'success': True})

@app.route('/api/books/categories')
@login_required
def api_categories():
    rows = qry("SELECT DISTINCT category FROM books WHERE category IS NOT NULL ORDER BY category")
    return jsonify([r['category'] for r in rows])


# ── API: Issues ───────────────────────────────────────────────────────────────

@app.route('/api/issues', methods=['GET'])
@login_required
def api_issues():
    status   = request.args.get('status', '')
    q        = request.args.get('q', '')
    page     = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))

    where, params = [], []
    if status: where.append("i.status=%s"); params.append(status)
    if q:
        where.append("(i.student_name ILIKE %s OR i.usn ILIKE %s OR i.accession_number ILIKE %s)")
        params += [f'%{q}%'] * 3

    clause = ("WHERE " + " AND ".join(where)) if where else ""
    total  = qry(f"SELECT COUNT(*) as cnt FROM issues i {clause}", params, one=True)['cnt']
    rows   = qry(f"""SELECT i.*,b.title as book_title FROM issues i
                     LEFT JOIN books b ON i.book_id=b.id
                     {clause} ORDER BY i.issue_date DESC LIMIT %s OFFSET %s""",
                 params + [per_page, (page-1)*per_page])
    return jsonify({
        'issues': [issue_dict(r) for r in rows], 'total': total,
        'page': page, 'pages': max(1, (total + per_page - 1) // per_page)
    })

@app.route('/api/issues', methods=['POST'])
@login_required
def api_issue_book():
    d   = request.get_json()
    row = qry("SELECT * FROM books WHERE accession_number=%s", (d.get('accession_number'),), one=True)
    if not row: return jsonify({'error': 'Book not found'}), 404
    if row['available_quantity'] < 1: return jsonify({'error': 'No copies available'}), 400

    today = date.today()
    iid   = qry("""INSERT INTO issues
                   (book_id,accession_number,student_name,usn,issue_date,return_date,status,issued_by)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                (row['id'], row['accession_number'], d['student_name'], d['usn'],
                 today, d['return_date'], 'Issued', session.get('username')), commit=True)
    new_avail = row['available_quantity'] - 1
    qry("UPDATE books SET available_quantity=%s, status=%s WHERE id=%s",
        (new_avail, 'Available' if new_avail > 0 else 'Issued', row['id']), commit=True)
    issue = issue_dict(qry(
        """SELECT i.*,b.title as book_title FROM issues i
           LEFT JOIN books b ON i.book_id=b.id WHERE i.id=%s""", (iid,), one=True))
    return jsonify({'success': True, 'issue': issue})

@app.route('/api/issues/<int:iid>/return', methods=['POST'])
@login_required
def api_return_book(iid):
    row = qry("SELECT * FROM issues WHERE id=%s", (iid,), one=True)
    if not row: return jsonify({'error': 'Not found'}), 404
    if row['status'] == 'Returned': return jsonify({'error': 'Already returned'}), 400

    today = date.today()
    due   = row['return_date'] if isinstance(row['return_date'], date) else date.fromisoformat(str(row['return_date']))
    fine  = max(0, (today - due).days) * 2.0

    qry("UPDATE issues SET status='Returned', actual_return_date=%s, fine=%s WHERE id=%s",
        (today, fine, iid), commit=True)
    book = qry("SELECT * FROM books WHERE id=%s", (row['book_id'],), one=True)
    qry("UPDATE books SET available_quantity=%s, status='Available' WHERE id=%s",
        (book['available_quantity'] + 1, row['book_id']), commit=True)
    return jsonify({'success': True, 'fine': fine})


# ── API: Reports / Export ─────────────────────────────────────────────────────

@app.route('/api/reports/export')
@login_required
def export_report():
    rtype = request.args.get('type', 'all_books')
    today = date.today()

    if rtype == 'all_books':
        rows = qry("SELECT * FROM books ORDER BY accession_number")
        headers = ['Accession No','Title','Author','Publisher','Edition','Year',
                   'Category','Shelf','Qty','Available','Status','Date Added']
        data = [[r['accession_number'],r['title'],r['author'],r['publisher'] or '',
                 r['edition'] or '',r['year_of_publication'] or '',r['category'] or '',
                 r['shelf_number'] or '',r['quantity'],r['available_quantity'],
                 r['status'],str(r['date_of_entry'])] for r in rows]
        fname = 'all_books'
    elif rtype == 'issued_books':
        rows = qry("""SELECT i.*,b.title as book_title FROM issues i
                      LEFT JOIN books b ON i.book_id=b.id WHERE i.status='Issued'""")
        headers = ['ID','Accession','Book Title','Student','USN','Issue Date','Due Date','Status']
        data = [[r['id'],r['accession_number'],r['book_title'] or '',r['student_name'],
                 r['usn'],str(r['issue_date']),str(r['return_date']),r['status']] for r in rows]
        fname = 'issued_books'
    elif rtype == 'overdue':
        rows = qry("""SELECT i.*,b.title as book_title FROM issues i
                      LEFT JOIN books b ON i.book_id=b.id
                      WHERE i.status='Issued' AND i.return_date<%s""", (today,))
        headers = ['ID','Accession','Book Title','Student','USN','Issue Date','Due Date','Days Overdue','Fine(Rs)']
        data = [[r['id'],r['accession_number'],r['book_title'] or '',r['student_name'],r['usn'],
                 str(r['issue_date']),str(r['return_date']),
                 (today - (r['return_date'] if isinstance(r['return_date'], date)
                           else date.fromisoformat(str(r['return_date'])))).days,
                 (today - (r['return_date'] if isinstance(r['return_date'], date)
                           else date.fromisoformat(str(r['return_date'])))).days * 2] for r in rows]
        fname = 'overdue_books'
    else:
        return jsonify({'error': 'Invalid type'}), 400

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    writer.writerows(data)
    buf.seek(0)
    return send_file(
        io.BytesIO(buf.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'{fname}_{today}.csv'
    )


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    print("\n✅ CMR Library started!")
    print("📌 Visit: http://localhost:5000")
    print("📚 Librarian: librarian / lib123\n")
    app.run(debug=True, port=5000)
