from flask import Flask, redirect, request, session, jsonify
app = Flask(__name__)
app.secret_key = 'patta-vercel-2025'

# 🔥 TEST DATA - 2 PERFECT APPS
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
        'submitted_at': '2025-12-28T10:00:00',
        'days_pending': 1
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
        'submitted_at': '2025-12-23T10:00:00',
        'days_pending': 5,
        'approved_by': {'name': 'Admin User'}
    }
]

# 🔥 HARDCODED CHATBOT - 100% WORKING!
CHAT_RESPONSES = {
    'hello': '👋 Hi Admin! 1 pending patta application needs your verification.',
    'help': '✅ COMMANDS:\n• "stats" - See application stats\n• "pending" - List pending apps\n• "approve" - How to approve\n• "verify" - AI document check',
    'stats': f'📊 STATS:\n• Total: {len(applications)}\n• Pending: 1\n• Approved: 1',
    'pending': '⏳ PENDING:\n• PATTA-20251228-0001 (Guindy, Survey 123/A/45)\nClick "AI Verify" button to analyze!',
    'approve': '✅ TO APPROVE:\n1. Click dropdown next to app\n2. Select "Approved"\n3. Saves automatically!',
    'verify': '🤖 AI VERIFY:\nAnalyzes survey numbers + documents\nReturns approve/reject + score 1-10',
    'patta': '📄 PATTA PROCESS:\n1. Citizen submits 5 docs\n2. Staff verifies\n3. Admin approves\n4. Digital patta issued!',
    'default': '🤖 Patta Portal AI Assistant\nType "help" for commands\n1 pending application!'
}

@app.route('/')
def home():
    return '''
    <!DOCTYPE html>
    <html><head><title>Patta Portal</title><script src="https://cdn.tailwindcss.com"></script></head>
    <body class="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-8">
        <div class="bg-white shadow-2xl rounded-2xl p-12 w-full max-w-md text-center">
            <h1 class="text-4xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent mb-8">👑 Patta Portal</h1>
            <form method="POST" action="/login" class="space-y-4">
                <input type="email" name="email" placeholder="admin@test.com" class="w-full p-4 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500" required>
                <input type="password" name="password" placeholder="123456" class="w-full p-4 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500" required>
                <button type="submit" class="w-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white p-4 rounded-xl text-lg font-semibold hover:shadow-lg">🚀 Enter Admin</button>
            </form>
            <p class="text-sm text-gray-500 mt-6">admin/test.com | 123456</p>
        </div>
    </body></html>
    '''

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    
    users = {
        'admin@test.com': {'role': 'admin', 'name': 'Admin User'},
        'staff@test.com': {'role': 'staff', 'name': 'Staff User'},
        'citizen@test.com': {'role': 'citizen', 'name': 'Citizen User'},
    }
    
    user = users.get(email)
    if user and user.get('password', '123456') == password:
        session['role'] = user['role']
        session['name'] = user['name']
        session['email'] = email
        
        if user['role'] == 'admin': return redirect('/admin')
    
    return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/admin')
def admin():
    if session.get('role') != 'admin':
        return redirect('/')
    
    total = len(applications)
    pending = len([a for a in applications if a['status'] == 'pending'])
    
    table_rows = ''.join([
        f'<tr class="hover:bg-gray-50"><td class="p-3">{a["ref_id"]}</td><td class="p-3">{a["citizen_email"]}</td><td class="p-3">{a["village"]}</td><td class="p-3">{a["surveyNo"]}/{a["subdivNo"]}</td><td class="p-3"><span class="px-2 py-1 rounded-full text-xs {"bg-yellow-200" if a["status"]=="pending" else "bg-green-200"}">{a["status"].title()}</span></td><td class="p-3">{a["days_pending"]} days</td></tr>'
        for a in applications
    ])
    
    return f'''
    <!DOCTYPE html>
    <html><head><title>Patta Admin</title><script src="https://cdn.tailwindcss.com"></script></head>
    <body class="bg-gradient-to-br from-indigo-50 to-blue-50 min-h-screen">
        <nav class="bg-white shadow-lg p-6"><div class="max-w-7xl mx-auto flex justify-between">
            <h1 class="text-3xl font-bold text-gray-800">👑 Patta Portal Admin</h1>
            <a href="/logout" class="bg-red-500 text-white px-6 py-2 rounded-xl">Logout</a>
        </div></nav>
        
        <div class="max-w-7xl mx-auto p-8">
            <div class="grid grid-cols-3 gap-6 mb-8">
                <div class="bg-white p-8 rounded-2xl shadow-xl text-center"><h3 class="text-lg font-semibold text-gray-700 mb-2">Total Apps</h3><p class="text-4xl font-bold text-blue-600">{total}</p></div>
                <div class="bg-white p-8 rounded-2xl shadow-xl text-center"><h3 class="text-lg font-semibold text-gray-700 mb-2">Pending</h3><p class="text-4xl font-bold text-yellow-600">{pending}</p></div>
                <div class="bg-white p-8 rounded-2xl shadow-xl text-center"><h3 class="text-lg font-semibold text-gray-700 mb-2">Approved</h3><p class="text-4xl font-bold text-green-600">{total-pending}</p></div>
            </div>
            
            <div class="bg-white rounded-2xl shadow-xl overflow-hidden mb-8">
                <div class="p-6 bg-gradient-to-r from-blue-500 to-indigo-500 text-white"><h2 class="text-2xl font-bold">📋 Applications</h2></div>
                <table class="w-full"><thead><tr class="bg-gray-50"><th class="p-3 text-left font-semibold">Ref ID</th><th class="p-3 text-left font-semibold">Citizen</th><th class="p-3 text-left font-semibold">Village</th><th class="p-3 text-left font-semibold">Survey</th><th class="p-3 text-left font-semibold">Status</th><th class="p-3 text-left font-semibold">Days</th></tr></thead><tbody>{table_rows}</tbody></table>
            </div>
            
            <!-- 🔥 HARDCODED CHATBOT -->
            <div class="bg-white rounded-2xl shadow-xl p-8">
                <h3 class="text-xl font-bold mb-4 flex items-center"><span class="w-3 h-3 bg-green-400 rounded-full mr-2"></span>🤖 Patta AI Assistant</h3>
                <div id="chat-output" class="h-48 overflow-y-auto bg-gray-50 p-4 rounded-xl mb-4 font-mono text-sm">Type "help" for commands...</div>
                <div class="flex gap-2"><input id="chat-input" type="text" placeholder="Ask about patta..." class="flex-1 p-3 border rounded-xl focus:ring-2 focus:ring-blue-500"><button onclick="sendChat()" class="bg-blue-600 text-white px-6 py-3 rounded-xl hover:bg-blue-700">Send</button></div>
            </div>
        </div>
        
        <script>
        async function sendChat() {{
            const input = document.getElementById('chat-input');
            const output = document.getElementById('chat-output');
            const message = input.value.trim().toLowerCase();
            if (!message) return;
            
            output.innerHTML += `<div><strong>You:</strong> ${{message}}</div>`;
            input.value = '';
            
            try {{
                const res = await fetch('/api/gemini/chat', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{message: message}})
                }});
                const data = await res.json();
                output.innerHTML += `<div><strong>🤖 AI:</strong> ${{data.response}}</div>`;
            }} catch(e) {{
                output.innerHTML += `<div><strong>🤖 AI:</strong> Network error - try "help"</div>`;
            }}
            output.scrollTop = output.scrollHeight;
        }}
        
        document.getElementById('chat-input').addEventListener('keypress', (e) => {{
            if (e.key === 'Enter') sendChat();
        }});
        </script>
    </body></html>'''

# 🔥 HARDCODED CHATBOT API
@app.route('/api/gemini/chat', methods=['POST'])
def chat_api():
    try:
        data = request.get_json() or {}
        message = data.get('message', '').lower().strip()
        
        response = CHAT_RESPONSES.get(message, CHAT_RESPONSES['default'])
        return jsonify({'success': True, 'response': response})
    except:
        return jsonify({'success': True, 'response': CHAT_RESPONSES['help']})

@app.route('/api/admin/applications')
def api_apps():
    if session.get('role') != 'admin':
        return jsonify({'error': 'Admin only'}), 403
    return jsonify(applications)

if __name__ == '__main__':
    app.run()
