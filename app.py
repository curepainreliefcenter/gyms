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
                "email": "rahul@example.com",
                "address": "Andheri West, Mumbai",
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
                "email": "vikas@example.com",
                "source": "Instagram Ad",
                "status": "Trial (3-Day)",
                "follow_up_date": "2026-09-10"
            }
        ],
        "staff": [
            {
                "id": 1, 
                "name": "Amit (Trainer)", 
                "phone": "9876543210", 
                "email": "amit@gym.com",
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
                "date": "2026-09-01"
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
        "message": "Gym Orbitedgemedia PDF reports and quick comms update",
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
                "id": max([m["id"] for m in data["members"]], default=0) + 1,
                "name": request.form.get("name"),
                "phone": request.form.get("phone"),
                "email": request.form.get("email"),
                "address": request.form.get("address"),
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

        elif form_type == "edit_member":
            m_id = int(request.form.get("member_id"))
            for m in data["members"]:
                if m["id"] == m_id:
                    m["name"] = request.form.get("name")
                    m["phone"] = request.form.get("phone")
                    m["email"] = request.form.get("email")
                    m["address"] = request.form.get("address")
                    m["plan"] = request.form.get("plan")
                    m["scheme"] = request.form.get("scheme")
                    m["amount"] = int(request.form.get("amount", 0))
                    m["dues"] = int(request.form.get("dues", 0))
                    m["pt_trainer"] = request.form.get("pt_trainer")
                    m["pt_amount"] = int(request.form.get("pt_amount", 0))
                    m["start_date"] = request.form.get("start_date")
                    m["end_date"] = request.form.get("end_date")
                    m["status"] = request.form.get("status")
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
                        m["email"] = request.form.get("new_holder_email", m["email"])
                        m["address"] = request.form.get("new_holder_address", m["address"])
            save_data(data)
            return redirect(url_for("index", action="members"))

        elif form_type == "add_lead":
            new_lead = {
                "id": max([l["id"] for l in data["leads"]], default=0) + 1,
                "name": request.form.get("name"),
                "phone": request.form.get("phone"),
                "email": request.form.get("email"),
                "source": request.form.get("source"),
                "status": request.form.get("status"),
                "follow_up_date": request.form.get("follow_up_date")
            }
            data["leads"].append(new_lead)
            save_data(data)
            return redirect(url_for("index", action="leads"))

        elif form_type == "edit_lead":
            l_id = int(request.form.get("lead_id"))
            for l in data["leads"]:
                if l["id"] == l_id:
                    l["name"] = request.form.get("name")
                    l["phone"] = request.form.get("phone")
                    l["email"] = request.form.get("email")
                    l["source"] = request.form.get("source")
                    l["status"] = request.form.get("status")
                    l["follow_up_date"] = request.form.get("follow_up_date")
            save_data(data)
            return redirect(url_for("index", action="leads"))

        elif role == "admin":
            if form_type == "add_staff":
                new_staff = {
                    "id": max([s["id"] for s in data["staff"]], default=0) + 1,
                    "name": request.form.get("name"),
                    "phone": request.form.get("phone"),
                    "email": request.form.get("email"),
                    "address": request.form.get("address"),
                    "base_salary": int(request.form.get("base_salary", 0)),
                    "advance": int(request.form.get("advance", 0)),
                    "attendance": request.form.get("attendance", "Present")
                }
                data["staff"].append(new_staff)
                save_data(data)
                return redirect(url_for("index", action="staff"))

            elif form_type == "edit_staff":
                s_id = int(request.form.get("staff_id"))
                for s in data["staff"]:
                    if s["id"] == s_id:
                        s["name"] = request.form.get("name")
                        s["phone"] = request.form.get("phone")
                        s["email"] = request.form.get("email")
                        s["address"] = request.form.get("address")
                        s["base_salary"] = int(request.form.get("base_salary", 0))
                        s["advance"] = int(request.form.get("advance", 0))
                        s["attendance"] = request.form.get("attendance")
                save_data(data)
                return redirect(url_for("index", action="staff"))

            elif form_type == "add_expense":
                new_exp = {
                    "id": max([e["id"] for e in data["expenses"]], default=0) + 1,
                    "category": request.form.get("category"),
                    "amount": int(request.form.get("amount", 0)),
                    "date": request.form.get("date")
                }
                data["expenses"].append(new_exp)
                save_data(data)
                return redirect(url_for("index", action="expenses"))

            elif form_type == "edit_expense":
                e_id = int(request.form.get("expense_id"))
                for e in data["expenses"]:
                    if e["id"] == e_id:
                        e["category"] = request.form.get("category")
                        e["amount"] = int(request.form.get("amount", 0))
                        e["date"] = request.form.get("date")
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
    <title>Gym Orbitedgemedia - Login</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-950 text-white flex items-center justify-center h-screen px-4">
    <div class="bg-gray-900 p-8 rounded-2xl shadow-2xl w-full max-w-md border border-gray-800">
        <h2 class="text-3xl font-black text-center mb-2 text-emerald-400">💪 Gym Orbitedgemedia</h2>
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
    <title>Gym Orbitedgemedia CRM Suite</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        @media print {
            body * {
                visibility: hidden;
            }
            #invoiceModal, #invoiceModal *, .printable-section, .printable-section * {
                visibility: visible;
            }
            .printable-section {
                position: absolute;
                left: 0;
                top: 0;
                width: 100%;
                background: white !important;
                color: black !important;
            }
            .no-print {
                display: none !important;
            }
        }
    </style>
</head>
<body class="bg-gray-950 text-gray-100 font-sans">
    <div class="flex h-screen overflow-hidden">
        <div class="hidden md:flex flex-col w-64 bg-gray-900 border-r border-gray-800 p-6">
            <h1 class="text-xl font-black text-emerald-400 mb-1 tracking-wider">💪 Gym Orbitedgemedia</h1>
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
                <h1 class="text-sm font-black text-emerald-400">💪 Gym Orbitedgemedia</h1>
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
                    <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-gray-900 p-6 rounded-2xl border border-gray-800 shadow-xl">
                        <div>
                            <h2 class="text-2xl font-black text-white">📊 Master Financial Dashboard & P&L</h2>
                            <p class="text-xs text-gray-400 mt-1">Real-time financial performance breakdown for Gym Orbitedgemedia.</p>
                        </div>
                        <button onclick="window.print()" class="px-4 py-2.5 bg-emerald-500 hover:bg-emerald-600 font-bold text-gray-950 rounded-xl transition text-xs shadow-lg cursor-pointer">🖨️ Print Dashboard Report</button>
                    </div>
                    
                    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
                        <div class="bg-gray-900 p-5 rounded-2xl border border-gray-800 shadow-xl relative overflow-hidden">
                            <div class="absolute -right-4 -bottom-4 text-emerald-500/10 text-6xl font-black">₹</div>
                            <p class="text-xs text-gray-400 font-bold">Total Revenue</p>
                            <h3 class="text-2xl font-black text-emerald-400 mt-2">₹{{ total_revenue }}</h3>
                            <span class="text-[10px] text-emerald-500 mt-1 block font-semibold">+ Memberships & PT</span>
                        </div>
                        <div class="bg-gray-900 p-5 rounded-2xl border border-gray-800 shadow-xl relative overflow-hidden">
                            <div class="absolute -right-4 -bottom-4 text-amber-500/10 text-6xl font-black">₹</div>
                            <p class="text-xs text-gray-400 font-bold">Pending Dues</p>
                            <h3 class="text-2xl font-black text-amber-400 mt-2">₹{{ total_dues }}</h3>
                            <span class="text-[10px] text-amber-500 mt-1 block font-semibold">To be collected</span>
                        </div>
                        <div class="bg-gray-900 p-5 rounded-2xl border border-gray-800 shadow-xl relative overflow-hidden">
                            <div class="absolute -right-4 -bottom-4 text-yellow-500/10 text-6xl font-black">₹</div>
                            <p class="text-xs text-gray-400 font-bold">Salary & Advances</p>
                            <h3 class="text-2xl font-black text-yellow-400 mt-2">₹{{ total_salaries + total_advances }}</h3>
                            <span class="text-[10px] text-yellow-500 mt-1 block font-semibold">Staff Payroll Outflow</span>
                        </div>
                        <div class="bg-gray-900 p-5 rounded-2xl border border-gray-800 shadow-xl relative overflow-hidden">
                            <div class="absolute -right-4 -bottom-4 text-red-500/10 text-6xl font-black">₹</div>
                            <p class="text-xs text-gray-400 font-bold">Total Expenses</p>
                            <h3 class="text-2xl font-black text-red-400 mt-2">₹{{ total_expenses }}</h3>
                            <span class="text-[10px] text-red-500 mt-1 block font-semibold">Utilities & Bills</span>
                        </div>
                        <div class="bg-gray-900 p-5 rounded-2xl border border-gray-800 shadow-xl relative overflow-hidden">
                            <div class="absolute -right-4 -bottom-4 text-blue-500/10 text-6xl font-black">₹</div>
                            <p class="text-xs text-gray-400 font-bold">Net Profit (P&L)</p>
                            <h3 class="text-2xl font-black text-blue-400 mt-2">₹{{ net_profit }}</h3>
                            <span class="text-[10px] text-blue-400 mt-1 block font-semibold">Revenue - (Salary+Exp)</span>
                        </div>
                    </div>

                    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        <div class="bg-gray-900 p-6 rounded-2xl border border-gray-800 shadow-xl lg:col-span-2 flex flex-col justify-center">
                            <h3 class="text-lg font-bold text-gray-200 mb-4">💡 Blueprint Business Summary</h3>
                            <ul class="space-y-3 text-sm text-gray-300">
                                <li class="flex justify-between p-3.5 bg-gray-800/40 rounded-xl border border-gray-800"><span>Active Members Registered:</span> <strong class="text-emerald-400 text-base">{{ data.members|length }}</strong></li>
                                <li class="flex justify-between p-3.5 bg-gray-800/40 rounded-xl border border-gray-800"><span>Active Prospects / Leads in Pipeline:</span> <strong class="text-amber-400 text-base">{{ data.leads|length }}</strong></li>
                                <li class="flex justify-between p-3.5 bg-gray-800/40 rounded-xl border border-gray-800"><span>Total Staff & Trainers Active:</span> <strong class="text-yellow-400 text-base">{{ data.staff|length }}</strong></li>
                            </ul>
                        </div>
                        <div class="bg-gray-900 p-6 rounded-2xl border border-gray-800 shadow-xl flex flex-col items-center justify-center">
                            <h3 class="text-sm font-bold text-gray-300 mb-3">Membership Plan Distribution</h3>
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
                                <label class="text-xs text-gray-400">Email Address</label>
                                <input type="email" name="email" placeholder="Optional" class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
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
                                <label class="text-xs text-gray-400">Follow-up Date (Calendar Picker)</label>
                                <input type="date" name="follow_up_date" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                            </div>
                            <div class="sm:col-span-3">
                                <button type="submit" class="w-full py-2.5 bg-emerald-500 hover:bg-emerald-600 font-bold text-gray-950 rounded-xl transition text-sm shadow-lg">Save Lead</button>
                            </div>
                        </form>
                    </div>

                    <div class="bg-gray-900 rounded-2xl border border-gray-800 shadow-xl overflow-hidden printable-section">
                        <div class="p-4 border-b border-gray-800 flex flex-col sm:flex-row justify-between items-center gap-4">
                            <h3 class="font-bold text-gray-200">📋 Leads & Trial Tracking</h3>
                            <div class="flex items-center gap-2 w-full sm:w-auto no-print">
                                <input type="text" id="searchLeads" onkeyup="filterTable('searchLeads', 'leadsTable')" placeholder="🔍 Search prospects..." class="px-4 py-2 bg-gray-800 border border-gray-700 rounded-xl text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-400 w-full sm:w-60">
                                <button type="button" onclick="window.print()" class="px-3.5 py-2 bg-emerald-500 hover:bg-emerald-600 text-gray-950 font-bold rounded-xl text-xs whitespace-nowrap cursor-pointer">📄 Export PDF</button>
                            </div>
                        </div>
                        <div class="overflow-x-auto">
                            <table id="leadsTable" class="w-full text-left border-collapse text-sm">
                                <thead>
                                    <tr class="bg-gray-800/50 text-gray-400">
                                        <th class="p-3">Name</th>
                                        <th class="p-3">Contact Info</th>
                                        <th class="p-3">Source</th>
                                        <th class="p-3">Status</th>
                                        <th class="p-3">Follow-up Date</th>
                                        <th class="p-3 text-center no-print">Quick Actions</th>
                                        <th class="p-3 text-center no-print">Admin Controls</th>
                                    </tr>
                                </thead>
                                <tbody class="divide-y divide-gray-800">
                                    {% for l in data.leads %}
                                    <tr class="hover:bg-gray-800/30">
                                        <td class="p-3 font-semibold text-white">{{ l.name }}</td>
                                        <td class="p-3 text-gray-300">
                                            📱 {{ l.phone }}<br>
                                            <span class="text-xs text-gray-400">📧 {{ l.email or 'N/A' }}</span>
                                        </td>
                                        <td class="p-3 text-emerald-400">{{ l.source }}</td>
                                        <td class="p-3 text-yellow-400">{{ l.status }}</td>
                                        <td class="p-3 text-gray-300">{{ l.follow_up_date }}</td>
                                        <td class="p-3 text-center space-x-1 no-print">
                                            <a href="https://wa.me/91{{ l.phone }}?text=Hello%20{{ l.name }},%20welcome%20to%20Gym%20Orbitedgemedia!" target="_blank" class="text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded text-xs font-bold inline-block">💬 WhatsApp</a>
                                            {% if l.email %}
                                            <a href="mailto:{{ l.email }}?subject=Gym%20Orbitedgemedia%20Trial" class="text-blue-400 bg-blue-500/10 px-2.5 py-1 rounded text-xs font-bold inline-block">📧 Email</a>
                                            {% endif %}
                                        </td>
                                        <td class="p-3 text-center space-x-1 no-print">
                                            <button type="button" onclick='openEditModal("lead", {{ l|tojson|safe }})' class="text-blue-400 bg-blue-500/10 px-2.5 py-1 rounded text-xs font-bold cursor-pointer">Edit</button>
                                            <a href="/delete/lead/{{ l.id }}" onclick="return confirm('Confirm delete lead?');" class="text-red-400 bg-red-500/10 px-2.5 py-1 rounded text-xs font-bold">Delete</a>
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
                        <h2 class="text-xl font-bold text-emerald-400 mb-4">➕ Add Member (Email, Address, Start & Expiry Calendar)</h2>
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
                                <label class="text-xs text-gray-400">Email Address</label>
                                <input type="email" name="email" required placeholder="member@example.com" class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                            </div>
                            <div class="sm:col-span-2">
                                <label class="text-xs text-gray-400">Residential Address</label>
                                <input type="text" name="address" required placeholder="Full street address, area" class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
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
                                <label class="text-xs text-gray-400">Personal Trainer (PT)</label>
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
                                <label class="text-xs text-gray-400">Start Date (Calendar Select)</label>
                                <input type="date" name="start_date" id="add_start_date" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm" onchange="calcExpiry()">
                            </div>
                            <div>
                                <label class="text-xs text-gray-400">End / Expiry Date (Calendar Select)</label>
                                <input type="date" name="end_date" id="add_end_date" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                            </div>
                            <div class="sm:col-span-3">
                                <button type="submit" class="w-full py-3 bg-emerald-500 hover:bg-emerald-600 font-bold text-gray-950 rounded-xl transition text-sm shadow-lg">Save Member Record</button>
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
                                <label class="text-xs text-gray-400">New Holder Name (Transfer)</label>
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

                    <div class="bg-gray-900 rounded-2xl border border-gray-800 shadow-xl overflow-hidden printable-section">
                        <div class="p-4 border-b border-gray-800 flex flex-col sm:flex-row justify-between items-center gap-4">
                            <h3 class="font-bold text-gray-200">👥 Members Directory</h3>
                            <div class="flex items-center gap-2 w-full sm:w-auto no-print">
                                <input type="text" id="searchMembers" onkeyup="filterTable('searchMembers', 'membersTable')" placeholder="🔍 Search members..." class="px-4 py-2 bg-gray-800 border border-gray-700 rounded-xl text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-400 w-full sm:w-60">
                                <button type="button" onclick="window.print()" class="px-3.5 py-2 bg-emerald-500 hover:bg-emerald-600 text-gray-950 font-bold rounded-xl text-xs whitespace-nowrap cursor-pointer">📄 Export PDF</button>
                            </div>
                        </div>
                        <div class="overflow-x-auto">
                            <table id="membersTable" class="w-full text-left border-collapse text-sm">
                                <thead>
                                    <tr class="bg-gray-800/50 text-gray-400">
                                        <th class="p-3">Member Details</th>
                                        <th class="p-3">Contact & Address</th>
                                        <th class="p-3">Plan / Scheme</th>
                                        <th class="p-3">Fee / Dues</th>
                                        <th class="p-3">Start & Expiry Dates</th>
                                        <th class="p-3">Status</th>
                                        <th class="p-3 text-center no-print">Quick Comms</th>
                                        <th class="p-3 text-center no-print">Actions / Invoice</th>
                                    </tr>
                                </thead>
                                <tbody class="divide-y divide-gray-800">
                                    {% for m in data.members %}
                                    <tr class="hover:bg-gray-800/30">
                                        <td class="p-3 font-semibold text-white">
                                            {{ m.name }}
                                            {% if m.pt_trainer != 'None' %}
                                            <br><span class="text-xs text-blue-400">PT: {{ m.pt_trainer }}</span>
                                            {% endif %}
                                        </td>
                                        <td class="p-3 text-gray-300 text-xs">
                                            📱 {{ m.phone }}<br>
                                            📧 {{ m.email or 'N/A' }}<br>
                                            🏠 {{ m.address or 'N/A' }}
                                        </td>
                                        <td class="p-3 text-emerald-400">{{ m.plan }} <br><span class="text-xs text-yellow-400">({{ m.scheme }})</span></td>
                                        <td class="p-3 text-gray-200">
                                            Paid: ₹{{ m.amount }}<br>
                                            <span class="text-amber-400 font-bold">Dues: ₹{{ m.dues }}</span>
                                        </td>
                                        <td class="p-3 text-xs text-gray-300">
                                            🟢 Starts: {{ m.start_date }}<br>
                                            🔴 Expires: {{ m.end_date }}
                                        </td>
                                        <td class="p-3"><span class="px-2 py-1 rounded text-xs {% if m.status == 'Active' %}bg-emerald-500/10 text-emerald-400{% else %}bg-amber-500/10 text-amber-400{% endif %}">{{ m.status }}</span></td>
                                        <td class="p-3 text-center space-x-1 no-print">
                                            <a href="https://wa.me/91{{ m.phone }}?text=Hello%20{{ m.name }},%20reminder%20from%20Gym%20Orbitedgemedia!" target="_blank" class="text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded text-xs font-bold inline-block">💬 WhatsApp</a>
                                            {% if m.email %}
                                            <a href="mailto:{{ m.email }}?subject=Gym%20Orbitedgemedia%20Membership" class="text-blue-400 bg-blue-500/10 px-2 py-1 rounded text-xs font-bold inline-block">📧 Email</a>
                                            {% endif %}
                                        </td>
                                        <td class="p-3 text-center space-x-1 no-print">
                                            <button type="button" onclick='openInvoiceModal({{ m|tojson|safe }})' class="text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded text-xs font-bold cursor-pointer">Invoice</button>
                                            <button type="button" onclick='openEditModal("member", {{ m|tojson|safe }})' class="text-blue-400 bg-blue-500/10 px-2 py-1 rounded text-xs font-bold cursor-pointer">Edit</button>
                                            {% if role == 'admin' %}
                                            <a href="/delete/member/{{ m.id }}" onclick="return confirm('Confirm delete member?');" class="text-red-400 bg-red-500/10 px-2 py-1 rounded text-xs font-bold">Delete</a>
                                            {% endif %}
                                        </td>
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
                                <label class="text-xs text-gray-400">Staff Name</label>
                                <input type="text" name="name" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm" placeholder="Trainer/Staff Name">
                            </div>
                            <div>
                                <label class="text-xs text-gray-400">Mobile Number</label>
                                <input type="text" name="phone" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm" placeholder="Staff Mobile">
                            </div>
                            <div>
                                <label class="text-xs text-gray-400">Email Address</label>
                                <input type="email" name="email" placeholder="staff@example.com" class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                            </div>
                            <div class="sm:col-span-2">
                                <label class="text-xs text-gray-400">Residential Address</label>
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

                    <div class="bg-gray-900 rounded-2xl border border-gray-800 shadow-xl overflow-hidden printable-section">
                        <div class="p-4 border-b border-gray-800 flex flex-col sm:flex-row justify-between items-center gap-4">
                            <h3 class="font-bold text-gray-200">📋 Staff Payroll Ledger</h3>
                            <div class="flex items-center gap-2 w-full sm:w-auto no-print">
                                <input type="text" id="searchStaff" onkeyup="filterTable('searchStaff', 'staffTable')" placeholder="🔍 Search staff..." class="px-4 py-2 bg-gray-800 border border-gray-700 rounded-xl text-sm text-white focus:outline-none focus:ring-2 focus:ring-yellow-400 w-full sm:w-60">
                                <button type="button" onclick="window.print()" class="px-3.5 py-2 bg-yellow-500 hover:bg-yellow-600 text-gray-950 font-bold rounded-xl text-xs whitespace-nowrap cursor-pointer">📄 Export PDF</button>
                            </div>
                        </div>
                        <div class="overflow-x-auto">
                            <table id="staffTable" class="w-full text-left border-collapse text-sm">
                                <thead>
                                    <tr class="bg-gray-800/50 text-gray-400">
                                        <th class="p-3">Staff Name</th>
                                        <th class="p-3">Contact & Address</th>
                                        <th class="p-3">Base Salary</th>
                                        <th class="p-3">Advance (Minus)</th>
                                        <th class="p-3">Net Pay</th>
                                        <th class="p-3">Attendance</th>
                                        <th class="p-3 text-center no-print">Quick Comms</th>
                                        <th class="p-3 text-center no-print">Actions</th>
                                    </tr>
                                </thead>
                                <tbody class="divide-y divide-gray-800">
                                    {% for s in data.staff %}
                                    <tr class="hover:bg-gray-800/30">
                                        <td class="p-3 font-semibold text-white">{{ s.name }}</td>
                                        <td class="p-3 text-gray-300 text-xs">
                                            📱 {{ s.phone }}<br>
                                            📧 {{ s.email or 'N/A' }}<br>
                                            🏠 {{ s.address }}
                                        </td>
                                        <td class="p-3 text-gray-200">₹{{ s.base_salary }}</td>
                                        <td class="p-3 text-red-400">₹{{ s.advance }}</td>
                                        <td class="p-3 text-emerald-400 font-bold">₹{{ s.base_salary - s.advance }}</td>
                                        <td class="p-3 text-yellow-300">{{ s.attendance }}</td>
                                        <td class="p-3 text-center space-x-1 no-print">
                                            <a href="https://wa.me/91{{ s.phone }}?text=Hello%20{{ s.name }},%20message%20from%20Gym%20Orbitedgemedia!" target="_blank" class="text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded text-xs font-bold inline-block">💬 WhatsApp</a>
                                            {% if s.email %}
                                            <a href="mailto:{{ s.email }}?subject=Gym%20Orbitedgemedia%20Staff" class="text-blue-400 bg-blue-500/10 px-2 py-1 rounded text-xs font-bold inline-block">📧 Email</a>
                                            {% endif %}
                                        </td>
                                        <td class="p-3 text-center space-x-1 no-print">
                                            <button type="button" onclick='openEditModal("staff", {{ s|tojson|safe }})' class="text-blue-400 bg-blue-500/10 px-2.5 py-1 rounded text-xs font-bold cursor-pointer">Edit</button>
                                            <a href="/delete/staff/{{ s.id }}" onclick="return confirm('Confirm delete staff?');" class="text-red-400 bg-red-500/10 px-2.5 py-1 rounded text-xs font-bold">Delete</a>
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
                                <label class="text-xs text-gray-400">Category / Title</label>
                                <input type="text" name="category" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm" placeholder="Electricity / Maintenance">
                            </div>
                            <div>
                                <label class="text-xs text-gray-400">Amount (₹)</label>
                                <input type="number" name="amount" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                            </div>
                            <div>
                                <label class="text-xs text-gray-400">Date (Calendar Select)</label>
                                <input type="date" name="date" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                            </div>
                            <div class="sm:col-span-3">
                                <button type="submit" class="w-full py-3 bg-red-500 hover:bg-red-600 font-bold text-gray-950 rounded-xl transition text-sm shadow-lg">Save Expense</button>
                            </div>
                        </form>
                    </div>

                    <div class="bg-gray-900 rounded-2xl border border-gray-800 shadow-xl overflow-hidden printable-section">
                        <div class="p-4 border-b border-gray-800 flex flex-col sm:flex-row justify-between items-center gap-4">
                            <h3 class="font-bold text-gray-200">📉 Expenses Ledger</h3>
                            <div class="flex items-center gap-2 w-full sm:w-auto no-print">
                                <input type="text" id="searchExpenses" onkeyup="filterTable('searchExpenses', 'expensesTable')" placeholder="🔍 Search expenses..." class="px-4 py-2 bg-gray-800 border border-gray-700 rounded-xl text-sm text-white focus:outline-none focus:ring-2 focus:ring-red-400 w-full sm:w-60">
                                <button type="button" onclick="window.print()" class="px-3.5 py-2 bg-red-500 hover:bg-red-600 text-gray-950 font-bold rounded-xl text-xs whitespace-nowrap cursor-pointer">📄 Export PDF</button>
                            </div>
                        </div>
                        <div class="overflow-x-auto">
                            <table id="expensesTable" class="w-full text-left border-collapse text-sm">
                                <thead>
                                    <tr class="bg-gray-800/50 text-gray-400">
                                        <th class="p-3">Description</th>
                                        <th class="p-3">Date</th>
                                        <th class="p-3">Amount</th>
                                        <th class="p-3 text-center no-print">Actions</th>
                                    </tr>
                                </thead>
                                <tbody class="divide-y divide-gray-800">
                                    {% for e in data.expenses %}
                                    <tr class="hover:bg-gray-800/30">
                                        <td class="p-3 font-semibold text-white">{{ e.category }}</td>
                                        <td class="p-3 text-gray-300">{{ e.date }}</td>
                                        <td class="p-3 text-red-400 font-bold">₹{{ e.amount }}</td>
                                        <td class="p-3 text-center space-x-2 no-print">
                                            <button type="button" onclick='openEditModal("expense", {{ e|tojson|safe }})' class="text-blue-400 bg-blue-500/10 px-2.5 py-1 rounded text-xs font-bold cursor-pointer">Edit</button>
                                            <a href="/delete/expense/{{ e.id }}" onclick="return confirm('Confirm delete expense?');" class="text-red-400 bg-red-500/10 px-2.5 py-1 rounded text-xs font-bold">Delete</a>
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

    <!-- UNIVERSAL EDIT MODAL -->
    <div id="editModal" class="fixed inset-0 bg-black/70 hidden items-center justify-center p-4 z-50">
        <div class="bg-gray-900 border border-gray-800 rounded-2xl w-full max-w-xl p-6 shadow-2xl relative max-h-[90vh] overflow-y-auto">
            <button type="button" onclick="closeEditModal()" class="absolute top-4 right-4 text-gray-400 hover:text-white font-bold text-lg cursor-pointer">✕</button>
            <h3 id="modalTitle" class="text-xl font-bold text-emerald-400 mb-4">Edit Entry</h3>
            <form id="editForm" method="POST" class="space-y-4">
                <input type="hidden" name="form_type" id="editFormType">
                <input type="hidden" name="" id="editRecordIdVal" value="">
                <div id="modalBodyFields" class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <!-- Injected dynamically via JS -->
                </div>
                <button type="submit" class="w-full py-3 bg-emerald-500 hover:bg-emerald-600 text-gray-950 font-bold rounded-xl shadow-lg transition text-sm cursor-pointer">Save Changes</button>
            </form>
        </div>
    </div>

    <!-- INVOICE PREVIEW MODAL -->
    <div id="invoiceModal" class="fixed inset-0 bg-black/80 hidden items-center justify-center p-4 z-50">
        <div class="bg-white text-gray-900 rounded-2xl w-full max-w-2xl p-8 shadow-2xl relative max-h-[95vh] overflow-y-auto">
            <button type="button" onclick="closeInvoiceModal()" class="absolute top-4 right-4 text-gray-500 hover:text-gray-900 font-bold text-lg no-print cursor-pointer">✕</button>
            
            <div class="text-center border-b pb-4 mb-6">
                <h2 class="text-2xl font-black text-emerald-600">Gym Orbitedgemedia</h2>
                <p class="text-xs text-gray-500">Official Membership Fee Receipt & Tax Invoice</p>
            </div>

            <div class="grid grid-cols-2 gap-4 mb-6 text-sm">
                <div>
                    <p class="text-xs text-gray-500 font-bold">INVOICE TO:</p>
                    <p id="invName" class="font-bold text-gray-950 text-base"></p>
                    <p id="invPhone" class="text-xs text-gray-600"></p>
                    <p id="invEmail" class="text-xs text-gray-600"></p>
                    <p id="invAddress" class="text-xs text-gray-600"></p>
                </div>
                <div class="text-right">
                    <p class="text-xs text-gray-500 font-bold">INVOICE DETAILS:</p>
                    <p class="text-xs text-gray-600">Invoice No: <span class="font-bold">GO-2026-001</span></p>
                    <p class="text-xs text-gray-600">Date Issued: <span id="invIssuedDate" class="font-bold"></span></p>
                    <p class="text-xs text-gray-600">Status: <span class="font-bold text-emerald-600">PAID</span></p>
                </div>
            </div>

            <table class="w-full text-left border-collapse mb-6 text-sm">
                <thead>
                    <tr class="bg-gray-100 text-gray-700 border-b">
                        <th class="p-2.5">Description / Plan</th>
                        <th class="p-2.5">Scheme</th>
                        <th class="p-2.5 text-right">Amount</th>
                    </tr>
                </thead>
                <tbody class="divide-y text-gray-800">
                    <tr>
                        <td class="p-2.5"><span id="invPlan"></span><br><span class="text-xs text-gray-500">Start: <span id="invStart"></span> | Expiry: <span id="invEnd"></span></span></td>
                        <td id="invScheme" class="p-2.5 text-xs"></td>
                        <td id="invAmount" class="p-2.5 text-right font-semibold"></td>
                    </tr>
                    <tr id="ptRow">
                        <td class="p-2.5"><span class="text-xs text-blue-600 font-bold">Personal Trainer Fees:</span> <span id="invPtTrainer"></span></td>
                        <td class="p-2.5 text-xs">PT Package</td>
                        <td id="invPtAmount" class="p-2.5 text-right font-semibold"></td>
                    </tr>
                    <tr>
                        <td colspan="2" class="p-2.5 font-bold text-right">Pending Dues:</td>
                        <td id="invDues" class="p-2.5 text-right font-bold text-amber-600"></td>
                    </tr>
                </tbody>
            </table>

            <div class="flex justify-between items-center border-t pt-4 mb-8">
                <span class="font-bold text-gray-700">Total Paid Amount:</span>
                <span id="invTotalPaid" class="text-2xl font-black text-emerald-600"></span>
            </div>

            <div class="text-center text-[10px] text-gray-400 border-t pt-4 mb-6">
                <p>Thank you for choosing Gym Orbitedgemedia! Stay fit, stay healthy.</p>
                <p>This is a computer-generated invoice document.</p>
            </div>

            <div class="flex space-x-4 no-print">
                <button type="button" onclick="window.print()" class="flex-1 py-3 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl shadow-lg transition text-sm text-center cursor-pointer">Download / Print PDF</button>
                <button type="button" onclick="closeInvoiceModal()" class="px-6 py-3 bg-gray-200 hover:bg-gray-300 text-gray-800 font-bold rounded-xl transition text-sm cursor-pointer">Close</button>
            </div>
        </div>
    </div>

    <script>
        window.addEventListener('DOMContentLoaded', () => {
            const startDateEl = document.getElementById('add_start_date');
            if(startDateEl && !startDateEl.value) {
                const today = new Date().toISOString().split('T')[0];
                startDateEl.value = today;
                calcExpiry();
            }
        });

        function calcExpiry() {
            const startInput = document.getElementById('add_start_date');
            const endInput = document.getElementById('add_end_date');
            if(startInput && endInput && startInput.value) {
                let d = new Date(startInput.value);
                d.setFullYear(d.getFullYear() + 1);
                endInput.value = d.toISOString().split('T')[0];
            }
        }

        function filterTable(inputId, tableId) {
            const input = document.getElementById(inputId);
            const filter = input.value.toLowerCase();
            const table = document.getElementById(tableId);
            const trs = table.getElementsByTagName('tr');
            
            for (let i = 1; i < trs.length; i++) {
                let visible = false;
                const tds = trs[i].getElementsByTagName('td');
                for (let j = 0; j < tds.length; j++) {
                    if (tds[j]) {
                        if (tds[j].innerText.toLowerCase().indexOf(filter) > -1) {
                            visible = true;
                            break;
                        }
                    }
                }
                trs[i].style.display = visible ? '' : 'none';
            }
        }

        function openInvoiceModal(m) {
            document.getElementById('invName').innerText = m.name;
            document.getElementById('invPhone').innerText = 'Phone: ' + m.phone;
            document.getElementById('invEmail').innerText = 'Email: ' + (m.email || 'N/A');
            document.getElementById('invAddress').innerText = 'Address: ' + (m.address || 'N/A');
            document.getElementById('invIssuedDate').innerText = new Date().toISOString().split('T')[0];
            document.getElementById('invPlan').innerText = m.plan;
            document.getElementById('invScheme').innerText = m.scheme;
            document.getElementById('invAmount').innerText = '₹' + m.amount;
            document.getElementById('invStart').innerText = m.start_date;
            document.getElementById('invEnd').innerText = m.end_date;
            document.getElementById('invDues').innerText = '₹' + m.dues;
            
            const ptRow = document.getElementById('ptRow');
            if (m.pt_trainer && m.pt_trainer !== 'None') {
                ptRow.style.display = 'table-row';
                document.getElementById('invPtTrainer').innerText = '(' + m.pt_trainer + ')';
                document.getElementById('invPtAmount').innerText = '₹' + m.pt_amount;
                document.getElementById('invTotalPaid').innerText = '₹' + (m.amount + m.pt_amount);
            } else {
                ptRow.style.display = 'none';
                document.getElementById('invTotalPaid').innerText = '₹' + m.amount;
            }

            const modal = document.getElementById('invoiceModal');
            modal.classList.remove('hidden');
            modal.classList.add('flex');
        }

        function closeInvoiceModal() {
            const modal = document.getElementById('invoiceModal');
            modal.classList.remove('flex');
            modal.classList.add('hidden');
        }

        function openEditModal(type, item) {
            const modal = document.getElementById('editModal');
            const title = document.getElementById('modalTitle');
            const formType = document.getElementById('editFormType');
            const idValInput = document.getElementById('editRecordIdVal');
            const fieldsContainer = document.getElementById('modalBodyFields');
            
            fieldsContainer.innerHTML = '';
            modal.classList.remove('hidden');
            modal.classList.add('flex');

            if (type === 'member') {
                title.innerText = 'Edit Member Record';
                formType.value = 'edit_member';
                idValInput.name = 'member_id';
                idValInput.value = item.id;

                fieldsContainer.innerHTML = `
                    <div><label class="text-xs text-gray-400">Full Name</label><input type="text" name="name" value="${item.name}" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm"></div>
                    <div><label class="text-xs text-gray-400">Mobile</label><input type="text" name="phone" value="${item.phone}" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm"></div>
                    <div><label class="text-xs text-gray-400">Email</label><input type="email" name="email" value="${item.email || ''}" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm"></div>
                    <div><label class="text-xs text-gray-400">Address</label><input type="text" name="address" value="${item.address || ''}" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm"></div>
                    <div><label class="text-xs text-gray-400">Plan</label><input type="text" name="plan" value="${item.plan}" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm"></div>
                    <div><label class="text-xs text-gray-400">Scheme</label><input type="text" name="scheme" value="${item.scheme}" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm"></div>
                    <div><label class="text-xs text-gray-400">Fee Paid (₹)</label><input type="number" name="amount" value="${item.amount}" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm"></div>
                    <div><label class="text-xs text-gray-400">Dues (₹)</label><input type="number" name="dues" value="${item.dues}" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm"></div>
                    <div><label class="text-xs text-gray-400">PT Trainer</label><input type="text" name="pt_trainer" value="${item.pt_trainer}" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm"></div>
                    <div><label class="text-xs text-gray-400">PT Amount (₹)</label><input type="number" name="pt_amount" value="${item.pt_amount}" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm"></div>
                    <div><label class="text-xs text-gray-400">Start Date</label><input type="date" name="start_date" value="${item.start_date}" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm"></div>
                    <div><label class="text-xs text-gray-400">End Date</label><input type="date" name="end_date" value="${item.end_date}" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm"></div>
                    <div class="sm:col-span-2"><label class="text-xs text-gray-400">Status</label><select name="status" class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm"><option value="Active" ${item.status=='Active'?'selected':''}>Active</option><option value="Frozen" ${item.status=='Frozen'?'selected':''}>Frozen</option></select></div>
                `;
            } else if (type === 'lead') {
                title.innerText = 'Edit Lead Record';
                formType.value = 'edit_lead';
                idValInput.name = 'lead_id';
                idValInput.value = item.id;

                fieldsContainer.innerHTML = `
                    <div><label class="text-xs text-gray-400">Name</label><input type="text" name="name" value="${item.name}" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm"></div>
                    <div><label class="text-xs text-gray-400">Phone</label><input type="text" name="phone" value="${item.phone}" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm"></div>
                    <div><label class="text-xs text-gray-400">Email</label><input type="email" name="email" value="${item.email || ''}" class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm"></div>
                    <div><label class="text-xs text-gray-400">Source</label><input type="text" name="source" value="${item.source}" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm"></div>
                    <div><label class="text-xs text-gray-400">Status</label><input type="text" name="status" value="${item.status}" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm"></div>
                    <div><label class="text-xs text-gray-400">Follow-up Date</label><input type="date" name="follow_up_date" value="${item.follow_up_date}" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm"></div>
                `;
            } else if (type === 'staff') {
                title.innerText = 'Edit Staff Record';
                formType.value = 'edit_staff';
                idValInput.name = 'staff_id';
                idValInput.value = item.id;

                fieldsContainer.innerHTML = `
                    <div><label class="text-xs text-gray-400">Name</label><input type="text" name="name" value="${item.name}" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm"></div>
                    <div><label class="text-xs text-gray-400">Phone</label><input type="text" name="phone" value="${item.phone}" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm"></div>
                    <div><label class="text-xs text-gray-400">Email</label><input type="email" name="email" value="${item.email || ''}" class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm"></div>
                    <div><label class="text-xs text-gray-400">Address</label><input type="text" name="address" value="${item.address}" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm"></div>
                    <div><label class="text-xs text-gray-400">Base Salary (₹)</label><input type="number" name="base_salary" value="${item.base_salary}" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm"></div>
                    <div><label class="text-xs text-gray-400">Advance (₹)</label><input type="number" name="advance" value="${item.advance}" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm"></div>
                    <div class="sm:col-span-2"><label class="text-xs text-gray-400">Attendance</label><input type="text" name="attendance" value="${item.attendance}" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm"></div>
                `;
            } else if (type === 'expense') {
                title.innerText = 'Edit Expense Record';
                formType.value = 'edit_expense';
                idValInput.name = 'expense_id';
                idValInput.value = item.id;

                fieldsContainer.innerHTML = `
                    <div><label class="text-xs text-gray-400">Category</label><input type="text" name="category" value="${item.category}" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm"></div>
                    <div><label class="text-xs text-gray-400">Amount (₹)</label><input type="number" name="amount" value="${item.amount}" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm"></div>
                    <div class="sm:col-span-2"><label class="text-xs text-gray-400">Date</label><input type="date" name="date" value="${item.date}" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm"></div>
                `;
            }
        }

        function closeEditModal() {
            const modal = document.getElementById('editModal');
            modal.classList.remove('flex');
            modal.classList.add('hidden');
        }
    </script>

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
