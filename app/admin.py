from flask import Blueprint, jsonify, request
import firebase_admin
from firebase_admin import firestore, auth, credentials
from functools import wraps
import os
from dotenv import load_dotenv
#hello change

# Load environment (don't init Firebase here - use app/__init__.py)
load_dotenv()

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

# ✅ FIXED: Self-contained token_required (no external deps)
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'Token required'}), 401
        
        try:
            decoded = auth.verify_id_token(token)
            uid = decoded['uid']
            
            # Get global db from flask app context
            from flask import current_app
            db = current_app.db
            
            user_doc = db.collection('users').document(uid).get()
            if not user_doc.exists:
                return jsonify({'error': 'User not found'}), 404
            
            user_data = user_doc.to_dict()
            return f(*args, **kwargs, current_user=user_data, uid=uid)
        except Exception as e:
            return jsonify({'error': 'Invalid token', 'details': str(e)}), 401
    return decorated

@admin_bp.route('/users', methods=['GET'])
@token_required
def get_users(current_user, uid):
    """List all users (Admin only)"""
    if current_user.get('role') != 'admin':
        return jsonify({'error': 'Admin only'}), 403
    
    try:
        from flask import current_app
        db = current_app.db
        
        users = db.collection('users').stream()
        user_list = []
        for user in users:
            user_data = user.to_dict()
            sanitized_user = {
                'id': user.id,
                'email': user_data.get('email', ''),
                'role': user_data.get('role', 'citizen'),
                'name': user_data.get('name', ''),
                'provider': user_data.get('provider', 'email'),
                'createdAt': str(user_data.get('createdAt', '')),
                'last_activity': str(user_data.get('last_activity', ''))
            }
            user_list.append(sanitized_user)
        
        return jsonify({
            'users': user_list, 
            'count': len(user_list),
            'admin_count': len([u for u in user_list if u['role'] == 'admin'])
        })
    
    except Exception as e:
        return jsonify({'error': 'Failed to fetch users', 'details': str(e)}), 500

@admin_bp.route('/audit', methods=['GET'])
@token_required
def get_audit(current_user, uid):
    """Get recent audit logs (Admin only)"""
    if current_user.get('role') != 'admin':
        return jsonify({'error': 'Admin only'}), 403
    
    try:
        from flask import current_app
        db = current_app.db
        
        audits = (
            db.collection('audit_trails')
            .order_by('timestamp', direction=firestore.Query.DESCENDING)
            .limit(100)
            .stream()
        )
        
        audit_list = []
        for audit in audits:
            audit_data = audit.to_dict()
            audit_list.append({
                'id': audit.id,
                'action': audit_data.get('action', ''),
                'actorUid': audit_data.get('actorUid', ''),
                'targetId': audit_data.get('targetId', ''),
                'timestamp': str(audit_data.get('timestamp', '')),
                'details': audit_data.get('details', {}),
                'data_hash': audit_data.get('data_hash', '')  # Tamper-proof
            })
        
        return jsonify({
            'audits': audit_list, 
            'count': len(audit_list),
            'total_available': '100+' if len(audit_list) == 100 else str(len(audit_list))
        })
    
    except Exception as e:
        return jsonify({'error': 'Failed to fetch audit logs', 'details': str(e)}), 500

@admin_bp.route('/users/<user_id>/role', methods=['PATCH'])
@token_required
def update_user_role(user_id, current_user, uid):
    """Update user role (Admin only)"""
    if current_user.get('role') != 'admin':
        return jsonify({'error': 'Admin only'}), 403
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid JSON'}), 400
    
    new_role = data.get('role')
    if new_role not in ['citizen', 'staff', 'admin']:
        return jsonify({'error': 'Invalid role. Must be: citizen, staff, admin'}), 400
    
    try:
        from flask import current_app
        db = current_app.db
        
        # ✅ FIXED: Use firestore.SERVER_TIMESTAMP correctly
        db.collection('users').document(user_id).update({
            'role': new_role,
            'role_updated_by': uid,
            'role_updated_at': firestore.SERVER_TIMESTAMP
        })
        
        # Audit log
        db.collection('audit_trails').add({
            'action': 'user_role_updated',
            'actorUid': uid,
            'targetId': user_id,
            'timestamp': firestore.SERVER_TIMESTAMP,
            'details': {'new_role': new_role, 'old_role': current_user.get('role')},
            'immutable': True
        })
        
        return jsonify({
            'message': 'Role updated successfully',
            'user_id': user_id,
            'new_role': new_role
        })
    
    except Exception as e:
        return jsonify({'error': 'Failed to update role', 'details': str(e)}), 500

@admin_bp.route('/security/events', methods=['GET'])
@token_required
def get_security_events(current_user, uid):
    """Security events log (Admin only)"""
    if current_user.get('role') != 'admin':
        return jsonify({'error': 'Admin only'}), 403
    
    try:
        from flask import current_app
        db = current_app.db
        
        events = (
            db.collection('security_events')
            .order_by('timestamp', direction=firestore.Query.DESCENDING)
            .limit(50)
            .stream()
        )
        
        event_list = []
        for event in events:
            event_data = event.to_dict()
            event_list.append({
                'id': event.id,
                'event': event_data.get('event', ''),
                'ip': event_data.get('ip', 'unknown'),
                'uid': event_data.get('uid', 'anonymous'),
                'timestamp': str(event_data.get('timestamp', '')),
                'details': event_data.get('details', {})
            })
        
        return jsonify({
            'events': event_list, 
            'count': len(event_list),
            'critical_count': len([e for e in event_list if 'suspicious' in e.get('event', '').lower()])
        })
    
    except Exception as e:
        return jsonify({'error': 'Failed to fetch security events', 'details': str(e)}), 500

@admin_bp.route('/stats', methods=['GET'])
@token_required
def get_stats(current_user, uid):
    """System statistics (Admin only)"""
    if current_user.get('role') != 'admin':
        return jsonify({'error': 'Admin only'}), 403
    
    try:
        from flask import current_app
        db = current_app.db
        
        # Count users by role
        users = db.collection('users').stream()
        role_counts = {'citizen': 0, 'staff': 0, 'admin': 0}
        for user in users:
            role = user.to_dict().get('role', 'citizen')
            role_counts[role] += 1
        
        # Recent activity
        recent_audits = (
            db.collection('audit_trails')
            .order_by('timestamp', direction=firestore.Query.DESCENDING)
            .limit(24)
            .stream()
        )
        active_hours = len(list(recent_audits))
        
        return jsonify({
            'users': role_counts,
            'total_users': sum(role_counts.values()),
            'active_last_24h': active_hours,
            'timestamp': firestore.SERVER_TIMESTAMP
        })
    
    except Exception as e:
        return jsonify({'error': 'Failed to fetch stats', 'details': str(e)}), 500
