from flask import Flask, redirect, request, session, render_template, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import os
import json
from datetime import datetime, timedelta
import google.generativeai as genai

# 🔥 GLOBAL VARIABLES - NO MORE UNBOUNDLOCALERROR!
applications = []
next_ref_id = 1
DATA_FILE = 'patta_data.json'
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', None)

def load_data():
    global applications, next_ref_id
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                applications = data.get('applications', [])
                next_ref_id = data.get('next_ref_id', 1)
            print(f"✅ LOADED {len(applications)} saved applications")
            return
        except Exception as e:
            print(f"❌ Load failed: {e}")
    
    # 🔥 TEST DATA - 2 PERFECT APPLICATIONS
    applications = [
        {
            'ref_id': 'PATTA-20251228-0001',
            'citizen_email': 'citizen@test.com',
            'village': 'Guindy',
            'taluk': 'Velachery',
            'district': 'Chennai',
            'surveyNo': '123',
            'subdivNo': 'A/45',
            'status': 'pending',
            'submitted_at': datetime.now().isoformat(),
            'days_pending': 0,
            'documents': {}
        },
        {
            'ref_id': 'PATTA-20251228-0002',
            'citizen_email': 'citizen2@test.com',
            'village': 'Anna Nagar',
            'taluk': 'Aminjikarai',
            'district': 'Chennai',
            'surveyNo': '456',
            'subdivNo': 'B/12',
            'status': 'approved',
            'submitted_at': (datetime.now() - timedelta(days=5)).isoformat(),
            'days_pending': 5,
            'documents': {},
            'approved_by': {'name': 'Admin User', 'email': 'admin@test.com'}
        }
    ]
    next_ref_id = 3
    print("✅ TEST DATA loaded - 2 applications ready!")

def save_data():
    global applications, next_ref_id
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump({
                'applications': applications,
                'next_ref_id': next_ref_id
            }, f, indent=2)
        print("💾 Data saved successfully")
    except Exception as e:
        print(f"❌ Save failed: {e}")

def create_app():
    app = Flask(__name__)
    app.secret_key = 'patta-super-secret-2025'
    
    # 🔥 ATTACH GLOBAL STATE TO APP
    app.applications = applications
    app.next_ref_id = next_ref_id
    
    # 🔥 GEMINI AI CONFIG
    global GEMINI_API_KEY
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        print("✅ Gemini AI READY")
    else:
        print("⚠️ GEMINI_API_KEY missing - AI features disabled")
    
    # 🔥 UPLOADS FOLDER
    UPLOAD_FOLDER = 'uploads'
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    # Load data on startup
    load_data()
    
    # 🔥 CONTEXT PROCESSORS
    @app.context_processor
    def inject_session():
        return dict(session=session)

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
            }
        }
        return dict(lang=languages.get(lang, languages['en']), current_lang=lang)

    # 🔥 FILE SERVER
    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        if '..' in filename or filename.startswith('/') or not filename:
            return "Access Denied", 403
        
        upload_dir = os.path.abspath('uploads')
        file_path = os.path.join(upload_dir, filename)
        
        if not os.path.abspath(file_path).startswith(upload_dir):
            return "Access Denied", 403
        
        if not os.path.isfile(file_path):
            return "File not found", 404
        
        print(f"✅ Serving: {filename}")
        return send_from_directory(upload_dir, filename, as_attachment=False)

    # 🔥 HOME
    @app.route('/', methods=['GET', 'POST'])
    def home():
        if session.get('role') == 'admin': return redirect('/admin')
        if session.get('role') == 'staff': return redirect('/staff')
        if session.get('role') == 'citizen': return redirect('/citizen')
        return render_template('index.html')

    # 🔥 LOGIN
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'GET':
            if session.get('role') == 'admin': return redirect('/admin')
            if session.get('role') == 'staff': return redirect('/staff')
            if session.get('role') == 'citizen': return redirect('/citizen')
            return render_template('index.html')

        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        users = {
            'citizen@test.com': {'password': '123456', 'role': 'citizen', 'name': 'Citizen User'},
            'staff@test.com': {'password': '123456', 'role': 'staff', 'name': 'Staff User'},
            'admin@test.com': {'password': '123456', 'role': 'admin', 'name': 'Admin User'},
        }

        user = users.get(email)
        if not user or user['password'] != password:
            return render_template('index.html', error='Invalid email or password')

        session['role'] = user['role']
        session['name'] = user['name']
        session['email'] = email
        print(f"✅ LOGIN {email} as {user['role']}")

        if user['role'] == 'admin': return redirect('/admin')
        if user['role'] == 'staff': return redirect('/staff')
        return redirect('/citizen')

    # 🔥 LOGOUT
    @app.route('/logout')
    def logout():
        session.clear()
        print("✅ LOGOUT")
        return redirect('/')

    # 🔥 DASHBOARDS
    @app.route('/citizen')
    def citizen():
        if session.get('role') != 'citizen': return redirect('/')
        try:
            return render_template('citizen.html')
        except:
            return '<h1 style="padding:4rem;font-family:Arial;">👤 Citizen Dashboard</h1>'

    @app.route('/staff')
    def staff():
        if session.get('role') not in ['staff', 'admin']: return redirect('/')
        try:
            return render_template('staff.html')
        except:
            return '<h1 style="padding:4rem;font-family:Arial;">🛡️ Staff Dashboard</h1>'

    @app.route('/admin')
    def admin():
        if session.get('role') != 'admin': return redirect('/')
        try:
            return render_template('admin.html')
        except:
            return '<h1 style="padding:4rem;font-family:Arial;">👑 Admin Dashboard</h1>'

    # 🔥 ADMIN API - YOUR MAIN API
    @app.route('/api/admin/applications')
    def api_admin_applications():
        if session.get('role') != 'admin':
            return jsonify({'error': 'Admin only'}), 403
        
        # 🔥 BULLETPROOF DATA PROCESSING
        safe_apps = []
        for app_data in app.applications:
            try:
                safe_app = {
                    'ref_id': app_data.get('ref_id', 'N/A'),
                    'citizen_email': app_data.get('citizen_email', 'Unknown'),
                    'village': app_data.get('village', 'N/A'),
                    'taluk': app_data.get('taluk', 'N/A'),
                    'district': app_data.get('district', 'N/A'),
                    'surveyNo': app_data.get('surveyNo', 'N/A'),
                    'subdivNo': app_data.get('subdivNo', ''),
                    'status': app_data.get('status', 'pending'),
                    'days_pending': 0,
                    'gemini_analysis': app_data.get('gemini_analysis'),
                    'documents': app_data.get('documents', {})
                }
                
                # Calculate days safely
                submitted_at = app_data.get('submitted_at')
                if submitted_at:
                    try:
                        submitted = datetime.fromisoformat(submitted_at.replace('Z', '+00:00'))
                        safe_app['days_pending'] = max(0, (datetime.now() - submitted).days)
                    except:
                        safe_app['days_pending'] = 0
                
                safe_apps.append(safe_app)
            except:
                continue  # Skip broken apps
        
        return jsonify(safe_apps)


    # 🔥 STAFF API
    @app.route('/api/patta/applications')
    def api_applications():
        if session.get('role') not in ['staff', 'admin']:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

        search = request.args.get('search', '').upper()
        status = request.args.get('status', '')
        
        filtered = app.applications[:]
        if search: 
            filtered = [app for app in filtered if search in app.get('ref_id', '')]
        if status: 
            filtered = [app for app in filtered if app.get('status') == status]

        print(f"🔍 STAFF API: Found {len(filtered)} applications")
        return jsonify(filtered)

    # 🔥 CITIZEN API
    @app.route('/api/citizen/applications')
    def api_citizen_applications():
        if session.get('role') != 'citizen':
            return jsonify({'success': False, 'error': 'Citizen only'}), 403
        
        citizen_email = session.get('email', '').lower()
        citizen_apps = [app for app in app.applications if app.get('citizen_email', '').lower() == citizen_email]
        return jsonify(citizen_apps)

    # 🔥 SUBMIT APPLICATION
    @app.route('/api/patta/apply', methods=['POST'])
    def api_apply():
        if session.get('role') != 'citizen':
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

        district = request.form.get('district', '')
        taluk = request.form.get('taluk', '')
        village = request.form.get('village', '')
        lat = request.form.get('lat', '0')
        lng = request.form.get('lng', '0')
        survey_no = request.form.get('surveyNo', '')
        subdiv_no = request.form.get('subdivNo', '')
        
        try:
            boundary = json.loads(request.form.get('boundary', '[]'))
        except:
            boundary = []

        files = {
            'parentDoc': request.files.get('parentDoc'),
            'saleDeed': request.files.get('saleDeed'),
            'aadharCard': request.files.get('aadharCard'),
            'encumbCert': request.files.get('encumbCert'),
            'layoutScan': request.files.get('layoutScan')
        }

        for doc_name, file in files.items():
            if not file or file.filename == '':
                return jsonify({'success': False, 'error': f'{doc_name} required'}), 400

        ref_id = f"PATTA-{datetime.now().strftime('%Y%m%d')}-{app.next_ref_id:04d}"
        app.next_ref_id += 1

        documents = {}
        for doc_name, file in files.items():
            if file and file.filename:
                filename = secure_filename(f"{ref_id}_{doc_name}_{file.filename}")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                documents[doc_name] = f"/uploads/{filename}"

        application = {
            'ref_id': ref_id,
            'citizen_email': session.get('email', 'unknown'),
            'district': district,
            'taluk': taluk,
            'village': village,
            'lat': float(lat),
            'lng': float(lng),
            'surveyNo': survey_no,
            'subdivNo': subdiv_no,
            'boundary': boundary,
            'documents': documents,
            'status': 'pending',
            'submitted_at': datetime.now().isoformat()
        }

        app.applications.append(application)
        save_data()
        print(f"✅ NEW APPLICATION: {ref_id}")
        return jsonify({'success': True, 'ref_id': ref_id})

    # 🔥 UPDATE STATUS
    @app.route('/api/patta/<ref_id>/status', methods=['POST'])
    def api_update_status(ref_id):
        if session.get('role') not in ['staff', 'admin']:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

        try:
            data = request.get_json(force=True)
            status = data.get('status')
        except:
            return jsonify({'success': False, 'error': 'Invalid JSON'}), 400

        if status not in ['pending', 'approved', 'rejected']:
            return jsonify({'success': False, 'error': 'Invalid status'}), 400

        for app_item in app.applications:
            if app_item['ref_id'] == ref_id:
                app_item['status'] = status
                if status in ['approved', 'rejected']:
                    app_item['approved_by'] = {
                        'name': session.get('name', 'Unknown'),
                        'email': session.get('email', 'unknown'),
                        'timestamp': datetime.now().isoformat()
                    }
                save_data()
                print(f"✅ {ref_id} → {status}")
                return jsonify({'success': True, 'status': status})
        
        return jsonify({'success': False, 'error': 'Application not found'}), 404

    # 🔥 GEMINI VERIFY
    @app.route('/api/gemini/verify/<ref_id>', methods=['POST'])
    def api_gemini_verify(ref_id):
        if session.get('role') not in ['staff', 'admin']:
            return jsonify({'success': False, 'error': 'Staff/Admin only'}), 403
        
        if not GEMINI_API_KEY:
            return jsonify({'success': False, 'error': 'Gemini not configured'}), 503
        
        app_item = next((a for a in app.applications if a['ref_id'] == ref_id), None)
        if not app_item:
            return jsonify({'success': False, 'error': 'Application not found'}), 404
        
        try:
            context = f"""
            Analyze Patta application:
            Location: {app_item.get('village', 'N/A')}, {app_item.get('taluk', 'N/A')}
            Survey: {app_item.get('surveyNo', 'N/A')}/{app_item.get('subdivNo', 'N/A')}
            Status: {app_item.get('status', 'pending')}
            
            Provide: approve/reject/pending, issues, score 1-10.
            """
            
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(context)
            ai_analysis = response.text
            
            app_item['gemini_analysis'] = {
                'analysis': ai_analysis,
                'analyzed_by': session.get('email'),
                'analyzed_at': datetime.now().isoformat()
            }
            save_data()
            
            return jsonify({'success': True, 'analysis': ai_analysis})
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    # 🔥 GEMINI CHAT
    @app.route('/api/gemini/chat', methods=['POST'])
    def api_gemini_chat():
        try:
            data = request.get_json() or {}
            message = data.get('message', '').lower().strip()
            role = session.get('role', 'guest')
            pending_count = len([a for a in applications if a.get('status') == 'pending'])
            total_count = len(applications)
            
            # 🔥 ROLE-SPECIFIC RESPONSES
            responses = {
                # ADMIN RESPONSES
                'admin': {
                    'hello': f'👋 Hi Admin! {pending_count} pending, {total_count} total apps.',
                    'help': '''✅ ADMIN COMMANDS:
    • "stats" - Full statistics
    • "pending" - List pending apps
    • "approve" - Approval steps
    • "verify" - AI verification
    • "patta" - Process overview''',
                    'stats': f'📊 ADMIN STATS:\n• Total: {total_count}\n• Pending: {pending_count}\n• Approved: {total_count-pending_count}',
                    'pending': f'⏳ PENDING ({pending_count}):\n• PATTA-20251228-0001 (Guindy)\nClick AI Verify!',
                    'approve': '✅ APPROVE: Status dropdown → "Approved" → Auto-save!',
                    'verify': '🤖 AI VERIFY: Analyzes docs → Approve/Reject + Score 1-10',
                    'patta': '📄 ADMIN: Verify → Approve → Issue digital Patta!'
                },
                
                # CITIZEN RESPONSES
                'citizen': {
                    'hello': f'👋 Welcome Citizen! Track your {pending_count} applications.',
                    'help': '''✅ CITIZEN COMMANDS:
    • "track" - Track Ref ID
    • "status" - Check status
    • "documents" - Required docs
    • "submit" - Submit guide
    • "patta" - What is Patta?''',
                    'track': f'🔍 TRACK: Enter Ref ID (PATTA-XXXX). {pending_count} pending apps.',
                    'status': f'📋 STATUS: {pending_count} pending. Check dashboard!',
                    'documents': '''📄 REQUIRED (5 DOCS):
    1. Parent document
    2. Sale deed  
    3. Aadhar card
    4. Encumbrance cert
    5. Layout scan''',
                    'submit': '''📤 SUBMIT:
    1. "New Application"
    2. Draw map boundary
    3. Upload 5 docs
    4. Get Ref ID instantly!''',
                    'patta': '🏆 PATTA = Digital land ownership certificate!'
                },
                
                # GUEST RESPONSES  
                'guest': {
                    'default': '👋 Login as admin/citizen@test.com (123456)'
                }
            }
            
            role_responses = responses.get(role, responses['guest'])
            specific_response = role_responses.get(message, role_responses.get('default', responses['admin']['default']))
            
            return jsonify({'success': True, 'response': specific_response})
            
        except:
            return jsonify({'success': True, 'response': '🤖 AI ready! Type "help".'})

    # 🔥 DEBUG
    @app.route('/debug')
    def debug():
        return f'''
        <h1>✅ Patta Portal ACTIVE</h1>
        <p>Role: <strong>{session.get("role") or "None"}</strong></p>
        <p>Apps: {len(app.applications)}</p>
        <p>Pending: {len([a for a in app.applications if a.get("status") == "pending"])}</p>
        <p>Gemini: {"✅ READY" if GEMINI_API_KEY else "❌ MISSING"}</p>
        <a href="/" style="background:#10b981;color:white;padding:1rem;border-radius:8px;text-decoration:none;">→ Login</a>
        '''

    print("✅ Patta Portal fully loaded - All features active!")
    return app

