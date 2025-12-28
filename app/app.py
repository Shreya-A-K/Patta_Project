from flask import (
    Flask, redirect, request, session,
    render_template, jsonify, send_from_directory
)
from werkzeug.utils import secure_filename
import os, json
from datetime import datetime, timedelta
import google.generativeai as genai

# =========================
# GLOBAL STATE
# =========================
applications = []
next_ref_id = 1
DATA_FILE = "patta_data.json"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# =========================
# DATA HELPERS
# =========================
def load_data():
    global applications, next_ref_id
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                applications = data.get("applications", [])
                next_ref_id = data.get("next_ref_id", 1)
            print(f"✅ Loaded {len(applications)} applications")
            return
        except Exception as e:
            print("❌ Failed loading data:", e)

    applications = [
        {
            "ref_id": "PATTA-20251228-0001",
            "citizen_email": "citizen@test.com",
            "village": "Guindy",
            "taluk": "Velachery",
            "district": "Chennai",
            "surveyNo": "123",
            "subdivNo": "A/45",
            "status": "pending",
            "submitted_at": datetime.now().isoformat(),
            "documents": {}
        },
        {
            "ref_id": "PATTA-20251228-0002",
            "citizen_email": "citizen2@test.com",
            "village": "Anna Nagar",
            "taluk": "Aminjikarai",
            "district": "Chennai",
            "surveyNo": "456",
            "subdivNo": "B/12",
            "status": "approved",
            "submitted_at": (datetime.now() - timedelta(days=5)).isoformat(),
            "documents": {},
            "approved_by": {
                "name": "Admin User",
                "email": "admin@test.com"
            }
        }
    ]
    next_ref_id = 3
    print("✅ Test data initialized")


def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump({
            "applications": applications,
            "next_ref_id": next_ref_id
        }, f, indent=2)
    print("💾 Data saved")


# =========================
# APP FACTORY
# =========================
def create_app():
    app = Flask(__name__)
    app.secret_key = "patta-super-secret-2025"

    app.applications = applications
    app.next_ref_id = next_ref_id

    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        print("✅ Gemini configured")
    else:
        print("⚠️ Gemini disabled (no API key)")

    UPLOAD_FOLDER = "uploads"
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

    load_data()

    # =========================
    # BASIC ROUTES
    # =========================
    @app.context_processor
    def inject_language():
        lang = request.cookies.get('lang', 'en')
        languages = {
    'en': {
        'Patta Application': 'Patta Portal', 
        'Logout': 'Logout',
        'Track Applications': 'Track My Applications',
        'Track My Applications': 'Track My Applications',
        'Staff Dashboard - Patta Verification': 'Staff Dashboard - Patta Verification',
        'Patta Verification Dashboard': 'Patta Verification Dashboard'
    },
    'ta': {
        'Patta Application': 'பட்டா போர்டல்', 
        'Logout': 'வெளியேறு',
        'Track Applications': 'என் விண்ணப்பங்களைப் பின்தொடரவும்',
        'Track My Applications': 'என் விண்ணப்பங்களைப் பின்தொடரவும்',
        'Staff Dashboard - Patta Verification': 'பட்டா சரிபார்ப்பு டாஷ்போர்ட்',
        'Patta Verification Dashboard': 'பட்டா சரிபார்ப்பு டாஷ்போர்ட்'
    },
    'kn': {
        'Patta Application': 'ಪಟ್ಟಾ ಪೋರ್ಟಲ್',
        'Logout': 'ಬಿಡಾ',
        'Track Applications': 'ನನ್ನ ಅರ್ಜಿಗಳನ್ನು ಟ್ರ್ಯಾಕ್ ಮಾಡಿ',
        'Track My Applications': 'ನನ್ನ ಅರ್ಜಿಗಳನ್ನು ಟ್ರ್ಯಾಕ್ ಮಾಡಿ',
        'Staff Dashboard - Patta Verification': 'ಪಟ್ಟಾ ಪರಿಶೀಲನೆ ಸ್ಟಾಫ್ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್',
        'Patta Verification Dashboard': 'ಪಟ್ಟಾ ಪರಿಶೀಲನೆ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್'
    },
    'te': {
        'Patta Application': 'పట్టా పోర్టల్',
        'Logout': 'లాగౌట్',
        'Track Applications': 'నా అప్లికేషన్లను ట్రాక్ చేయండి',
        'Track My Applications': 'నా అప్లికేషన్లను ట్రాక్ చేయండి',
        'Staff Dashboard - Patta Verification': 'పట్టా ధృవీకరణ స్టాఫ్ డాష్‌బోర్డ్',
        'Patta Verification Dashboard': 'పట్టా ధృవీకరణ డాష్‌బోర్డ్'
    },
    'ml': {
        'Patta Application': 'പട്ട ഓർട്ടൽ',
        'Logout': 'ലോഗൗട്ട്',
        'Track Applications': 'എന്റെ അപേക്ഷകൾ ട്രാക്ക് ചെയ്യുക',
        'Track My Applications': 'എന്റെ അപേക്ഷകൾ ട്രാക്ക് ചെയ്യുക',
        'Staff Dashboard - Patta Verification': 'പട്ട സ്ഥിരീകരണ സ്റ്റാഫ് ഡാഷ്ബോർഡ്',
        'Patta Verification Dashboard': 'പട്ട സ്ഥിരീകരണ ഡാഷ്ബോർഡ്'
    },
    'hi': {
        'Patta Application': 'पट्टा पोर्टल',
        'Logout': 'लॉग आउट',
        'Track Applications': 'मेरे आवेदनों को ट्रैक करें',
        'Track My Applications': 'मेरे आवेदनों को ट्रैक करें',
        'Staff Dashboard - Patta Verification': 'पट्टा सत्यापन स्टाफ डैशबोर्ड',
        'Patta Verification Dashboard': 'पट्टा सत्यापन डैशबोर्ड'
    },
    'bn': {
        'Patta Application': 'পট্টা পোর্টাল',
        'Logout': 'লগ আউট',
        'Track Applications': 'আমার আবেদনগুলি ট্র্যাক করুন',
        'Track My Applications': 'আমার আবেদনগুলি ট্র্যাক করুন',
        'Staff Dashboard - Patta Verification': 'পট্টা যাচাই স্টাফ ড্যাশবোর্ড',
        'Patta Verification Dashboard': 'পট্টা যাচাই ড্যাশবোর্ড'
    },
    'mr': {
        'Patta Application': 'पट्टा पोर्टल',
        'Logout': 'बाहेर पडा',
        'Track Applications': 'माझ्या अर्जांचा मागोवा घ्या',
        'Track My Applications': 'माझ्या अर्जांचा मागोवा घ्या',
        'Staff Dashboard - Patta Verification': 'पट्टा तपासणी स्टाफ डॅशबोर्ड',
        'Patta Verification Dashboard': 'पट्टा तपासणी डॅशबोर्ड'
    },
    'gu': {
        'Patta Application': 'પટ્ટા પોર્ટલ',
        'Logout': 'લૉગઆઉટ',
        'Track Applications': 'મારા અરજીઓ ટ્રેક કરો',
        'Track My Applications': 'મારા અરજીઓ ટ્રેક કરો',
        'Staff Dashboard - Patta Verification': 'પટ્ટા ચકાસણી સ્ટાફ ડેશબોર્ડ',
        'Patta Verification Dashboard': 'પટ્ટા ચકાસણી ડેશબોર્ડ'
    },
    'pa': {
        'Patta Application': 'ਪਟਟਾ ਪੋਰਟਲ',
        'Logout': 'ਲੌਗ ਆਊਟ',
        'Track Applications': 'ਮੇਰੀਆਂ ਅਰਜ਼ੀਆਂ ਟਰੈਕ ਕਰੋ',
        'Track My Applications': 'ਮੇਰੀਆਂ ਅਰਜ਼ੀਆਂ ਟਰੈਕ ਕਰੋ',
        'Staff Dashboard - Patta Verification': 'ਪਟਟਾ ਜਾਂਚ ਸਟਾਫ਼ ਡੈਸ਼ਬੋਰਡ',
        'Patta Verification Dashboard': 'ਪਟਟਾ ਜਾਂਚ ਡੈਸ਼ਬੋਰਡ'
    }
}


        return dict(lang=languages.get(lang, languages['en']), current_lang=lang)

    @app.route("/")
    def home():
        role = session.get("role")
        if role == "admin": return redirect("/admin")
        if role == "staff": return redirect("/staff")
        if role == "citizen": return redirect("/citizen")
        return render_template("index.html")

    @app.route("/login", methods=["POST"])
    def login():
        email = request.form.get("email", "").lower().strip()
        password = request.form.get("password", "")

        users = {
            "admin@test.com":   {"password": "123456", "role": "admin",   "name": "Admin User"},
            "staff@test.com":   {"password": "123456", "role": "staff",   "name": "Staff User"},
            "citizen@test.com": {"password": "123456", "role": "citizen", "name": "Citizen User"},
        }

        user = users.get(email)
        if not user or user["password"] != password:
            return render_template("index.html", error="Invalid credentials")

        session["email"] = email
        session["role"] = user["role"]
        session["name"] = user["name"]

        print(f"✅ Login: {email} ({user['role']})")

        return redirect(f"/{user['role']}")

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect("/")

    # =========================
    # DASHBOARDS
    # =========================
    @app.route("/admin")
    def admin():
        if session.get("role") != "admin":
            return redirect("/")
        return render_template("admin.html")

    @app.route("/staff")
    def staff():
        if session.get("role") not in ["staff", "admin"]:
            return redirect("/")
        return render_template("staff.html")

    @app.route("/citizen")
    def citizen():
        if session.get("role") != "citizen":
            return redirect("/")
        return render_template("citizen.html")

    # =========================
    # FILE SERVING
    # =========================
    @app.route("/uploads/<path:filename>")
    def uploads(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    # =========================
    # ADMIN API
    # =========================
    @app.route("/api/admin/applications")
    def admin_apps():
        if session.get("role") != "admin":
            return jsonify({"error": "Admin only"}), 403
        return jsonify(app.applications)

    # =========================
    # GEMINI CHAT
    # =========================
    @app.route("/api/gemini/chat", methods=["POST"])
    def gemini_chat():
        data = request.get_json() or {}
        msg = data.get("message", "").lower().strip()
        pending = len([a for a in applications if a["status"] == "pending"])

        responses = {
            "hello": f"👋 Hi! {pending} pending applications.",
            "help": "Commands: stats, pending, patta",
            "stats": f"Total: {len(applications)}, Pending: {pending}",
            "pending": "Use Admin dashboard to verify pending applications.",
            "patta": "Patta is a digital land ownership certificate."
        }

        return jsonify({"response": responses.get(msg, "Type 'help'")})

    # =========================
    # DEBUG
    # =========================
    @app.route("/debug")
    def debug():
        return {
            "role": session.get("role"),
            "applications": len(app.applications),
            "pending": len([a for a in app.applications if a["status"] == "pending"]),
            "gemini": bool(GEMINI_API_KEY)
        }

    print("✅ Patta Portal ready")
    return app
