from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3, os, uuid
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "solvehub.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif", "svg", "jfif", "avif", "bmp", "tiff", "heic"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

app = Flask(__name__)
app.secret_key = "change-this-secret-key"
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max upload

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'student'
    );

    CREATE TABLE IF NOT EXISTS problems (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        location TEXT,
        category TEXT,
        urgency TEXT,
        people_affected INTEGER DEFAULT 0,
        status TEXT DEFAULT 'Submitted',
        expected_solution TEXT,
        image TEXT,
        created_by INTEGER,
        latitude REAL,
        longitude REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS solutions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        problem_id INTEGER NOT NULL,
        team_name TEXT NOT NULL,
        solution_text TEXT NOT NULL,
        technology TEXT,
        impact TEXT,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS supports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        problem_id INTEGER NOT NULL,
        user_id INTEGER,
        UNIQUE(problem_id, user_id)
    );

    CREATE TABLE IF NOT EXISTS problem_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        problem_id INTEGER NOT NULL,
        sender_id INTEGER NOT NULL,
        sender_name TEXT NOT NULL,
        sender_role TEXT NOT NULL,
        message TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        category TEXT,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        link TEXT,
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        problem_id INTEGER NOT NULL,
        user_id INTEGER,
        user_name TEXT NOT NULL,
        user_role TEXT DEFAULT 'Citizen',
        rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
        feedback_tag TEXT,
        comment TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(problem_id) REFERENCES problems(id)
    );
    """)
    conn.commit()

    # Migrate problems columns if not present
    cols = [col[1] for col in cur.execute("PRAGMA table_info(problems)").fetchall()]
    if "latitude" not in cols:
        cur.execute("ALTER TABLE problems ADD COLUMN latitude REAL")
    if "longitude" not in cols:
        cur.execute("ALTER TABLE problems ADD COLUMN longitude REAL")
    if "assigned_to" not in cols:
        cur.execute("ALTER TABLE problems ADD COLUMN assigned_to TEXT")
    if "assigned_at" not in cols:
        cur.execute("ALTER TABLE problems ADD COLUMN assigned_at TIMESTAMP")
    if "resolution_notes" not in cols:
        cur.execute("ALTER TABLE problems ADD COLUMN resolution_notes TEXT")
    if "resolved_at" not in cols:
        cur.execute("ALTER TABLE problems ADD COLUMN resolved_at TIMESTAMP")

    # Migrate users columns if not present
    user_cols = [col[1] for col in cur.execute("PRAGMA table_info(users)").fetchall()]
    if "organization" not in user_cols:
        cur.execute("ALTER TABLE users ADD COLUMN organization TEXT")
    if "category_interest" not in user_cols:
        cur.execute("ALTER TABLE users ADD COLUMN category_interest TEXT")

    if cur.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        users = [
            ("Admin", "admin@solvehub.com", generate_password_hash("admin123"), "admin", "SolveHub Civic Ops", "All"),
            ("Demo Student", "student@solvehub.com", generate_password_hash("student123"), "student", "Community Solver", "All"),
        ]
        cur.executemany("INSERT INTO users(name,email,password,role,organization,category_interest) VALUES(?,?,?,?,?,?)", users)

    # Ensure demo university solver exists
    solver_user = cur.execute("SELECT * FROM users WHERE email='university@solvehub.com'").fetchone()
    if not solver_user:
        cur.execute("""
            INSERT INTO users(name,email,password,role,organization,category_interest)
            VALUES(?,?,?,?,?,?)
        """, ("NIT Calicut Civil & Environmental Lab", "university@solvehub.com", generate_password_hash("solver123"), "university", "NIT Calicut Research Cell", "Waste Management"))

    # Seed initial discussion messages on problem 1 if empty
    if cur.execute("SELECT COUNT(*) FROM problem_messages").fetchone()[0] == 0:
        cur.execute("""
            INSERT INTO problem_messages(problem_id, sender_id, sender_name, sender_role, message)
            VALUES(?, ?, ?, ?, ?)
        """, (
            1, 2, "Demo Student (Citizen)", "citizen",
            "The waste bins on Beach Road have been overflowing for a week. Strays are scattering garbage onto the pedestrian pathway."
        ))
        cur.execute("""
            INSERT INTO problem_messages(problem_id, sender_id, sender_name, sender_role, message)
            VALUES(?, ?, ?, ?, ?)
        """, (
            1, 1, "Admin (Civic Ops)", "admin",
            "Complaint verified. We have flagged this as High Priority and routed it to the Civil & Environmental Engineering team for route scheduling and bin placement."
        ))

    # Seed initial notification if empty
    if cur.execute("SELECT COUNT(*) FROM notifications").fetchone()[0] == 0:
        cur.execute("""
            INSERT INTO notifications(category, title, message, link)
            VALUES(?, ?, ?, ?)
        """, (
            "Waste Management",
            "New Problem Reported: Poor Waste Collection in Kozhikode",
            "A new community problem in 'Waste Management' was reported at Kozhikode, Kerala affecting 450+ citizens. As a registered solver in this domain, review the report and propose a solution.",
            "/problem/1"
        ))

    if cur.execute("SELECT COUNT(*) FROM problems").fetchone()[0] == 0:
        demo = [
            ("Poor Waste Collection in Kozhikode",
             "Waste collection has become irregular in this locality. Garbage is piling up in residential areas, causing health and environmental concerns.",
             "Kozhikode, Kerala", "Waste Management", "High", 450, "Under Review",
             "A smart waste-collection scheduling and route optimization system.", "", 2, 11.2588, 75.7804),
            ("Frequent Power Cuts in Malappuram",
             "Residents and small businesses experience frequent interruptions and need better visibility into local power reliability.",
             "Malappuram, Kerala", "Infrastructure", "Medium", 300, "Solutions Received",
             "A low-cost monitoring and notification system.", "", 2, 11.0732, 76.0740),
            ("Lack of Proper Drainage System",
             "Heavy rain causes waterlogging because existing drainage channels are inadequate.",
             "Thrissur, Kerala", "Water & Sanitation", "High", 720, "Verified",
             "A community drainage monitoring and maintenance platform.", "", 2, 10.5276, 76.2144),
            ("Water Quality Monitoring",
             "A local water source needs regular quality monitoring and accessible reporting for residents.",
             "Kannur, Kerala", "Water", "Medium", 520, "Submitted",
             "IoT-based water-quality sensing with a public dashboard.", "", 2, 11.8745, 75.3704),
        ]
        cur.executemany("""
            INSERT INTO problems(title,description,location,category,urgency,people_affected,status,expected_solution,image,created_by,latitude,longitude)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
        """, demo)

    # Populate coordinates for demo problems if missing
    demo_coords = [
        (11.2588, 75.7804, "%Kozhikode%"),
        (11.0732, 76.0740, "%Malappuram%"),
        (10.5276, 76.2144, "%Thrissur%"),
        (11.8745, 75.3704, "%Kannur%"),
    ]
    for lat, lng, loc_pattern in demo_coords:
        cur.execute("UPDATE problems SET latitude=?, longitude=? WHERE location LIKE ? AND (latitude IS NULL OR longitude IS NULL)", (lat, lng, loc_pattern))

    # Populate default images for demo problems if missing
    cur.execute("UPDATE problems SET image='/static/uploads/waste_collection.svg' WHERE id=1 AND (image IS NULL OR image='')")
    cur.execute("UPDATE problems SET image='/static/uploads/power_cuts.svg' WHERE id=2 AND (image IS NULL OR image='')")
    cur.execute("UPDATE problems SET image='/static/uploads/drainage_overflow.svg' WHERE id=3 AND (image IS NULL OR image='')")
    cur.execute("UPDATE problems SET image='/static/uploads/water_quality.svg' WHERE id=4 AND (image IS NULL OR image='')")

    # Seed initial community reviews if empty
    if cur.execute("SELECT COUNT(*) FROM reviews").fetchone()[0] == 0:
        demo_reviews = [
            (1, 2, "Amina K. (Resident)", "Citizen", 5, "Fast Resolution", "NIT Calicut team placed sensor bins and municipal collection is on schedule now! Huge improvement on Beach Road."),
            (1, 1, "Rahul Menon (Community Leader)", "Citizen", 5, "High Quality Fix", "The overflow issue is completely resolved. Pedestrian pathway is finally clean and odor-free."),
            (1, None, "Dr. V. George (Local Merchant)", "Citizen", 4, "Responsive Team", "Good follow up from civic admin and the university lab. Great to see transparent tracking."),
            (3, 2, "Suresh Kumar (Resident)", "Citizen", 5, "Field Verified", "Corporation engineers cleared the drainage bottleneck. Rain runoff is now flowing smoothly."),
            (3, None, "Meera Nair (Resident)", "Citizen", 4, "Quick Action", "Response was much faster than regular municipal complaints. Love the live progress tracking."),
        ]
        cur.executemany("""
            INSERT INTO reviews(problem_id, user_id, user_name, user_role, rating, feedback_tag, comment)
            VALUES(?, ?, ?, ?, ?, ?, ?)
        """, demo_reviews)

    conn.commit()
    conn.close()

init_db()

def get_rating_summary(conn, problem_id):
    rows = conn.execute("SELECT rating FROM reviews WHERE problem_id=?", (problem_id,)).fetchall()
    total = len(rows)
    if total == 0:
        return {
            "average": 0.0,
            "total": 0,
            "stars_int": 0,
            "counts": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
            "pcts": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        }
    counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in rows:
        rating_val = int(r["rating"])
        if 1 <= rating_val <= 5:
            counts[rating_val] += 1
    avg = sum(k * v for k, v in counts.items()) / total
    pcts = {k: int(round((v / total) * 100)) for k, v in counts.items()}
    return {
        "average": round(avg, 1),
        "total": total,
        "stars_int": int(round(avg)),
        "counts": counts,
        "pcts": pcts
    }

def triage_text(text):
    text = " ".join(str(text or "").lower().split())
    rules = [
        ("Water & Drainage", ["flood","flooding","waterlog","drain","drainage","sewage","overflow","rain"], "Water & Sanitation Team", "High"),
        ("Roads & Infrastructure", ["road","pothole","bridge","footpath","sidewalk","traffic","crack","infrastructure","infrasrtucture"], "Infrastructure Response Team", "High"),
        ("Waste Management", ["garbage","waste","trash","dump","litter","collection","plastic"], "Waste Management Team", "Medium"),
        ("Street Safety & Lighting", ["light","lighting","lamp","dark","unsafe","streetlight","street light"], "Public Safety & Electrical Team", "High"),
        ("Water Supply", ["tap","drinking water","water shortage","pipeline","leak","cooler"], "Water Services Team", "High"),
        ("Electricity", ["power","electric","electricity","shock","wire","transformer","outage"], "Electrical Response Team", "High"),
        ("Campus & Facilities", ["campus","college","hostel","classroom","canteen","toilet","facility","maintenance"], "Institution Facilities Team", "Medium"),
        ("Connectivity", ["wifi","wi-fi","internet","network","signal"], "IT / Connectivity Team", "Medium"),
        ("Healthcare", ["hospital","clinic","ambulance","health","medical","medicine"], "Healthcare Coordination Team", "High"),
        ("Education", ["school","teacher","student","education","class","library"], "Education Support Team", "Medium"),
    ]
    best = None; score = 0
    for category, keywords, team, urgency in rules:
        points = sum(1 for k in keywords if k in text)
        if points > score: score, best = points, (category, team, urgency)
    if not best: best=("Other Community Issue","Civic Coordination Team","Medium")
    category, team, urgency = best
    return category, team, urgency, min(98,72+score*7)

def calculate_progress(problem):
    if not problem:
        return {"pct": 20, "step": 1, "label": "Report Submitted"}
    try:
        status = str(problem["status"] or "Submitted").strip()
    except Exception:
        status = "Submitted"
    try:
        assigned = bool(problem["assigned_to"]) if problem["assigned_to"] else False
    except Exception:
        assigned = False

    if status == "Completed":
        pct = 100
        step = 5
        label = "Resolved & Verified"
    elif status == "In Progress" or assigned:
        pct = 80
        step = 4
        label = "Field Action in Progress"
    elif status in ("Solution Selected", "Solutions Received"):
        pct = 60
        step = 3
        label = "Solutions Under Review"
    elif status in ("Verified", "Under Review"):
        pct = 40
        step = 2
        label = "AI Triaged & Verified"
    else:
        pct = 20
        step = 1
        label = "Report Submitted"
    return {"pct": pct, "step": step, "label": label}

@app.context_processor
def inject_globals():
    return {
        "logged_in": "user_id" in session,
        "current_user": session.get("user_name"),
        "user_role": session.get("role"),
        "calculate_progress": calculate_progress
    }

@app.route("/")
def index():
    conn = get_db()
    stats = {
        "problems": conn.execute("SELECT COUNT(*) FROM problems").fetchone()[0],
        "solved": conn.execute("SELECT COUNT(*) FROM problems WHERE status='Completed'").fetchone()[0],
        "in_progress": conn.execute("SELECT COUNT(*) FROM problems WHERE status IN ('In Progress','Solution Selected')").fetchone()[0],
        "universities": 18,
        "industry": 9
    }
    problems = conn.execute("SELECT * FROM problems ORDER BY id DESC LIMIT 3").fetchall()
    conn.close()
    return render_template("index.html", stats=stats, problems=problems)

@app.route("/api/triage", methods=["POST"])
def api_triage():
    payload=request.get_json(silent=True) or {}
    text=str(payload.get("text","")).strip()
    if not text:
        return jsonify({"ok":False,"message":"Describe the problem first."}),400
    category, team, urgency, confidence=triage_text(text)
    impact="Community-wide" if urgency=="High" else "Community"
    action="Verify location and assign a field inspection" if category in ("Water & Drainage","Roads & Infrastructure","Street Safety & Lighting") else "Review the report and route it to the responsible team"
    return jsonify({"ok":True,"category":category,"department":team,"urgency":urgency,"impact":impact,"action":action,"confidence":confidence})

@app.route("/explore")
def explore():
    conn = get_db()
    category = request.args.get("category", "")
    urgency = request.args.get("urgency", "")
    q = request.args.get("q", "")
    sql = """
        SELECT p.*, 
        (SELECT COUNT(*) FROM solutions WHERE problem_id=p.id) AS solution_count,
        (SELECT ROUND(AVG(rating), 1) FROM reviews WHERE problem_id=p.id) AS avg_rating,
        (SELECT COUNT(*) FROM reviews WHERE problem_id=p.id) AS review_count
        FROM problems p WHERE 1=1
    """
    args = []
    if category:
        sql += " AND p.category=?"; args.append(category)
    if urgency:
        sql += " AND p.urgency=?"; args.append(urgency)
    if q:
        sql += " AND (p.title LIKE ? OR p.description LIKE ? OR p.location LIKE ?)"
        args.extend([f"%{q}%", f"%{q}%", f"%{q}%"])
    sql += " ORDER BY p.id DESC"
    problems = conn.execute(sql, args).fetchall()
    categories = [r[0] for r in conn.execute("SELECT DISTINCT category FROM problems ORDER BY category").fetchall()]
    conn.close()
    return render_template("explore.html", problems=problems, categories=categories,
                           selected_category=category, selected_urgency=urgency, q=q)

@app.route("/map")
def problem_map():
    conn = get_db()
    problems = conn.execute("SELECT * FROM problems ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("map.html", problems=problems)

@app.route("/problem/<int:problem_id>")
def problem_detail(problem_id):
    conn = get_db()
    problem = conn.execute("SELECT * FROM problems WHERE id=?", (problem_id,)).fetchone()
    if not problem:
        conn.close()
        return "Problem not found", 404

    solutions = conn.execute("""
        SELECT s.*, u.name FROM solutions s
        LEFT JOIN users u ON u.id=s.created_by
        WHERE problem_id=? ORDER BY s.id DESC
    """, (problem_id,)).fetchall()
    support_count = conn.execute("SELECT COUNT(*) FROM supports WHERE problem_id=?", (problem_id,)).fetchone()[0]

    # 1. AI Analysis & Triage Data
    desc = problem["description"] or problem["title"] or ""
    category, team, urgency, confidence = triage_text(desc)
    active_category = problem["category"] or category
    active_urgency = problem["urgency"] or urgency

    impact = "Community-wide Impact" if active_urgency == "High" else "Local Locality Impact"
    action = (
        "Verify geo-coordinates and dispatch municipal field inspection task."
        if active_category in ("Water & Drainage", "Roads & Infrastructure", "Street Safety & Lighting")
        else "Route report to responsible department and cluster related community signals."
    )
    words = [w.strip(".,!?()\"'") for w in desc.lower().split()]
    stopwords = {"about", "their", "there", "which", "could", "would", "should", "people", "problem", "solution", "after", "before", "because"}
    signals = list(dict.fromkeys([w for w in words if len(w) > 4 and w not in stopwords]))[:6]

    ai_data = {
        "category": active_category,
        "team": team,
        "urgency": active_urgency,
        "confidence": confidence,
        "impact": impact,
        "action": action,
        "signals": signals,
        "sla": "24 - 48 Hours" if active_urgency == "High" else "3 - 5 Days"
    }

    # 2. Similar Problems in the community
    similar_problems = conn.execute("""
        SELECT * FROM problems 
        WHERE id != ? AND (category = ? OR category LIKE ? OR title LIKE ?)
        ORDER BY id DESC LIMIT 4
    """, (problem_id, active_category, f"%{active_category[:5]}%", f"%{active_category[:5]}%")).fetchall()

    if len(similar_problems) < 2:
        additional = conn.execute("""
            SELECT * FROM problems WHERE id != ? ORDER BY id DESC LIMIT 4
        """, (problem_id,)).fetchall()
        seen = {p["id"] for p in similar_problems}
        similar_problems = list(similar_problems) + [p for p in additional if p["id"] not in seen]
        similar_problems = similar_problems[:4]

    # 3. Dynamic Recommended Collaborators based on category
    collaborator_map = {
        "Waste Management": [
            {"role": "University Lab", "name": "Environmental Engineering & Waste Systems Cell", "dept": "NIT Calicut / CET", "match": "96%", "icon": "🎓", "specialty": "Circular waste logistics, organic degradation & route optimization"},
            {"role": "Industry Partner", "name": "EcoSmart Waste IoT Solutions", "dept": "CleanTech Ventures", "match": "92%", "icon": "🏢", "specialty": "Sensor-enabled bin tracking and scheduled fleet routing"},
            {"role": "Student Innovators", "name": "ZeroWaste Campus Hackers", "dept": "SolveHub Student Network", "match": "88%", "icon": "💡", "specialty": "Community reporting dashboard & incentive tracking"}
        ],
        "Water & Sanitation": [
            {"role": "University Lab", "name": "Hydrology & Drainage Systems Research Group", "dept": "Civil Engineering Faculty", "match": "95%", "icon": "🎓", "specialty": "Runoff simulation, drainage capacity calculation & flood barriers"},
            {"role": "Municipal Cell", "name": "Public Health & Sanitation Taskforce", "dept": "Municipal Corporation", "match": "91%", "icon": "🏛️", "specialty": "Rapid drainage clearance and field intervention"},
            {"role": "Student Innovators", "name": "IoT Water Sense Team", "dept": "Electronics & CSE Lab", "match": "89%", "icon": "💡", "specialty": "Low-cost waterlogging depth sensors with telemetry"}
        ],
        "Roads & Infrastructure": [
            {"role": "University Lab", "name": "Urban Transportation & Pavement Engineering", "dept": "Engineering Research Cell", "match": "94%", "icon": "🎓", "specialty": "Pothole durability materials and asphalt quality analysis"},
            {"role": "Industry Partner", "name": "RoadVision GeoTech", "dept": "Smart Infrastructure Pvt", "match": "90%", "icon": "🏢", "specialty": "AI pothole computer vision mapping & repair scheduling"},
            {"role": "Student Innovators", "name": "Civic Mobility Lab", "dept": "Student Innovation Collective", "match": "87%", "icon": "💡", "specialty": "Citizen crowd-sourced road condition mobile apps"}
        ],
        "Street Safety & Lighting": [
            {"role": "University Lab", "name": "Public Safety & Power Electronics Lab", "dept": "Electrical Engineering", "match": "93%", "icon": "🎓", "specialty": "Solar smart street lighting and low-power mesh networks"},
            {"role": "Industry Partner", "name": "LumiGrid Municipal Systems", "dept": "Energy Solutions", "match": "89%", "icon": "🏢", "specialty": "Automated lamp failure telemetry and LED retrofit"},
            {"role": "Community Group", "name": "Safe Streets Citizens Council", "dept": "Community Volunteer Alliance", "match": "86%", "icon": "🛡️", "specialty": "Night safety audits and pedestrian security advocacy"}
        ]
    }
    collaborators = collaborator_map.get(active_category, [
        {"role": "University Lab", "name": "Civic Systems & Public Engineering Cell", "dept": "State Engineering Faculty", "match": "92%", "icon": "🎓", "specialty": "Public issue analysis, structural assessment and technical documentation"},
        {"role": "Industry Partner", "name": "SmartCity Solutions Group", "dept": "Civic Tech Implementation", "match": "88%", "icon": "🏢", "specialty": "Rapid prototyping, technology scaling and pilot deployment"},
        {"role": "Student Innovators", "name": "SolveHub Student Rapid Solvers", "dept": "Multi-disciplinary Student Cell", "match": "85%", "icon": "💡", "specialty": "Software prototypes, community verification and survey workflows"}
    ])

    messages = conn.execute("""
        SELECT * FROM problem_messages WHERE problem_id=? ORDER BY id ASC
    """, (problem_id,)).fetchall()

    # Community Public Reviews & Ratings
    reviews = conn.execute("""
        SELECT * FROM reviews WHERE problem_id=? ORDER BY id DESC
    """, (problem_id,)).fetchall()
    rating_summary = get_rating_summary(conn, problem_id)

    conn.close()
    return render_template(
        "problem_detail.html",
        problem=problem,
        solutions=solutions,
        support_count=support_count,
        ai_data=ai_data,
        similar_problems=similar_problems,
        collaborators=collaborators,
        messages=messages,
        reviews=reviews,
        rating_summary=rating_summary
    )

@app.route("/problem/<int:problem_id>/review", methods=["POST"])
def post_problem_review(problem_id):
    if "user_id" not in session:
        flash("Please log in or create an account to post a review and rating.", "warning")
        return redirect(url_for("login", next=url_for("problem_detail", problem_id=problem_id)))
    
    conn = get_db()
    prob = conn.execute("SELECT * FROM problems WHERE id=?", (problem_id,)).fetchone()
    if not prob:
        conn.close()
        return "Problem not found", 404
        
    try:
        rating = int(request.form.get("rating", 5))
        if rating < 1 or rating > 5:
            rating = 5
    except (ValueError, TypeError):
        rating = 5
        
    comment = request.form.get("comment", "").strip()
    feedback_tag = request.form.get("feedback_tag", "").strip() or "Civic Feedback"
    
    if not comment:
        flash("Please provide a short written review or feedback comment.", "warning")
        conn.close()
        return redirect(url_for("problem_detail", problem_id=problem_id))
        
    user_name = session.get("user_name", "Citizen Contributor")
    user_role = session.get("role", "Citizen").title()
    
    conn.execute("""
        INSERT INTO reviews(problem_id, user_id, user_name, user_role, rating, feedback_tag, comment)
        VALUES(?, ?, ?, ?, ?, ?, ?)
    """, (problem_id, session["user_id"], user_name, user_role, rating, feedback_tag, comment))
    conn.commit()
    conn.close()
    
    flash("Thank you! Your community review and rating have been posted publicly.", "success")
    return redirect(url_for("problem_detail", problem_id=problem_id))

@app.route("/features")
def features():
    return render_template("features.html")

@app.route("/organizations")
def organizations():
    return render_template("organizations.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        message = request.form.get("message", "").strip()
        if not name or not email or not message:
            flash("Please complete your name, email and message.", "danger")
            return redirect(url_for("contact"))
        # Demo/local deployment: store contact submissions in a lightweight table.
        conn = get_db()
        conn.execute("CREATE TABLE IF NOT EXISTS contact_messages (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT, message TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        conn.execute("INSERT INTO contact_messages(name,email,message) VALUES(?,?,?)", (name, email, message))
        conn.commit()
        conn.close()
        flash("Message received. The SolveHub team can follow up from the dashboard/database.", "success")
        return redirect(url_for("contact"))
    return render_template("contact.html")

@app.route("/report", methods=["GET", "POST"])
def report():
    if "user_id" not in session:
        flash("Sign in or create a free account to report a civic issue.", "warning")
        return redirect(url_for("login", next="report"))
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        location = request.form.get("location", "").strip()
        people = request.form.get("people_affected", "0") or 0
        expected = request.form.get("expected_solution", "").strip()
        lat = request.form.get("latitude", "").strip()
        lng = request.form.get("longitude", "").strip()

        if not title or not description:
            flash("Please provide both a problem title and description.", "danger")
            return render_template("report.html")

        t_cat, _team, t_urg, _confidence = triage_text(f"{title} {description}")
        req_cat = request.form.get("category", "").strip()
        req_urg = request.form.get("urgency", "").strip()
        category = req_cat if req_cat and req_cat != "Other Community Issue" else t_cat
        urgency = req_urg if req_urg else t_urg

        try:
            latitude = float(lat) if lat else None
            longitude = float(lng) if lng else None
        except (TypeError, ValueError):
            latitude, longitude = None, None

        try:
            people_count = max(0, int(people or 0))
        except (TypeError, ValueError):
            people_count = 0

        # Handle uploaded problem image or image URL
        image_path = ""
        if "image" in request.files:
            file = request.files["image"]
            if file and file.filename and allowed_file(file.filename):
                ext = file.filename.rsplit(".", 1)[1].lower()
                unique_name = f"problem_{uuid.uuid4().hex[:10]}.{ext}"
                file.save(os.path.join(UPLOAD_FOLDER, unique_name))
                image_path = f"/static/uploads/{unique_name}"
        if not image_path:
            url_img = request.form.get("image_url", "").strip()
            if url_img:
                image_path = url_img

        conn = get_db()
        cur = conn.execute("""
            INSERT INTO problems(title,description,location,category,urgency,people_affected,status,expected_solution,image,created_by,latitude,longitude)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
        """, (title, description, location, category, urgency, people_count, "Submitted", expected, image_path, session["user_id"], latitude, longitude))
        conn.commit()
        pid = cur.lastrowid

        # Automated default alert to problem solvers / universities in this category
        alert_msg = f"A new problem in '{category}' was reported at '{location or 'Community area'}' affecting {people_count}+ citizens. As a registered solver in this domain, your team can review the issue and propose a solution."
        conn.execute("""
            INSERT INTO notifications(category, title, message, link)
            VALUES(?, ?, ?, ?)
        """, (category, f"New Problem Reported: {title}", alert_msg, f"/problem/{pid}"))
        conn.commit()
        conn.close()
        flash("Problem submitted successfully!", "success")
        return redirect(url_for("problem_detail", problem_id=pid))
    return render_template("report.html")

@app.route("/problem/<int:problem_id>/solution", methods=["GET", "POST"])
def solution(problem_id):
    if "user_id" not in session:
        flash("Please login to propose a solution.", "warning")
        return redirect(url_for("login"))
    conn = get_db()
    problem = conn.execute("SELECT * FROM problems WHERE id=?", (problem_id,)).fetchone()
    if not problem:
        conn.close()
        return "Problem not found", 404
    if request.method == "POST":
        conn.execute("""
            INSERT INTO solutions(problem_id,team_name,solution_text,technology,impact,created_by)
            VALUES(?,?,?,?,?,?)
        """, (
            problem_id,
            request.form["team_name"],
            request.form["solution_text"],
            request.form.get("technology", ""),
            request.form.get("impact", ""),
            session["user_id"]
        ))
        conn.execute("UPDATE problems SET status='Solutions Received' WHERE id=? AND status IN ('Submitted','Verified','Under Review')", (problem_id,))
        conn.commit()
        conn.close()
        flash("Your solution has been submitted!", "success")
        return redirect(url_for("problem_detail", problem_id=problem_id))
    conn.close()
    return render_template("solution.html", problem=problem)

@app.route("/support/<int:problem_id>", methods=["POST"])
def support(problem_id):
    if "user_id" not in session:
        return jsonify({"ok": False, "message": "Login required"}), 401
    conn = get_db()
    try:
        conn.execute("INSERT INTO supports(problem_id,user_id) VALUES(?,?)", (problem_id, session["user_id"]))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    count = conn.execute("SELECT COUNT(*) FROM supports WHERE problem_id=?", (problem_id,)).fetchone()[0]
    conn.close()
    return jsonify({"ok": True, "count": count})

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["role"] = user["role"]
            flash(f"Welcome back, {user['name']}!", "success")
            next_page = request.args.get("next") or request.form.get("next")
            if next_page:
                if next_page == "report":
                    return redirect(url_for("report"))
                elif next_page.startswith("/") and not next_page.startswith("//"):
                    return redirect(next_page)
            if user["role"] == "admin":
                return redirect(url_for("admin"))
            elif user["role"] in ("university", "solver"):
                return redirect(url_for("solver_dashboard"))
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "student")
        organization = request.form.get("organization", "").strip()
        category_interest = request.form.get("category_interest", "All").strip()
        if not name or not email or not password:
            flash("Please complete all required fields.", "danger")
            return render_template("signup.html")
        conn = get_db()
        try:
            cur = conn.execute("""
                INSERT INTO users(name,email,password,role,organization,category_interest)
                VALUES(?,?,?,?,?,?)
            """, (name, email, generate_password_hash(password), role, organization, category_interest))
            conn.commit()
            uid = cur.lastrowid
            session["user_id"] = uid
            session["user_name"] = name
            session["role"] = role
            conn.close()
            flash("Account created successfully! Welcome to SolveHub.", "success")
            next_page = request.form.get("next") or request.args.get("next")
            if next_page:
                if next_page == "report":
                    return redirect(url_for("report"))
                elif next_page.startswith("/") and not next_page.startswith("//"):
                    return redirect(next_page)
            if role in ("university", "solver"):
                return redirect(url_for("solver_dashboard"))
            elif role == "admin":
                return redirect(url_for("admin"))
            return redirect(url_for("dashboard"))
        except sqlite3.IntegrityError:
            conn.close()
            flash("An account with that email already exists.", "danger")
    return render_template("signup.html")

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if request.args.get("view") != "citizen":
        if session.get("role") in ("university", "solver"):
            return redirect(url_for("solver_dashboard"))
        if session.get("role") == "admin":
            return redirect(url_for("admin"))
    conn = get_db()
    my_problems = conn.execute("""
        SELECT p.*, 
        (SELECT ROUND(AVG(rating), 1) FROM reviews WHERE problem_id=p.id) AS avg_rating,
        (SELECT COUNT(*) FROM reviews WHERE problem_id=p.id) AS review_count
        FROM problems p WHERE created_by=? ORDER BY id DESC
    """, (session["user_id"],)).fetchall()
    all_problems = conn.execute("""
        SELECT p.*, 
        (SELECT COUNT(*) FROM solutions WHERE problem_id=p.id) AS solution_count,
        (SELECT ROUND(AVG(rating), 1) FROM reviews WHERE problem_id=p.id) AS avg_rating,
        (SELECT COUNT(*) FROM reviews WHERE problem_id=p.id) AS review_count
        FROM problems p ORDER BY p.id DESC LIMIT 20
    """).fetchall()
    my_solutions = conn.execute("""
        SELECT s.*, p.title FROM solutions s JOIN problems p ON p.id=s.problem_id
        WHERE s.created_by=? ORDER BY s.id DESC
    """, (session["user_id"],)).fetchall()
    counts = {
        "total": len(my_problems),
        "solutions": len(my_solutions),
        "in_progress": sum(1 for p in my_problems if p["status"] in ("In Progress", "Solution Selected", "Solutions Received", "Under Review", "Verified")),
        "completed": sum(1 for p in my_problems if p["status"] == "Completed"),
        "community_total": len(all_problems),
        "community_resolved": sum(1 for p in all_problems if p["status"] == "Completed")
    }
    conn.close()
    return render_template("dashboard.html", my_problems=my_problems, all_problems=all_problems, my_solutions=my_solutions, counts=counts)

@app.route("/problems")
def problems_redirect():
    return redirect(url_for("explore"))

@app.route("/progress")
@app.route("/progresses")
def progress_redirect():
    return redirect(url_for("explore"))

@app.route("/solver/dashboard")
def solver_dashboard():
    if "user_id" not in session:
        flash("Please log in to access the Solver Dashboard.", "warning")
        return redirect(url_for("login"))
    
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    user_cat = user["category_interest"] if user and user["category_interest"] and user["category_interest"] != "All" else None
    user_org = user["organization"] if user and user["organization"] else (user["name"] if user else "")
    user_name = user["name"] if user else ""

    # 1. Problems Assigned to this Solver or their Lab/Institution
    assigned_problems = conn.execute("""
        SELECT p.*,
        (SELECT ROUND(AVG(rating), 1) FROM reviews WHERE problem_id=p.id) AS avg_rating,
        (SELECT COUNT(*) FROM reviews WHERE problem_id=p.id) AS review_count
        FROM problems p 
        WHERE (assigned_to LIKE ? OR assigned_to LIKE ? OR created_by=?)
        ORDER BY id DESC
    """, (f"%{user_name}%", f"%{user_org}%", session["user_id"])).fetchall()

    # If no explicitly assigned, find problems in progress
    if not assigned_problems:
        assigned_problems = conn.execute("""
            SELECT p.*,
            (SELECT ROUND(AVG(rating), 1) FROM reviews WHERE problem_id=p.id) AS avg_rating,
            (SELECT COUNT(*) FROM reviews WHERE problem_id=p.id) AS review_count
            FROM problems p WHERE status IN ('In Progress', 'Solution Selected') ORDER BY id DESC LIMIT 5
        """).fetchall()

    # 2. Automated Category Alerts & Notifications
    if user_cat:
        notifications = conn.execute("""
            SELECT * FROM notifications 
            WHERE category=? OR category='All' OR user_id=?
            ORDER BY id DESC LIMIT 15
        """, (user_cat, session["user_id"])).fetchall()
    else:
        notifications = conn.execute("""
            SELECT * FROM notifications ORDER BY id DESC LIMIT 15
        """).fetchall()

    # 3. Domain Problems in their Category
    if user_cat:
        domain_problems = conn.execute("""
            SELECT p.*,
            (SELECT ROUND(AVG(rating), 1) FROM reviews WHERE problem_id=p.id) AS avg_rating,
            (SELECT COUNT(*) FROM reviews WHERE problem_id=p.id) AS review_count
            FROM problems p 
            WHERE category=? ORDER BY id DESC LIMIT 10
        """, (user_cat,)).fetchall()
    else:
        domain_problems = conn.execute("""
            SELECT p.*,
            (SELECT ROUND(AVG(rating), 1) FROM reviews WHERE problem_id=p.id) AS avg_rating,
            (SELECT COUNT(*) FROM reviews WHERE problem_id=p.id) AS review_count
            FROM problems p ORDER BY id DESC LIMIT 10
        """).fetchall()

    # 4. Solutions submitted by this team
    my_solutions = conn.execute("""
        SELECT s.*, p.title, p.status as problem_status FROM solutions s 
        JOIN problems p ON p.id=s.problem_id
        WHERE s.created_by=? ORDER BY s.id DESC
    """, (session["user_id"],)).fetchall()

    stats = {
        "assigned": len(assigned_problems),
        "in_progress": sum(1 for p in assigned_problems if p["status"] in ("In Progress", "Solution Selected")),
        "resolved": sum(1 for p in assigned_problems if p["status"] == "Completed"),
        "solutions_proposed": len(my_solutions),
        "category_alerts": len(notifications),
        "domain_count": len(domain_problems)
    }
    conn.close()

    return render_template(
        "solver_dashboard.html",
        user=user,
        stats=stats,
        assigned_problems=assigned_problems,
        notifications=notifications,
        domain_problems=domain_problems,
        my_solutions=my_solutions,
        user_cat=user_cat or "All Categories"
    )

@app.route("/problem/<int:problem_id>/message", methods=["POST"])
def post_problem_message(problem_id):
    if "user_id" not in session:
        flash("Please log in to participate in the civic discussion.", "warning")
        return redirect(url_for("login"))
    message_text = request.form.get("message", "").strip()
    ref = request.referrer or url_for("problem_detail", problem_id=problem_id)
    if not message_text:
        flash("Message cannot be empty.", "warning")
        return redirect(ref)
    
    conn = get_db()
    sender_role = session.get("role", "citizen")
    sender_name = session.get("user_name", "Contributor")
    conn.execute("""
        INSERT INTO problem_messages(problem_id, sender_id, sender_name, sender_role, message)
        VALUES(?, ?, ?, ?, ?)
    """, (problem_id, session["user_id"], sender_name, sender_role, message_text))
    conn.commit()
    conn.close()
    flash("Message posted to civic discussion thread.", "success")
    return redirect(ref)

@app.route("/solver/problem/<int:problem_id>/resolve", methods=["POST"])
def solver_resolve_problem(problem_id):
    if "user_id" not in session:
        flash("Please log in.", "warning")
        return redirect(url_for("login"))
    
    if session.get("role") not in ("university", "solver", "admin"):
        flash("Only assigned university solvers and admins can submit official resolution reports.", "danger")
        return redirect(url_for("problem_detail", problem_id=problem_id))
    
    resolution_notes = request.form.get("resolution_notes", "").strip()
    if not resolution_notes:
        resolution_notes = "Technical solution, field implementation, and verification completed by university solver team."
    
    conn = get_db()
    problem = conn.execute("SELECT * FROM problems WHERE id=?", (problem_id,)).fetchone()
    assigned = problem["assigned_to"] if problem and problem["assigned_to"] else session.get("user_name")

    conn.execute("""
        UPDATE problems 
        SET status='Completed', resolution_notes=?, resolved_at=CURRENT_TIMESTAMP, assigned_to=?
        WHERE id=?
    """, (resolution_notes, assigned, problem_id))
    conn.commit()
    conn.close()
    flash(f"Problem #{problem_id} marked as Resolved! Official report published.", "success")
    ref = request.referrer or url_for("problem_detail", problem_id=problem_id)
    return redirect(ref)

@app.route("/admin")
def admin():
    if session.get("role") != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("dashboard"))
    filter_type = request.args.get("filter", "all")
    conn = get_db()
    query_prefix = """
        SELECT p.*,
        (SELECT ROUND(AVG(rating), 1) FROM reviews WHERE problem_id=p.id) AS avg_rating,
        (SELECT COUNT(*) FROM reviews WHERE problem_id=p.id) AS review_count
        FROM problems p
    """
    if filter_type == "unassigned":
        problems = conn.execute(query_prefix + " WHERE (assigned_to IS NULL OR assigned_to='') AND status != 'Completed' ORDER BY id DESC").fetchall()
    elif filter_type == "in_progress":
        problems = conn.execute(query_prefix + " WHERE status IN ('In Progress', 'Solution Selected', 'Under Review') ORDER BY id DESC").fetchall()
    elif filter_type == "resolved":
        problems = conn.execute(query_prefix + " WHERE status='Completed' ORDER BY id DESC").fetchall()
    else:
        problems = conn.execute(query_prefix + " ORDER BY id DESC").fetchall()

    stats = {
        "total": conn.execute("SELECT COUNT(*) FROM problems").fetchone()[0],
        "solved": conn.execute("SELECT COUNT(*) FROM problems WHERE status='Completed'").fetchone()[0],
        "in_progress": conn.execute("SELECT COUNT(*) FROM problems WHERE status IN ('In Progress', 'Solution Selected', 'Under Review')").fetchone()[0],
        "unassigned": conn.execute("SELECT COUNT(*) FROM problems WHERE (assigned_to IS NULL OR assigned_to='') AND status != 'Completed'").fetchone()[0],
        "industry": 9
    }
    solvers = conn.execute("SELECT id, name, organization, category_interest, email FROM users WHERE role IN ('university', 'solver')").fetchall()
    conn.close()
    return render_template("admin.html", problems=problems, stats=stats, current_filter=filter_type, solvers=solvers)

@app.route("/admin/status/<int:problem_id>", methods=["POST"])
def update_status(problem_id):
    if session.get("role") != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("login"))
    status = request.form.get("status")
    allowed = ["Submitted", "Verified", "Solutions Received", "Solution Selected", "In Progress", "Completed"]
    ref = request.referrer or url_for("admin")
    if status not in allowed:
        flash("Invalid status.", "danger")
        return redirect(ref)
    conn = get_db()
    conn.execute("UPDATE problems SET status=? WHERE id=?", (status, problem_id))
    conn.commit()
    conn.close()
    flash(f"Problem #{problem_id} status updated to {status}.", "success")
    return redirect(ref)

@app.route("/admin/problem/<int:problem_id>/assign", methods=["POST"])
def assign_problem(problem_id):
    if session.get("role") != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("login"))
    assigned_to = request.form.get("assigned_to", "").strip()
    status = request.form.get("status", "In Progress").strip()
    ref = request.referrer or url_for("admin")
    if not assigned_to:
        flash("Please provide a team, department, or solver name to assign.", "warning")
        return redirect(ref)

    conn = get_db()
    conn.execute("""
        UPDATE problems 
        SET assigned_to=?, assigned_at=CURRENT_TIMESTAMP, status=?
        WHERE id=?
    """, (assigned_to, status, problem_id))

    # Send automated alert to the assigned solver if matched
    prob = conn.execute("SELECT title, category FROM problems WHERE id=?", (problem_id,)).fetchone()
    clean_assignee = assigned_to.split("(")[0].strip()
    matched_solver = conn.execute("""
        SELECT id, name FROM users 
        WHERE (name LIKE ? OR organization LIKE ?) AND role IN ('university', 'solver')
    """, (f"%{clean_assignee}%", f"%{clean_assignee}%")).fetchone()
    user_id = matched_solver["id"] if matched_solver else None
    prob_title = prob["title"] if prob else f"Problem #{problem_id}"
    cat = prob["category"] if prob else "General"
    conn.execute("""
        INSERT INTO notifications(user_id, category, title, message, link)
        VALUES(?, ?, ?, ?, ?)
    """, (user_id, cat, f"Directly Assigned: {prob_title}", f"Civic Admin officially assigned problem #{problem_id} to you / your research lab. Status set to '{status}'.", f"/problem/{problem_id}"))

    conn.commit()
    conn.close()
    flash(f"Problem #{problem_id} assigned to '{assigned_to}' (Status set to {status}).", "success")
    return redirect(ref)

@app.route("/admin/problem/<int:problem_id>/resolve", methods=["POST"])
def resolve_problem(problem_id):
    if session.get("role") != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("login"))
    resolution_notes = request.form.get("resolution_notes", "").strip()
    ref = request.referrer or url_for("admin")
    if not resolution_notes:
        resolution_notes = "Official civic intervention completed and community verified."

    conn = get_db()
    conn.execute("""
        UPDATE problems 
        SET status='Completed', resolution_notes=?, resolved_at=CURRENT_TIMESTAMP
        WHERE id=?
    """, (resolution_notes, problem_id))
    conn.commit()
    conn.close()
    flash(f"Problem #{problem_id} has been marked as Resolved & Completed!", "success")
    return redirect(ref)

@app.route("/admin/problem/<int:problem_id>/reopen", methods=["POST"])
def reopen_problem(problem_id):
    if session.get("role") != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("login"))
    status = request.form.get("status", "In Progress").strip()
    ref = request.referrer or url_for("admin")
    conn = get_db()
    conn.execute("UPDATE problems SET status=? WHERE id=?", (status, problem_id))
    conn.commit()
    conn.close()
    flash(f"Problem #{problem_id} reopened (Status: {status}).", "info")
    return redirect(ref)

@app.route("/admin/export")
def admin_export():
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    import csv, io
    conn = get_db()
    rows = conn.execute("SELECT id,title,location,category,urgency,people_affected,status,assigned_to,resolution_notes,created_at FROM problems ORDER BY id DESC").fetchall()
    conn.close()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID","Title","Location","Category","Priority","People Affected","Status","Assigned To","Resolution Notes","Created At"])
    writer.writerows([tuple(row) for row in rows])
    from flask import Response
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition":"attachment; filename=solvehub-problems.csv"})

@app.route("/admin/users")
def admin_users():
    if session.get("role") != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("dashboard"))
    conn=get_db(); users=conn.execute("SELECT id,name,email,role FROM users ORDER BY id DESC").fetchall(); conn.close()
    return render_template("admin_users.html", users=users)

@app.route("/admin/solutions")
def admin_solutions():
    if session.get("role") != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("dashboard"))
    conn=get_db(); solutions=conn.execute("SELECT s.*, p.title, u.name FROM solutions s JOIN problems p ON p.id=s.problem_id LEFT JOIN users u ON u.id=s.created_by ORDER BY s.id DESC").fetchall(); conn.close()
    return render_template("admin_solutions.html", solutions=solutions)

@app.route("/admin/settings")
def admin_settings():
    if session.get("role") != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("dashboard"))
    return render_template("admin_settings.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))

@app.route("/api/stats")
def api_stats():
    conn = get_db()
    data = {
        "problems": conn.execute("SELECT COUNT(*) FROM problems").fetchone()[0],
        "solved": conn.execute("SELECT COUNT(*) FROM problems WHERE status='Completed'").fetchone()[0],
        "in_progress": conn.execute("SELECT COUNT(*) FROM problems WHERE status='In Progress'").fetchone()[0],
        "solutions": conn.execute("SELECT COUNT(*) FROM solutions").fetchone()[0]
    }
    conn.close()
    return jsonify(data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
