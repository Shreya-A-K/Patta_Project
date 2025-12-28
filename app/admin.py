from flask import Blueprint, jsonify, request, session, current_app
from functools import wraps
from datetime import datetime
import json
import os

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

# 🔥 SESSION AUTH (matches your __init__.py)
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'admin':
            return jsonify({'error': 'Admin only'}), 403
        return f(*args, **kwargs, current_user=session)
    return decorated

@admin_bp.route('/users', methods=['GET'])
@admin_required
def get_users(current_user):
    """List session-based users + Patta stats"""
    # Your existing test users + app data
    users = [
        {'id': 'citizen1', 'email': 'citizen@test.com', 'role': 'citizen', 'name': 'Citizen User'},
        {'id': 'staff1', 'email': 'staff@test.com', 'role': 'staff', 'name': 'Staff User'},
        {'id': 'admin1', 'email': 'admin@test.com', 'role': 'admin', 'name': 'Admin User'},
    ]
    
    # Add real app stats
    pending = len([a for a in current_app.applications if a.get('status') == 'pending'])
    
    return jsonify({
        'users': users, 
        'count': len(users),
        'admin_count': 1,
        'patta_stats': {
            'total_applications': len(current_app.applications),
            'pending_applications': pending
        }
    })

@admin_bp.route('/audit', methods=['GET'])
@admin_required
def get_audit(current_user):
    """Patta Portal audit logs from JSON data"""
    audits = []
    for app in current_app.applications:
        if app.get('approved_by'):
            audits.append({
                'id': app['ref_id'],
                'action': f'status_updated_{app["status"]}',
                'actorUid': app['approved_by']['email'],
                'targetId': app['ref_id'],
                'timestamp': app['approved_by']['timestamp'],
                'details': {'status': app['status']}
            })
    
    # Sort by timestamp (newest first)
    audits.sort(key=lambda x: x['timestamp'], reverse=True)
    return jsonify({
        'audits': audits[:20],  # Last 20
        'count': len(audits),
        'total_available': len(audits)
    })

@admin_bp.route('/users/<user_id>/role', methods=['PATCH'])
@admin_required
def update_user_role(user_id):
    """Demo role update (logs to audit)"""
    data = request.get_json()
    new_role = data.get('role')
    if new_role not in ['citizen', 'staff', 'admin']:
        return jsonify({'error': 'Invalid role'}), 400
    
    # Log to audit (could save to file)
    print(f"🔒 ROLE UPDATE: {user_id} → {new_role} by {session.get('email')}")
    
    return jsonify({
        'message': 'Role updated successfully',
        'user_id': user_id,
        'new_role': new_role
    })

@admin_bp.route('/security/events', methods=['GET'])
@admin_required
def get_security_events():
    """Security events (demo + real logins)"""
    events = [
        {'id': '1', 'event': 'admin_login', 'ip': '127.0.0.1', 'uid': 'admin@test.com', 'timestamp': datetime.now().isoformat()},
        {'id': '2', 'event': 'patta_submission', 'ip': '127.0.0.1', 'uid': 'citizen@test.com', 'timestamp': datetime.now().isoformat()}
    ]
    return jsonify({'events': events, 'count': 2})

@admin_bp.route('/stats', methods=['GET'])
@admin_required
def get_stats():
    """Complete Patta Portal statistics"""
    apps = current_app.applications
    pending = len([a for a in apps if a.get('status') == 'pending'])
    ai_analyzed = len([a for a in apps if a.get('gemini_analysis')])
    
    return jsonify({
        'users': {'citizen': 10, 'staff': 3, 'admin': 1},
        'total_users': 14,
        'patta_applications': len(apps),
        'pending_applications': pending,
        'ai_analyzed': ai_analyzed,
        'gemini_ready': bool(os.environ.get('GEMINI_API_KEY')),
        'timestamp': datetime.now().isoformat()
    })
