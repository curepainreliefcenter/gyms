from flask import Flask, render_template_string, request, redirect, url_for, session
import json
import os
import base64
import requests
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "gymos_secure_master_key_2026"

# GitHub API Configurations
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO")
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main")
FILE_PATH = "gymos_data.json"

def load_data():
    default_data = {
        "members": [
            {
                "id": 1, 
                "name": "Rahul Sharma", 
                "phone": "9876543210", 
                "plan": "Gold (12 Months)", 
                "scheme": "12+1 Free", 
                "amount": 15000, 
                "dues": 2000,
                "pt_trainer": "Amit (Trainer)", 
                "pt_amount": 5000, 
                "status": "Active",
                "start_date": "2026-01-01",
                "end_date": "2027-01-01"
            }
        ],
        "leads": [
            {
                "id": 1,
                "name": "Vikas Verma",
                "phone": "9123456789",
                "source": "Instagram Ad",
                "status": "Trial (3-Day)",
                "follow_up_date": "2026-06-10"
            }
        ],
        "staff": [
            {
                "id": 1, 
                "name": "Amit (Trainer)", 
                "phone": "9876543210", 
                "address": "Main Street, Gym Area", 
                "base_salary": 15000, 
                "advance": 3000,
                "attendance": "Present"
            }
        ],
        "expenses": [
            {
                "id": 1, 
                "category": "Electricity Bill", 
                "amount": 4500, 
                "date": "2026-06-01"
            }
        ]
    }
    
    if not GITHUB_TOKEN or not GITHUB_REPO:
        if not os.path.exists(FILE_PATH):
            with open(FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(default_data, f, indent=4, ensure_ascii=False)
        try:
            with open(FILE_PATH, "r", encoding="utf-8") as f:
                d = json.load(f)
                # Ensure all required keys exist to prevent KeyErrors
                for key in default_data:
                    if key not in d:
                        d[key] = default_data[key]
                return d
        except:
            return default_data

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "vnd.github+json"}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        try:
            file_content = response.json().get("content")
            decoded_content = base64.b64decode(file_content).decode("utf-8")
            d = json.loads(decoded_content)
            for key in default_data:
                if key not in d:
                    d[key] = default_data[key]
            return d
        except:
            return default_data
    else:
        save_data(default_data)
        return default_data

def save_data(data):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        with open(FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "vnd.github+json"}
    
    get_res = requests.get(url, headers=headers)
    sha = get_res.json().get("sha") if get_res.status_code == 200 else None

    json_str = json.dumps(data, indent=4, ensure_ascii=False)
    encoded_content = base64.b64encode(json_str.encode("utf-8")).decode("utf-8")

    payload = {
        "message": "Auto-sync gymos blueprint upgrade update",
        "content": encoded_content,
        "branch": GITHUB_BRANCH
    }
    if sha:
        payload["sha"] = sha

    requests.put(url, headers=headers, json=payload)

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        if username == "admin" and password == "admin123":
            session["user"] = username
            session["role"] = "admin"
            return redirect(url_for("index"))
        elif username == "staff" and password == "staff123":
            session["user"] = username
            session["role"] = "employee"
            return redirect(url_for("index", action="members"))
        else:
            error = "Invalid credentials! Use admin/admin123 or staff/staff123"
            
    return render_template_string(LOGIN_HTML, error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/", methods=["GET", "POST"])
def index():
    if "user" not in session:
        return redirect(url_for("login"))
    
    role = session.get("role", "employee")
    data = load_data()
    
    # Ensure keys exist safely
    data.setdefault("members", [])
    data.setdefault("leads", [])
    data.setdefault("staff", [])
    data.setdefault("expenses", [])

    default_action = "members" if role == "employee" else "dashboard"
    action = request.args.get("action", default_action)
    
    if role == "employee" and action in ["dashboard", "staff", "expenses", "leads"]:
        action = "members"

    if request.method == "POST":
        form_type = request.form.get("form_type")
        
        if form_type == "add_member":
            new_member = {
                "id": len(data["members"]) + 1,
                "name": request.form.get("name"),
                "phone": request.form.get("phone"),
                "plan": request.form.get("plan"),
                "scheme": request.form.get("scheme", "Standard"),
                "amount": int(request.form.get("amount", 0)),
                "dues": int(request.form.get("dues", 0)),
                "pt_trainer": request.form.get("pt_trainer", "None"),
                "pt_amount": int(request.form.get("pt_amount", 0)),
                "status": "Active",
                "start_date": request.form.get("start_date", str(datetime.now().date())),
                "end_date": request.form.get("end_date", str(datetime.now().date() + timedelta(days=365)))
            }
            data["members"].append(new_member)
            save_data(data)
            return redirect(url_for("index", action="members"))

        elif form_type == "lifecycle_update":
            m_id = int(request.form.get("member_id"))
            action_type = request.form.get("lifecycle_action")
            for m in data["members"]:
                if m["id"] == m_id:
                    if action_type == "freeze":
                        m["status"] = "Frozen"
                    elif action_type == "activate":
                        m["status"] = "Active"
                    elif action_type == "transfer":
                        m["name"] = request.form.get("new_holder_name")
                        m["phone"] = request.form.get("new_holder_phone")
            save_data(data)
            return redirect(url_for("index", action="members"))

        elif form_type == "add_lead":
            new_lead = {
                "id": len(data["leads"]) + 1,
                "name": request.form.get("name"),
                "phone": request.form.get("phone"),
                "source": request.form.get("source"),
                "status": request.form.get("status"),
                "follow_up_date": request.form.get("follow_up_date")
            }
            data["leads"].append(new_lead)
            save_data(data)
            return redirect(url_for("index", action="leads"))

        elif role == "admin":
            if form_type == "add_staff":
                new_staff = {
                    "id": len(data["staff"]) + 1,
                    "name": request.form.get("name"),
                    "phone": request.form.get("phone"),
                    "address": request.form.get("address"),
                    "base_salary": int(request.form.get("base_salary", 0)),
                    "advance": int(request.form.get("advance", 0)),
                    "attendance": request.form.get("attendance", "Present")
                }
                data["staff"].append(new_staff)
                save_data(data)
                return redirect(url_for("index", action="staff"))

            elif form_type == "add_expense":
                new_exp = {
                    "id": len(data["expenses"]) + 1,
                    "category": request.form.get("category"),
                    "amount": int(request.form.get("amount", 0)),
                    "date": request.form.get("date")
                }
                data["expenses"].append(new_exp)
                save_data(data)
                return redirect(url_for("index", action="expenses"))

    total_revenue = sum(m.get("amount", 0) + m.get("pt_amount", 0) for m in data["members"])
    total_dues = sum(m.get("dues", 0) for m in data["members"])
    total_salaries = sum(s.get("base_salary", 0) for s in data["staff"])
    total_advances = sum(s.get("advance", 0) for s in data["staff"])
    total_expenses = sum(e.get("amount", 0) for e in data["expenses"])
    net_profit = total_revenue - (total_salaries + total_expenses)

    plans_count = {}
    for m in data["members"]:
        p = m.get("plan", "Standard")
        plans_count[p] = plans_count.get(p, 0) + 1

    plan_labels = list(plans_count.keys())
    plan_values = list(plans_count.values())

    return render_template_string(
        DASHBOARD_HTML, 
        data=data, 
        action=action, 
        role=role,
        sources_status="GitHub API Synced" if GITHUB_TOKEN else "Local JSON Mode",
        total_revenue=total_revenue,
        total_dues=total_dues,
        total_salaries=total_salaries,
        total_advances=total_advances,
        total_expenses=total_expenses,
        net_profit=net_profit,
        plan_labels=plan_labels,
        plan_values=plan_values
    )

@app.route("/delete/<string:category>/<int:item_id>")
def delete_item(category, item_id):
    if "user" not in session or session.get("role") != "admin":
        return redirect(url_for("index", action="members"))

    data = load_data()
    data.setdefault("members", [])
    data.setdefault("leads", [])
    data.setdefault("staff", [])
    data.setdefault("expenses", [])

    if category == "member":
        data["members"] = [m for m in data["members"] if m["id"] != item_id]
        redirect_action = "members"
    elif category == "lead":
        data["leads"] = [l for l in data["leads"] if l["id"] != item_id]
        redirect_action = "leads"
    elif category == "staff":
        data["staff"] = [s for s in data["staff"] if s["id"] != item_id]
        redirect_action = "staff"
    elif category == "expense":
        data["expenses"] = [e for e in data["expenses"] if e["id"] != item_id]
        redirect_action = "expenses"
    
    save_data(data)
    return redirect(url_for("index", action=redirect_action))

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GymOS - Login</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-950 text-white flex items-center justify-center h-screen px-4">
    <div class="bg-gray-900 p-8 rounded-2xl shadow-2xl w-full max-w-md border border-gray-800">
        <h2 class="text-3xl font-black text-center mb-2 text-emerald-400">💪 GymOS CRM</h2>
        <p class="text-xs text-gray-400 text-center mb-6">Complete Blueprint Management System</p>
        
        {% if error %}
            <div class="bg-red-500/20 border border-red-500 text-red-300 p-3 rounded-xl mb-4 text-xs text-center">{{ error }}</div>
        {% endif %}
        
        <form method="POST" class="space-y-4">
            <div>
                <label class="block text-xs text-gray-400 mb-1">Username</label>
                <input type="text" name="username" required placeholder="admin or staff" class="w-full px-4 py-2.5 bg-gray-800 rounded-xl border border-gray-700 focus:outline-none focus:ring-2 focus:ring-emerald-400 text-sm">
            </div>
            <div>
                <label class="block text-xs text-gray-400 mb-1">Password</label>
                <input type="password" name="password" required placeholder="password" class="w-full px-4 py-2.5 bg-gray-800 rounded-xl border border-gray-700 focus:outline-none focus:ring-2 focus:ring-emerald-400 text-sm">
            </div>
            <button type="submit" class="w-full py-3 bg-emerald-500 hover:bg-emerald-600 transition rounded-xl font-bold text-gray-950 shadow-lg text-sm mt-2">Log In</button>
        </form>

        <div class="mt-6 p-4 bg-gray-800/50 rounded-xl border border-gray-800 text-xs space-y-1 text-gray-400">
            <p><strong class="text-emerald-400">👑 Admin:</strong> admin / admin123</p>
            <p><strong class="text-yellow-400">👔 Staff:</strong> staff / staff123</p>
        </div>
    </div>
</body>
</html>
"""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GymOS CRM Suite</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body class="bg-gray-950 text-gray-100 font-sans">
    <div class="flex h-screen overflow-hidden">
        <div class="hidden md:flex flex-col w-64 bg-gray-900 border-r border-gray-800 p-6">
            <h1 class="text-2xl font-black text-emerald-400 mb-1 tracking-wider">💪 GymOS</h1>
            <p class="text-xs text-gray-400 mb-6 capitalize">Role: <span class="text-emerald-400 font-bold">{{ role }}</span></p>
            <div class="mb-6 px-3 py-1.5 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-[10px] text-emerald-400 font-mono text-center">
                🟢 {{ sources_status }}
            </div>
            
            <nav class="space-y-2 flex-1">
                {% if role == 'admin' %}
                <a href="/?action=dashboard" class="block py-2.5 px-4 rounded-xl font-semibold transition {% if action == 'dashboard' %}bg-emerald-500/10 text-emerald-400{% else %}text-gray-400 hover:bg-gray-800{% endif %}">📊 P&L Dashboard</a>
                <a href="/?action=leads" class="block py-2.5 px-4 rounded-xl font-semibold transition {% if action == 'leads' %}bg-emerald-500/10 text-emerald-400{% else %}text-gray-400 hover:bg-gray-800{% endif %}">🎯 Prospect & Leads</a>
                {% endif %}
                <a href="/?action=members" class="block py-2.5 px-4 rounded-xl font-semibold transition {% if action == 'members' %}bg-emerald-500/10 text-emerald-400{% else %}text-gray-400 hover:bg-gray-800{% endif %}">👥 Members & Lifecycle</a>
                {% if role == 'admin' %}
                <a href="/?action=staff" class="block py-2.5 px-4 rounded-xl font-semibold transition {% if action == 'staff' %}bg-emerald-500/10 text-emerald-400{% else %}text-gray-400 hover:bg-gray-800{% endif %}">👔 Staff Payroll & Attn</a>
                <a href="/?action=expenses" class="block py-2.5 px-4 rounded-xl font-semibold transition {% if action == 'expenses' %}bg-emerald-500/10 text-emerald-400{% else %}text-gray-400 hover:bg-gray-800{% endif %}">💡 Expenses Ledger</a>
                {% endif %}
                <a href="/logout" class="block py-2.5 px-4 rounded-xl font-semibold text-red-400 hover:bg-red-500/10 transition mt-8">🚪 Log Out</a>
            </nav>
        </div>

        <div class="flex-1 flex flex-col overflow-y-auto">
            <header class="bg-gray-900 border-b border-gray-800 p-4 flex justify-between items-center md:hidden">
                <h1 class="text-lg font-black text-emerald-400">💪 GymOS <span class="text-[10px] text-emerald-300 font-mono">({{ sources_status }})</span></h1>
                <a href="/logout" class="text-xs text-red-400 font-bold bg-red-500/10 px-3 py-1.5 rounded-lg">Log Out</a>
            </header>

            <div class="flex md:hidden bg-gray-900 p-2 overflow-x-auto space-x-2 border-b border-gray-800 shrink-0">
                {% if role == 'admin' %}
                <a href="/?action=dashboard" class="px-3 py-1.5 text-xs font-semibold rounded-lg {% if action == 'dashboard' %}bg-emerald-500 text-gray-950{% else %}bg-gray-800 text-gray-300{% endif %} whitespace-nowrap">Dashboard</a>
                <a href="/?action=leads" class="px-3 py-1.5 text-xs font-semibold rounded-lg {% if action == 'leads' %}bg-emerald-500 text-gray-950{% else %}bg-gray-800 text-gray-300{% endif %} whitespace-nowrap">Leads</a>
                {% endif %}
                <a href="/?action=members" class="px-3 py-1.5 text-xs font-semibold rounded-lg {% if action == 'members' %}bg-emerald-500 text-gray-950{% else %}bg-gray-800 text-gray-300{% endif %} whitespace-nowrap">Members</a>
                {% if role == 'admin' %}
                <a href="/?action=staff" class="px-3 py-1.5 text-xs font-semibold rounded-lg {% if action == 'staff' %}bg-emerald-500 text-gray-950{% else %}bg-gray-800 text-gray-300{% endif %} whitespace-nowrap">Staff</a>
                <a href="/?action=expenses" class="px-3 py-1.5 text-xs font-semibold rounded-lg {% if action == 'expenses' %}bg-emerald-500 text-gray-950{% else %}bg-gray-800 text-gray-300{% endif %} whitespace-nowrap">Expenses</a>
                {% endif %}
            </div>

            <div class="p-4 sm:p-6 max-w-7xl mx-auto w-full space-y-6">
                
                {% if action == 'dashboard' and role == 'admin' %}
                <div class="space-y-6">
                    <h2 class="text-2xl font-black text-white">📊 Master Financial Dashboard & P&L</h2>
                    
                    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
                        <div class="bg-gray-900 p-5 rounded-2xl border border-gray-800 shadow-xl">
                            <p class="text-xs text-gray-400 font-bold">Total Revenue</p>
                            <h3 class="text-xl font-black text-emerald-400 mt-1">₹{{ total_revenue }}</h3>
                        </div>
                        <div class="bg-gray-900 p-5 rounded-2xl border border-gray-800 shadow-xl">
                            <p class="text-xs text-gray-400 font-bold">Pending Dues</p>
                            <h3 class="text-xl font-black text-amber-400 mt-1">₹{{ total_dues }}</h3>
                        </div>
                        <div class="bg-gray-900 p-5 rounded-2xl border border-gray-800 shadow-xl">
                            <p class="text-xs text-gray-400 font-bold">Salary & Advances</p>
                            <h3 class="text-xl font-black text-yellow-400 mt-1">₹{{ total_salaries + total_advances }}</h3>
                        </div>
                        <div class="bg-gray-900 p-5 rounded-2xl border border-gray-800 shadow-xl">
                            <p class="text-xs text-gray-400 font-bold">Total Expenses</p>
                            <h3 class="text-xl font-black text-red-400 mt-1">₹{{ total_expenses }}</h3>
                        </div>
                        <div class="bg-gray-900 p-5 rounded-2xl border border-gray-800 shadow-xl">
                            <p class="text-xs text-gray-400 font-bold">Net Profit (P&L)</p>
                            <h3 class="text-xl font-black text-blue-400 mt-1">₹{{ net_profit }}</h3>
                        </div>
                    </div>

                    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        <div class="bg-gray-900 p-6 rounded-2xl border border-gray-800 shadow-xl lg:col-span-2 flex flex-col justify-center">
                            <h3 class="text-lg font-bold text-gray-200 mb-4">💡 Blueprint Business Insights</h3>
                            <ul class="space-y-3 text-sm text-gray-300">
                                <li class="flex justify-between p-3 bg-gray-800/40 rounded-xl"><span>Active Members:</span> <strong class="text-emerald-400">{{ data.members|length }}</strong></li>
                                <li class="flex justify-between p-3 bg-gray-800/40 rounded-xl"><span>Active Prospects / Leads:</span> <strong class="text-amber-400">{{ data.leads|length }}</strong></li>
                                <li class="flex justify-between p-3 bg-gray-800/40 rounded-xl"><span>Total Staff Registered:</span> <strong class="text-yellow-400">{{ data.staff|length }}</strong></li>
                            </ul>
                        </div>
                        <div class="bg-gray-900 p-6 rounded-2xl border border-gray-800 shadow-xl flex flex-col items-center justify-center">
                            <h3 class="text-sm font-bold text-gray-300 mb-3">Membership Breakdown</h3>
                            <div class="w-48 h-48">
                                <canvas id="planChart"></canvas>
                            </div>
                        </div>
                    </div>
                </div>

                {% elif action == 'leads' and role == 'admin' %}
                <div class="space-y-6">
                    <div class="bg-gray-900 p-6 rounded-2xl border border-gray-800 shadow-xl">
                        <h2 class="text-xl font-bold text-emerald-400 mb-4">🎯 Prospect & Lead Management</h2>
                        <form method="POST" class="grid grid-cols-1 sm:grid-cols-3 gap-4">
                            <input type="hidden" name="form_type" value="add_lead">
                            <div>
                                <label class="text-xs text-gray-400">Prospect Name</label>
                                <input type="text" name="name" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                            </div>
                            <div>
                                <label class="text-xs text-gray-400">Mobile Number</label>
                                <input type="text" name="phone" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                            </div>
                            <div>
                                <label class="text-xs text-gray-400">Marketing Source</label>
                                <select name="source" class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                                    <option value="Walk-In">Walk-In</option>
                                    <option value="Instagram Ad">Instagram Ad</option>
                                    <option value="Facebook Ad">Facebook Ad</option>
                                    <option value="Direct Call">Direct Call</option>
                                </select>
                            </div>
                            <div>
                                <label class="text-xs text-gray-400">Lead Status</label>
                                <select name="status" class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                                    <option value="Trial (3-Day)">Trial (3-Day)</option>
                                    <option value="Trial (7-Day)">Trial (7-Day)</option>
                                    <option value="Follow-Up Pending">Follow-Up Pending</option>
                                    <option value="Converted">Converted</option>
                                </select>
                            </div>
                            <div>
                                <label class="text-xs text-gray-400">Follow-up Date</label>
                                <input type="date" name="follow_up_date" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                            </div>
                            <div class="sm:flex items-end">
                                <button type="submit" class="w-full py-2.5 bg-emerald-500 hover:bg-emerald-600 font-bold text-gray-950 rounded-xl transition text-sm shadow-lg">Save Lead</button>
                            </div>
                        </form>
                    </div>

                    <div class="bg-gray-900 rounded-2xl border border-gray-800 shadow-xl overflow-hidden">
                        <div class="p-4 border-b border-gray-800"><h3 class="font-bold text-gray-200">📋 Leads & Trial Tracking</h3></div>
                        <div class="overflow-x-auto">
                            <table class="w-full text-left border-collapse text-sm">
                                <thead>
                                    <tr class="bg-gray-800/50 text-gray-400">
                                        <th class="p-3">Name</th>
                                        <th class="p-3">Phone</th>
                                        <th class="p-3">Source</th>
                                        <th class="p-3">Status</th>
                                        <th class="p-3">Follow-up Date</th>
                                        <th class="p-3 text-center">Action</th>
                                    </tr>
                                </thead>
                                <tbody class="divide-y divide-gray-800">
                                    {% for l in data.leads %}
                                    <tr class="hover:bg-gray-800/30">
                                        <td class="p-3 font-semibold text-white">{{ l.name }}</td>
                                        <td class="p-3 text-gray-300">{{ l.phone }}</td>
                                        <td class="p-3 text-emerald-400">{{ l.source }}</td>
                                        <td class="p-3 text-yellow-400">{{ l.status }}</td>
                                        <td class="p-3 text-gray-300">{{ l.follow_up_date }}</td>
                                        <td class="p-3 text-center">
                                            <a href="/delete/lead/{{ l.id }}" class="text-red-400 bg-red-500/10 px-2.5 py-1 rounded text-xs font-bold">Delete</a>
                                        </td>
                                    </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
                
                {% elif action == 'members' %}
                <div class="space-y-6">
                    <div class="bg-gray-900 p-6 rounded-2xl border border-gray-800 shadow-xl">
                        <h2 class="text-xl font-bold text-emerald-400 mb-4">➕ Add Member & Schemes (12+1 / PT & Dues)</h2>
                        <form method="POST" class="grid grid-cols-1 sm:grid-cols-3 gap-4">
                            <input type="hidden" name="form_type" value="add_member">
                            <div>
                                <label class="text-xs text-gray-400">Full Name</label>
                                <input type="text" name="name" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                            </div>
                            <div>
                                <label class="text-xs text-gray-400">Mobile Number</label>
                                <input type="text" name="phone" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                            </div>
                            <div>
                                <label class="text-xs text-gray-400">Membership Plan</label>
                                <select name="plan" class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                                    <option value="Gold (12 Months)">Gold (12 Months)</option>
                                    <option value="Silver (6 Months)">Silver (6 Months)</option>
                                    <option value="Bronze (3 Months)">Bronze (3 Months)</option>
                                    <option value="Monthly Pass">Monthly Pass</option>
                                </select>
                            </div>
                            <div>
                                <label class="text-xs text-gray-400">Special Scheme</label>
                                <select name="scheme" class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                                    <option value="Standard">Standard</option>
                                    <option value="12+1 Free">12+1 Free Scheme</option>
                                    <option value="6+1 Free">6+1 Free Scheme</option>
                                    <option value="3+1 Free">3+1 Free Scheme</option>
                                </select>
                            </div>
                            <div>
                                <label class="text-xs text-gray-400">Paid Fee (₹)</label>
                                <input type="number" name="amount" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                            </div>
                            <div>
                                <label class="text-xs text-gray-400">Pending Dues (₹)</label>
                                <input type="number" name="dues" value="0" class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                            </div>
                            <div>
                                <label class="text-xs text-gray-400">Personal Trainer (PT) - Interlinked</label>
                                <select name="pt_trainer" class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                                    <option value="None">None</option>
                                    {% for s in data.staff %}
                                    <option value="{{ s.name }}">{{ s.name }}</option>
                                    {% endfor %}
                                </select>
                            </div>
                            <div>
                                <label class="text-xs text-gray-400">PT Amount (₹)</label>
                                <input type="number" name="pt_amount" value="0" class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                            </div>
                            <div>
                                <label class="text-xs text-gray-400">Start Date</label>
                                <input type="date" name="start_date" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                            </div>
                            <div class="sm:col-span-3">
                                <button type="submit" class="w-full py-3 bg-emerald-500 hover:bg-emerald-600 font-bold text-gray-950 rounded-xl transition text-sm shadow-lg">Save Member Record & POS Receipt</button>
                            </div>
                        </form>
                    </div>

                    <div class="bg-gray-900 p-6 rounded-2xl border border-gray-800 shadow-xl">
                        <h2 class="text-xl font-bold text-blue-400 mb-4">🔄 Membership Lifecycle (Freeze / Transfer)</h2>
                        <form method="POST" class="grid grid-cols-1 sm:grid-cols-4 gap-4">
                            <input type="hidden" name="form_type" value="lifecycle_update">
                            <div>
                                <label class="text-xs text-gray-400">Select Member</label>
                                <select name="member_id" class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                                    {% for m in data.members %}
                                    <option value="{{ m.id }}">{{ m.name }} ({{ m.status }})</option>
                                    {% endfor %}
                                </select>
                            </div>
                            <div>
                                <label class="text-xs text-gray-400">Action Type</label>
                                <select name="lifecycle_action" class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                                    <option value="freeze">Freeze Membership</option>
                                    <option value="activate">Activate / Unfreeze</option>
                                    <option value="transfer">Transfer Ownership</option>
                                </select>
                            </div>
                            <div>
                                <label class="text-xs text-gray-400">New Holder Name (If Transfer)</label>
                                <input type="text" name="new_holder_name" placeholder="Optional" class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                            </div>
                            <div>
                                <label class="text-xs text-gray-400">New Holder Phone</label>
                                <input type="text" name="new_holder_phone" placeholder="Optional" class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                            </div>
                            <div class="sm:col-span-4">
                                <button type="submit" class="w-full py-2.5 bg-blue-500 hover:bg-blue-600 font-bold text-gray-950 rounded-xl transition text-sm shadow-lg">Apply Lifecycle Update</button>
                            </div>
                        </form>
                    </div>

                    <div class="bg-gray-900 rounded-2xl border border-gray-800 shadow-xl overflow-hidden">
                        <div class="p-4 border-b border-gray-800"><h3 class="font-bold text-gray-200">👥 Members List</h3></div>
                        <div class="overflow-x-auto">
                            <table class="w-full text-left border-collapse text-sm">
                                <thead>
                                    <tr class="bg-gray-800/50 text-gray-400">
                                        <th class="p-3">Name</th>
                                        <th class="p-3">Mobile</th>
                                        <th class="p-3">Plan / Scheme</th>
                                        <th class="p-3">Fee Paid</th>
                                        <th class="p-3">Dues</th>
                                        <th class="p-3">PT Trainer</th>
                                        <th class="p-3">Status</th>
                                        {% if role == 'admin' %}
                                        <th class="p-3 text-center">Action</th>
                                        {% endif %}
                                    </tr>
                                </thead>
                                <tbody class="divide-y divide-gray-800">
                                    {% for m in data.members %}
                                    <tr class="hover:bg-gray-800/30">
                                        <td class="p-3 font-semibold text-white">{{ m.name }}</td>
                                        <td class="p-3 text-gray-300">{{ m.phone }}</td>
                                        <td class="p-3 text-emerald-400">{{ m.plan }} <br><span class="text-xs text-yellow-400">({{ m.scheme }})</span></td>
                                        <td class="p-3 text-gray-200">₹{{ m.amount }}</td>
                                        <td class="p-3 text-amber-400 font-bold">₹{{ m.dues }}</td>
                                        <td class="p-3 text-blue-300">{{ m.pt_trainer }} <br><span class="text-xs text-gray-400">(₹{{ m.pt_amount }})</span></td>
                                        <td class="p-3"><span class="px-2 py-1 rounded text-xs {% if m.status == 'Active' %}bg-emerald-500/10 text-emerald-400{% else %}bg-amber-500/10 text-amber-400{% endif %}">{{ m.status }}</span></td>
                                        {% if role == 'admin' %}
                                        <td class="p-3 text-center">
                                            <a href="/delete/member/{{ m.id }}" onclick="return confirm('Confirm delete?');" class="text-red-400 bg-red-500/10 px-2.5 py-1 rounded text-xs font-bold">Delete</a>
                                        </td>
                                        {% endif %}
                                    </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                {% elif action == 'staff' and role == 'admin' %}
                <div class="space-y-6">
                    <div class="bg-gray-900 p-6 rounded-2xl border border-gray-800 shadow-xl">
                        <h2 class="text-xl font-bold text-yellow-400 mb-4">👔 Staff Payroll, Attendance & Auto-Deduction</h2>
                        <form method="POST" class="grid grid-cols-1 sm:grid-cols-3 gap-4">
                            <input type="hidden" name="form_type" value="add_staff">
                            <div>
                                <label class="text-xs text-gray-400">Staff Name & Role</label>
                                <input type="text" name="name" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm" placeholder="Trainer/Staff Name">
                            </div>
                            <div>
                                <label class="text-xs text-gray-400">Mobile Number</label>
                                <input type="text" name="phone" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm" placeholder="Staff Mobile">
                            </div>
                            <div>
                                <label class="text-xs text-gray-400">Address</label>
                                <input type="text" name="address" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm" placeholder="Staff Address">
                            </div>
                            <div>
                                <label class="text-xs text-gray-400">Base Salary (₹)</label>
                                <input type="number" name="base_salary" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                            </div>
                            <div>
                                <label class="text-xs text-gray-400">Advance Taken (Auto-Deducted) (₹)</label>
                                <input type="number" name="advance" value="0" class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                            </div>
                            <div>
                                <label class="text-xs text-gray-400">Attendance Status</label>
                                <select name="attendance" class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                                    <option value="Present">Present / Active</option>
                                    <option value="On Leave">On Leave</option>
                                </select>
                            </div>
                            <div class="sm:col-span-3">
                                <button type="submit" class="w-full py-3 bg-yellow-500 hover:bg-yellow-600 font-bold text-gray-950 rounded-xl transition text-sm shadow-lg">Save Staff Record</button>
                            </div>
                        </form>
                    </div>

                    <div class="bg-gray-900 rounded-2xl border border-gray-800 shadow-xl overflow-hidden">
                        <div class="p-4 border-b border-gray-800"><h3 class="font-bold text-gray-200">📋 Staff Payroll Ledger</h3></div>
                        <div class="overflow-x-auto">
                            <table class="w-full text-left border-collapse text-sm">
                                <thead>
                                    <tr class="bg-gray-800/50 text-gray-400">
                                        <th class="p-3">Staff Name</th>
                                        <th class="p-3">Mobile</th>
                                        <th class="p-3">Address</th>
                                        <th class="p-3">Base Salary</th>
                                        <th class="p-3">Advance (Minus)</th>
                                        <th class="p-3">Net Pay</th>
                                        <th class="p-3">Attendance</th>
                                        <th class="p-3 text-center">Action</th>
                                    </tr>
                                </thead>
                                <tbody class="divide-y divide-gray-800">
                                    {% for s in data.staff %}
                                    <tr class="hover:bg-gray-800/30">
                                        <td class="p-3 font-semibold text-white">{{ s.name }}</td>
                                        <td class="p-3 text-gray-300">{{ s.phone }}</td>
                                        <td class="p-3 text-gray-300">{{ s.address }}</td>
                                        <td class="p-3 text-gray-200">₹{{ s.base_salary }}</td>
                                        <td class="p-3 text-red-400">₹{{ s.advance }}</td>
                                        <td class="p-3 text-emerald-400 font-bold">₹{{ s.base_salary - s.advance }}</td>
                                        <td class="p-3 text-yellow-300">{{ s.attendance }}</td>
                                        <td class="p-3 text-center">
                                            <a href="/delete/staff/{{ s.id }}" class="text-red-400 bg-red-500/10 px-2.5 py-1 rounded text-xs font-bold">Delete</a>
                                        </td>
                                    </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                {% elif action == 'expenses' and role == 'admin' %}
                <div class="space-y-6">
                    <div class="bg-gray-900 p-6 rounded-2xl border border-gray-800 shadow-xl">
                        <h2 class="text-xl font-bold text-red-400 mb-4">💡 Utilities & Gym Expenses Ledger</h2>
                        <form method="POST" class="grid grid-cols-1 sm:grid-cols-3 gap-4">
                            <input type="hidden" name="form_type" value="add_expense">
                            <div>
                                <label class="text-xs text-gray-400">Category</label>
                                <input type="text" name="category" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm" placeholder="Electricity / Maintenance">
                            </div>
                            <div>
                                <label class="text-xs text-gray-400">Amount (₹)</label>
                                <input type="number" name="amount" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                            </div>
                            <div>
                                <label class="text-xs text-gray-400">Date</label>
                                <input type="date" name="date" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                            </div>
                            <div class="sm:col-span-3">
                                <button type="submit" class="w-full py-3 bg-red-500 hover:bg-red-600 font-bold text-gray-950 rounded-xl transition text-sm shadow-lg">Save Expense</button>
                            </div>
                        </form>
                    </div>

                    <div class="bg-gray-900 rounded-2xl border border-gray-800 shadow-xl overflow-hidden">
                        <div class="p-4 border-b border-gray-800"><h3 class="font-bold text-gray-200">📉 Expenses Ledger</h3></div>
                        <div class="overflow-x-auto">
                            <table class="w-full text-left border-collapse text-sm">
                                <thead>
                                    <tr class="bg-gray-800/50 text-gray-400">
                                        <th class="p-3">Description</th>
                                        <th class="p-3">Date</th>
                                        <th class="p-3">Amount</th>
                                        <th class="p-3 text-center">Action</th>
                                    </tr>
                                </thead>
                                <tbody class="divide-y divide-gray-800">
                                    {% for e in data.expenses %}
                                    <tr class="hover:bg-gray-800/30">
                                        <td class="p-3 font-semibold text-white">{{ e.category }}</td>
                                        <td class="p-3 text-gray-300">{{ e.date }}</td>
                                        <td class="p-3 text-red-400 font-bold">₹{{ e.amount }}</td>
                                        <td class="p-3 text-center">
                                            <a href="/delete/expense/{{ e.id }}" class="text-red-400 bg-red-500/10 px-2.5 py-1 rounded text-xs font-bold">Delete</a>
                                        </td>
                                    </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
                {% endif %}

            </div>
        </div>
    </div>

    {% if action == 'dashboard' and role == 'admin' %}
    <script>
        const ctx = document.getElementById('planChart').getContext('2d');
        new Chart(ctx, {
            type: 'pie',
            data: {
                labels: {{ plan_labels | tojson }},
                datasets: [{
                    data: {{ plan_values | tojson }},
                    backgroundColor: ['#10B981', '#3B82F6', '#F59E0B', '#EF4444'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom', labels: { color: '#9CA3AF', boxWidth: 10, font: {size: 10} } }
                }
            }
        });
    </script>
    {% endif %}
</body>
</html>
"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
