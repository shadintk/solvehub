# 🏛️ SolveHub — Civic Problem-Solving & Governance Platform

SolveHub is a modern, full-stack civic engagement and problem resolution ecosystem. It connects **Citizens**, **Municipal Administrators**, and **University Problem Solvers** (research labs, engineering colleges, and technical institutions) into a unified, transparent workflow to report, assign, track, and resolve community challenges.

---

## 🌟 Key Features

1. **Intelligent Civic Reporting**:
   - **Local AI Triage**: Automatically categorizes problems (Infrastructure, Water & Sanitation, Electrical, Environment, Waste Management) and calculates urgency scores in real-time.
   - **Real-Time Interactive Geolocation**: Pinpoint issues on a Leaflet map with GPS one-click detection and address/landmark search.
   - **Field Photo Evidence**: Citizens can upload camera photos or evidence images (JPEG, PNG, WebP) with inline verification cards.

2. **Role-Based Portals & Dashboards**:
   - **Citizen / Student Portal**: Track submitted reports, watch live lifecycle progress, upvote issues, and submit community ratings.
   - **Admin Governance Center**: Dispatch challenges, assign university teams, monitor SLA resolution velocity, update lifecycle stages, and export CSV reports.
   - **University Solver Hub**: Specialized dashboard for academic institutions and research teams to review assigned challenges, receive category-based challenge alerts, collaborate via civic discussion threads, and submit official verified solutions.

3. **Transparent 5-Stage Problem Lifecycle**:
   - `Submitted` ➔ `Under Review` ➔ `Assigned` ➔ `In Progress` ➔ `Completed (Resolved)`.

4. **Public Reviews & 5-Star Rating System**:
   - Real-time rating scorecard displaying community trust metrics, average ratings, and public feedback visible to all citizens and evaluators.

5. **Civic Discussion & Collaboration Threads**:
   - Two-way communication between citizens, administrators, and university solvers on every problem page.

---

## 🔐 Demo Accounts

| Role | Email | Password | Access / Capabilities |
| :--- | :--- | :--- | :--- |
| **Municipal Admin** | `admin@solvehub.com` | `admin123` | Governance Center, team assignment, stage updates, CSV export |
| **Citizen / Reporter** | `student@solvehub.com` | `student123` | Report problems, upload photo evidence, track progress, review solutions |
| **University Solver** | `university@solvehub.com` | `solver123` | University Hub, category challenge alerts, resolve issues, post updates |

*(New users can also self-register anytime via the Sign Up page with their preferred role).*

---

## 🚀 Running Locally

### Prerequisites
- Python 3.8 or higher installed on your computer.

### Quick Start (Windows)
Double-click `run.bat` or run:
```bash
python -m pip install -r requirements.txt
python app.py
```

### Quick Start (macOS / Linux)
```bash
python3 -m pip install -r requirements.txt
python3 app.py
```

Open your browser and navigate to: **`http://127.0.0.1:5000`**

---

## ☁️ Deployment Guide

### Deploying to GitHub
1. Open terminal in this folder.
2. Initialize and push your repository:
   ```bash
   git init
   git add .
   git commit -m "Initial commit: SolveHub Platform"
   git branch -M main
   git remote add origin https://github.com/<your-username>/<your-repo-name>.git
   git push -u origin main
   ```

### 1-Click Free Cloud Deployment (Render.com)
SolveHub includes a preconfigured `Procfile` (`web: gunicorn app:app`) and `requirements.txt`:
1. Push your code to GitHub.
2. Go to [Render.com](https://render.com) and click **New + ➔ Web Service**.
3. Connect your GitHub repository.
4. Set:
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
5. Click **Deploy Web Service**. Your app will be live on a public URL!

### Alternative Deployment (PythonAnywhere)
1. Sign up on [PythonAnywhere](https://www.pythonanywhere.com/).
2. In the "Web" tab, create a new manual Flask configuration using Python 3.10+.
3. Upload/clone this repository and set the WSGI configuration file to import `app as application`.

---

## 🛠️ Technology Stack
- **Backend**: Python, Flask 3.x, Werkzeug, SQLite3
- **Frontend**: Vanilla JavaScript (ES6+), Semantic HTML5, Custom Responsive Design
- **GIS / Mapping**: Leaflet.js, OpenStreetMap
- **Production Server**: Gunicorn (included in Procfile)
- **Zero Heavy Dependencies**: Completely self-contained without external paid API dependencies.
