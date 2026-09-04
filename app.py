from flask import Flask, render_template_string, request, redirect, url_for, session
import json
import os
import base64
import requests

app = Flask(__name__)
app.secret_key = "gymos_secure_role_based_key_777"

# GitHub API Configurations
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO") # Format: username/repo-name
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main")
FILE_PATH = "gymos_data.json"

def load_data():
    if not GITHUB_TOKEN or not GITHUB_REPO:
        if not os.path.exists(FILE_PATH):
            default_data = {
                "members": [{"id": 1, "name": "Rahul Sharma", "phone": "9876543210", "plan": "Gold (12 Months)", "scheme": "12+1 Free", "amount": 15000, "pt_trainer": "Amit", "pt_amount": 5000, "status": "Active"}],
                "staff": [{"id": 1, "name": "Amit (Trainer)", "base_salary": 15000, "advance": 3000}],
                "expenses": [{"id": 1, "category": "Electricity Bill", "amount": 4500, "date": "2026-06-01"}]
            }
            save_data(default_data)
        with open(FILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "vnd.github+json"}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        file_content = response.json().get("content")
        decoded_content = base64.b64decode(file_content).decode("utf-8")
        return json.loads(decoded_content)
    else:
        return {"members": [], "staff": [], "expenses": []}

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
        "message": "Role-based action update gym data",
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
        
        # Admin Role
        if username == "admin" and password == "admin123":
            session["user"] = username
            session["role"] = "admin"
            return redirect(url_for("index"))
        # Employee Role
        elif username == "staff" and password == "staff123":
            session["user"] = username
            session["role"] = "employee"
            return redirect(url_for("index", action="members"))
        else:
            error = "Invalid username or password! (Admin: admin/admin123 or Staff: staff/staff123)"
            
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
    
    # Redirect employee to members page if they try to access restricted pages
    default_action = "members" if role == "employee" else "dashboard"
    action = request.args.get("action", default_action)
    
    if role == "employee" and action in ["dashboard", "staff", "expenses"]:
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
                "pt_trainer": request.form.get("pt_trainer", "None"),
                "pt_amount": int(request.form.get("pt_amount", 0)),
                "status": "Active"
            }
            data["members"].append(new_member)
            save_data(data)
            return redirect(url_for("index", action="members"))

        # Only Admin can add staff or expenses
        elif role == "admin":
            if form_type == "add_staff":
                new_staff = {
                    "id": len(data["staff"]) + 1,
                    "name": request.form.get("name"),
                    "base_salary": int(request.form.get("base_salary", 0)),
                    "advance": int(request.form.get("advance", 0))
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

    total_revenue = sum(m["amount"] + m["pt_amount"] for m in data["members"])
    total_salaries = sum(s["base_salary"] for s in data["staff"])
    total_advances = sum(s["advance"] for s in data["staff"])
    total_expenses = sum(e["amount"] for e in data["expenses"])
    net_profit = total_revenue - (total_salaries + total_expenses)

    plans_count = {}
    for m in data["members"]:
        p = m["plan"]
        plans_count[p] = plans_count.get(p, 0) + 1

    return render_template_string(
        DASHBOARD_HTML, 
        data=data, 
        action=action, 
        role=role,
        total_revenue=total_revenue,
        total_salaries=total_salaries,
        total_advances=total_advances,
        total_expenses=total_expenses,
        net_profit=net_profit,
        plans_count=plans_count
    )

@app.route("/delete/<string:category>/<int:item_id>")
def delete_item(category, item_id):
    if "user" not in session:
        return redirect(url_for("login"))
    
    # Security check: Only admin can delete data
    if session.get("role") != "admin":
        return redirect(url_for("index", action="members"))

    data = load_data()
    if category == "member":
        data["members"] = [m for m in data["members"] if m["id"] != item_id]
        redirect_action = "members"
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
        <p class="text-xs text-gray-400 text-center mb-6">Gym Management & Role-Based Access System</p>
        
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
            <p><strong class="text-emerald-400">👑 Admin Login:</strong> admin / admin123</p>
            <p><strong class="text-yellow-400">👔 Staff Login:</strong> staff / staff123</p>
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
    <title>GymOS - Gym Management Suite</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body class="bg-gray-950 text-gray-100 font-sans">
    <div class="flex h-screen overflow-hidden">
        <!-- Sidebar -->
        <div class="hidden md:flex flex-col w-64 bg-gray-900 border-r border-gray-800 p-6">
            <h1 class="text-2xl font-black text-emerald-400 mb-2 tracking-wider">💪 GymOS CRM</h1>
            <p class="text-xs text-gray-400 mb-8 capitalize">role: <span class="text-emerald-400 font-bold">{{ role }}</span></p>
            
            <nav class="space-y-2 flex-1">
                {% if role == 'admin' %}
                <a href="/?action=dashboard" class="block py-2.5 px-4 rounded-xl font-semibold transition {% if action == 'dashboard' %}bg-emerald-500/10 text-emerald-400{% else %}text-gray-400 hover:bg-gray-800{% endif %}">📊 Financial Dashboard</a>
                {% endif %}
                
                <a href="/?action=members" class="block py-2.5 px-4 rounded-xl font-semibold transition {% if action == 'members' %}bg-emerald-500/10 text-emerald-400{% else %}text-gray-400 hover:bg-gray-800{% endif %}">👥 Membership & Schemes</a>
                
                {% if role == 'admin' %}
                <a href="/?action=staff" class="block py-2.5 px-4 rounded-xl font-semibold transition {% if action == 'staff' %}bg-emerald-500/10 text-emerald-400{% else %}text-gray-400 hover:bg-gray-800{% endif %}">👔 Staff & Advance Salary</a>
                <a href="/?action=expenses" class="block py-2.5 px-4 rounded-xl font-semibold transition {% if action == 'expenses' %}bg-emerald-500/10 text-emerald-400{% else %}text-gray-400 hover:bg-gray-800{% endif %}">💡 Utilities & Expenses</a>
                {% endif %}
                
                <a href="/logout" class="block py-2.5 px-4 rounded-xl font-semibold text-red-400 hover:bg-red-500/10 transition mt-8">🚪 Log Out</a>
            </nav>
        </div>

        <!-- Main Workspace -->
        <div class="flex-1 flex flex-col overflow-y-auto">
            <!-- Mobile Header -->
            <header class="bg-gray-900 border-b border-gray-800 p-4 flex justify-between items-center md:hidden">
                <h1 class="text-xl font-bold text-emerald-400">GymOS <span class="text-xs text-gray-400">({{ role }})</span></h1>
                <a href="/logout" class="text-xs text-red-400 font-bold">Log Out</a>
            </header>

            <div class="flex md:hidden bg-gray-900/50 p-2 overflow-x-auto space-x-2 border-b border-gray-800">
                {% if role == 'admin' %}
                <a href="/?action=dashboard" class="px-3 py-1 text-xs rounded bg-gray-800 text-emerald-400 whitespace-nowrap">Dashboard</a>
                {% endif %}
                <a href="/?action=members" class="px-3 py-1 text-xs rounded bg-gray-800 text-gray-300 whitespace-nowrap">Members</a>
                {% if role == 'admin' %}
                <a href="/?action=staff" class="px-3 py-1 text-xs rounded bg-gray-800 text-gray-300 whitespace-nowrap">Staff</a>
                <a href="/?action=expenses" class="px-3 py-1 text-xs rounded bg-gray-800 text-gray-300 whitespace-nowrap">Expenses</a>
                {% endif %}
            </div>

            <div class="p-6 max-w-7xl mx-auto w-full space-y-6">
                
                <!-- VIEW 1: ADMIN DASHBOARD -->
                {% if action == 'dashboard' and role == 'admin' %}
                <div class="space-y-6">
                    <h2 class="text-2xl font-black text-white">📊 Master Financial Dashboard & P&L</h2>
                    
                    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                        <div class="bg-gray-900 p-5 rounded-2xl border border-gray-800 shadow-xl">
                            <p class="text-xs text-gray-400 font-bold">Total Revenue (Membership + PT)</p>
                            <h3 class="text-2xl font-black text-emerald-400 mt-1">₹{{ total_revenue }}</h3>
                        </div>
                        <div class="bg-gray-900 p-5 rounded-2xl border border-gray-800 shadow-xl">
                            <p class="text-xs text-gray-400 font-bold">Total Staff Salary & Advance</p>
                            <h3 class="text-2xl font-black text-yellow-400 mt-1">₹{{ total_salaries + total_advances }}</h3>
                        </div>
                        <div class="bg-gray-900 p-5 rounded-2xl border border-gray-800 shadow-xl">
                            <p class="text-xs text-gray-400 font-bold">Utilities & Other Expenses</p>
                            <h3 class="text-2xl font-black text-red-400 mt-1">₹{{ total_expenses }}</h3>
                        </div>
                        <div class="bg-gray-900 p-5 rounded-2xl border border-gray-800 shadow-xl">
                            <p class="text-xs text-gray-400 font-bold">Net Profit (P&L)</p>
                            <h3 class="text-2xl font-black text-blue-400 mt-1">₹{{ net_profit }}</h3>
                        </div>
                    </div>

                    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        <div class="bg-gray-900 p-6 rounded-2xl border border-gray-800 shadow-xl lg:col-span-2 flex flex-col justify-center">
                            <h3 class="text-lg font-bold text-gray-200 mb-4">💡 Business Insights</h3>
                            <ul class="space-y-3 text-sm text-gray-300">
                                <li class="flex justify-between p-3 bg-gray-800/40 rounded-xl"><span>Active Gym Members:</span> <strong class="text-emerald-400">{{ data.members|length }}</strong></li>
                                <li class="flex justify-between p-3 bg-gray-800/40 rounded-xl"><span>Staff Count:</span> <strong class="text-yellow-400">{{ data.staff|length }}</strong></li>
                                <li class="flex justify-between p-3 bg-gray-800/40 rounded-xl"><span>Total Advance Salaries Distributed:</span> <strong class="text-red-400">₹{{ total_advances }}</strong></li>
                            </ul>
                        </div>
                        <div class="bg-gray-900 p-6 rounded-2xl border border-gray-800 shadow-xl flex flex-col items-center justify-center">
                            <h3 class="text-sm font-bold text-gray-300 mb-2">Plan Distribution</h3>
                            <div class="w-44 h-44">
                                <canvas id="planChart"></canvas>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- VIEW 2: MEMBERS & SCHEMES -->
                {% elif action == 'members' %}
                <div class="space-y-6">
                    <div class="bg-gray-900 p-6 rounded-2xl border border-gray-800 shadow-xl">
                        <h2 class="text-xl font-bold text-emerald-400 mb-4">➕ Add New Member & Special Offer (12+1 / PT)</h2>
                        <form method="POST" class="grid grid-cols-1 sm:grid-cols-3 gap-4">
                            <input type="hidden" name="form_type" value="add_member">
                            <div>
                                <label class="text-xs text-gray-400">Full Name</label>
                                <input type="text" name="name" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                            </div>
                            <div>
                                <label class="text-xs text-gray-400">Mobile Number (WhatsApp)</label>
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
                                <label class="text-xs text-gray-400">Special Offer Scheme</label>
                                <select name="scheme" class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                                    <option value="Standard">Standard (No Bonus)</option>
                                    <option value="12+1 Free Scheme">12+1 Free Scheme</option>
                                    <option value="6+1 Free Scheme">6+1 Free Scheme</option>
                                    <option value="3+1 Free Scheme">3+1 Free Scheme</option>
                                </select>
                            </div>
                            <div>
                                <label class="text-xs text-gray-400">Membership Fee (₹)</label>
                                <input type="number" name="amount" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                            </div>
                            <div>
                                <label class="text-xs text-gray-400">Personal Trainer (PT)</label>
                                <select name="pt_trainer" class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                                    <option value="None">None</option>
                                    <option value="Amit">Amit</option>
                                    <option value="Rohit">Rohit</option>
                                </select>
                            </div>
                            <div>
                                <label class="text-xs text-gray-400">PT Package Fee (₹)</label>
                                <input type="number" name="pt_amount" value="0" class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                            </div>
                            <div class="sm:col-span-3">
                                <button type="submit" class="w-full py-3 bg-emerald-500 hover:bg-emerald-600 font-bold text-gray-950 rounded-xl transition text-sm shadow-lg">Save Member & Scheme</button>
                            </div>
                        </form>
                    </div>

                    <div class="bg-gray-900 rounded-2xl border border-gray-800 shadow-xl overflow-hidden">
                        <div class="p-4 border-b border-gray-800"><h3 class="font-bold text-gray-200">👥 All Gym Members List</h3></div>
                        <div class="overflow-x-auto">
                            <table class="w-full text-left border-collapse text-sm">
                                <thead>
                                    <tr class="bg-gray-800/50 text-gray-400">
                                        <th class="p-3">Name</th>
                                        <th class="p-3">Mobile</th>
                                        <th class="p-3">Plan / Scheme</th>
                                        <th class="p-3">Fee</th>
                                        <th class="p-3">PT Trainer & Fee</th>
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
                                        <td class="p-3 text-blue-300">{{ m.pt_trainer }} <br><span class="text-xs text-gray-400">(₹{{ m.pt_amount }})</span></td>
                                        {% if role == 'admin' %}
                                        <td class="p-3 text-center">
                                            <a href="/delete/member/{{ m.id }}" onclick="return confirm('Delete detail?');" class="text-red-400 bg-red-500/10 px-2.5 py-1 rounded text-xs font-bold">Delete</a>
                                        </td>
                                        {% endif %}
                                    </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <!-- VIEW 3: STAFF & PAYROLL (Admin Only) -->
                {% elif action == 'staff' and role == 'admin' %}
                <div class="space-y-6">
                    <div class="bg-gray-900 p-6 rounded-2xl border border-gray-800 shadow-xl">
                        <h2 class="text-xl font-bold text-yellow-400 mb-4">👔 Staff & Advance Salary Management</h2>
                        <form method="POST" class="grid grid-cols-1 sm:grid-cols-3 gap-4">
                            <input type="hidden" name="form_type" value="add_staff">
                            <div>
                                <label class="text-xs text-gray-400">Staff Name & Designation</label>
                                <input type="text" name="name" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm" placeholder="e.g. Suresh (Trainer)">
                            </div>
                            <div>
                                <label class="text-xs text-gray-400">Base Salary (₹)</label>
                                <input type="number" name="base_salary" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                            </div>
                            <div>
                                <label class="text-xs text-gray-400">Advance Salary Taken (₹)</label>
                                <input type="number" name="advance" value="0" class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm">
                            </div>
                            <div class="sm:col-span-3">
                                <button type="submit" class="w-full py-3 bg-yellow-500 hover:bg-yellow-600 font-bold text-gray-950 rounded-lg transition text-sm shadow-lg">Save Staff Record</button>
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
                                        <th class="p-3">Base Salary</th>
                                        <th class="p-3">Advance Deduction</th>
                                        <th class="p-3">Net Pay</th>
                                        <th class="p-3 text-center">Action</th>
                                    </tr>
                                </thead>
                                <tbody class="divide-y divide-gray-800">
                                    {% for s in data.staff %}
                                    <tr class="hover:bg-gray-800/30">
                                        <td class="p-3 font-semibold text-white">{{ s.name }}</td>
                                        <td class="p-3 text-gray-300">₹{{ s.base_salary }}</td>
                                        <td class="p-3 text-red-400">₹{{ s.advance }}</td>
                                        <td class="p-3 text-emerald-400 font-bold">₹{{ s.base_salary - s.advance }}</td>
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

                <!-- VIEW 4: EXPENSES & UTILITIES (Admin Only) -->
                {% elif action == 'expenses' and role == 'admin' %}
                <div class="space-y-6">
                    <div class="bg-gray-900 p-6 rounded-2xl border border-gray-800 shadow-xl">
                        <h2 class="text-xl font-bold text-red-400 mb-4">💡 Record Utilities & Gym Expenses</h2>
                        <form method="POST" class="grid grid-cols-1 sm:grid-cols-3 gap-4">
                            <input type="hidden" name="form_type" value="add_expense">
                            <div>
                                <label class="text-xs text-gray-400">Expense Category</label>
                                <input type="text" name="category" required class="w-full mt-1 p-2.5 bg-gray-800 rounded-xl border border-gray-700 text-sm" placeholder="Electricity Bill / Maintenance">
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
                                <button type="submit" class="w-full py-3 bg-red-500 hover:bg-red-600 font-bold text-gray-950 rounded-lg transition text-sm shadow-lg">Save Expense</button>
                            </div>
                        </form>
                    </div>

                    <div class="bg-gray-900 rounded-2xl border border-gray-800 shadow-xl overflow-hidden">
                        <div class="p-4 border-b border-gray-800"><h3 class="font-bold text-gray-200">📉 Expenses & Utilities Ledger</h3></div>
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
                labels: {{ plans_count.keys() | list | tojson }},
                datasets: [{
                    data: {{ plans_count.values() | list | tojson }},
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
