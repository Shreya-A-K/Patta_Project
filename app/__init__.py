from flask import Flask, redirect, request, session, render_template, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import os
import json
from datetime import datetime

def create_app():
    app = Flask(__name__)
    app.secret_key = 'patta-super-secret-2025'
    
    # 🔥 UPLOADS FOLDER
    UPLOAD_FOLDER = 'uploads'
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    # 🔥 PERSISTENT STORAGE
    DATA_FILE = 'patta_data.json'
    
    def load_data():
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r') as f:
                    data = json.load(f)
                    app.applications = data.get('applications', [])
                    app.next_ref_id = data.get('next_ref_id', 1)
                print(f"✅ LOADED {len(app.applications)} saved applications")
            except:
                print("❌ Load failed, starting fresh")
                app.applications = []
                app.next_ref_id = 1
        else:
            # 🔥 TEST DATA - Shows IMMEDIATELY!
            app.applications = [
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
                    'days_pending': 0
                }
            ]
            app.next_ref_id = 2
            print("✅ TEST DATA loaded - 1 application ready!")
    
    def save_data():
        try:
            with open(DATA_FILE, 'w') as f:
                json.dump({
                    'applications': app.applications,
                    'next_ref_id': app.next_ref_id
                }, f, indent=2)
        except Exception as e:
            print(f"❌ Save failed: {e}")
    
    # Load data on startup
    load_data()
    
    # 🔥 SESSION IN ALL TEMPLATES
    @app.context_processor
    def inject_session():
        return dict(session=session)

    # 🔥 LANGUAGE SUPPORT
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

    # 🔥 BULLETPROOF DOCUMENT SERVER
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
            'citizen@test.com': {'password': '123456', 'role': 'citizen', 'name': 'Citizen User', 'email': 'citizen@test.com'},
            'staff@test.com': {'password': '123456', 'role': 'staff', 'name': 'Staff User', 'email': 'staff@test.com'},
            'admin@test.com': {'password': '123456', 'role': 'admin', 'name': 'Admin User', 'email': 'admin@test.com'},
        }

        user = users.get(email)
        if not user or user['password'] != password:
            return render_template('index.html', error='Invalid email or password')

        session['role'] = user['role']
        session['name'] = user['name']
        session['email'] = user['email']
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

    # 🔥 API: LIST APPLICATIONS (STAFF + ADMIN)
    @app.route('/api/patta/applications')
    def api_applications():
        if session.get('role') not in ['staff', 'admin']:
            print(f"❌ STAFF API: Unauthorized role={session.get('role')}")
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

        search = request.args.get('search', '').upper()
        status = request.args.get('status', '')
        date_filter = request.args.get('date', '')

        filtered = app.applications[:]
        if search: filtered = [app for app in filtered if search in app['ref_id']]
        if status: filtered = [app for app in filtered if app['status'] == status]
        if date_filter: filtered = [app for app in filtered if app['submitted_at'][:10] == date_filter]

        print(f"🔍 STAFF API: Role={session.get('role')}, Found {len(filtered)} applications")
        return jsonify(filtered)

    # 🔥 API: ADMIN VIEW - HARDCODED ACCESS
    @app.route('/api/admin/applications')
    def api_admin_applications():
        print(f"🔍 ADMIN API: Total apps = {len(app.applications)}")
        
        admin_view = []
        for app in app.applications:
            if not app.get('submitted_at'):
                continue
                
            display_app = app.copy()
            display_app['days_pending'] = max(0, (datetime.now() - datetime.fromisoformat(app['submitted_at'])).days)
            
            if app.get('status') == 'approved' and app.get('approved_by'):
                display_app['approved_by_staff'] = f"{app['approved_by'].get('name', 'N/A')} ({app['approved_by'].get('email', 'N/A')})"
            else:
                display_app['approved_by_staff'] = 'N/A'
                
            # Ensure required fields
            display_app.setdefault('village', 'N/A')
            display_app.setdefault('taluk', 'N/A')
            display_app.setdefault('district', 'N/A')
            display_app.setdefault('surveyNo', 'N/A')
            
            admin_view.append(display_app)
        
        print(f"✅ ADMIN API SUCCESS: Returning {len(admin_view)} apps")
        return jsonify(admin_view)

    # 🔥 API: CITIZEN TRACK OWN APPLICATIONS
    @app.route('/api/citizen/applications')
    def api_citizen_applications():
        if session.get('role') != 'citizen':
            return jsonify({'success': False, 'error': 'Citizen only'}), 403
        
        citizen_email = session.get('email', '').lower()
        citizen_apps = [app for app in app.applications if app['citizen_email'].lower() == citizen_email]
        return jsonify(citizen_apps)

    # 🔥 API: SUBMIT APPLICATION
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
        boundary = json.loads(request.form.get('boundary', '[]'))

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
        save_data()  # 🔥 SAVE TO FILE
        print(f"✅ NEW APPLICATION: {ref_id} | Total apps now: {len(app.applications)}")
        return jsonify({'success': True, 'ref_id': ref_id})

    # 🔥 FIXED API: UPDATE STATUS
    @app.route('/api/patta/<ref_id>/status', methods=['POST'])
    def api_update_status(ref_id):
        if session.get('role') not in ['staff', 'admin']:
            print("❌ Unauthorized access")
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

        try:
            data = request.get_json(force=True)
            if not data:
                print("❌ No JSON data")
                return jsonify({'success': False, 'error': 'No JSON data received'}), 400
        except Exception as e:
            print(f"❌ JSON parse error: {e}")
            return jsonify({'success': False, 'error': f'Invalid JSON: {str(e)}'}), 400

        status = data.get('status')
        print(f"📥 Status update {ref_id} → {status} by {session.get('name')}")

        if status not in ['pending', 'approved', 'rejected']:
            return jsonify({'success': False, 'error': 'Invalid status'}), 400

        app_found = False
        for app_item in app.applications:
            if app_item['ref_id'] == ref_id:
                app_found = True
                app_item['status'] = status
                
                if status in ['approved', 'rejected']:
                    app_item['approved_by'] = {
                        'name': session.get('name', 'Unknown'),
                        'email': session.get('email', 'unknown'),
                        'role': session.get('role'),
                        'timestamp': datetime.now().isoformat()
                    }
                
                print(f"✅ {ref_id} → {status} SUCCESS")
                save_data()  # 🔥 SAVE TO FILE
                return jsonify({'success': True, 'ref_id': ref_id, 'status': status})
        
        print(f"❌ Application {ref_id} not found")
        return jsonify({'success': False, 'error': 'Application not found'}), 404

    # 🔥 DEBUG
    @app.route('/debug')
    def debug():
        return f'''
        <h1>✅ Patta Portal ACTIVE</h1>
        <p>Role: <strong>{session.get("role")}</strong></p>
        <p>Session: {dict(session)}</p>
        <p>Apps: {len(app.applications)}</p>
        <p>Pending: {len([a for a in app.applications if a.get("status") == "pending"])}</p>
        <a href="/" style="background:#10b981;color:white;padding:1rem;border-radius:8px;text-decoration:none;">→ Login</a>
        '''

    return app


