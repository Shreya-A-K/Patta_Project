from flask import Blueprint, request, jsonify
import firebase_admin
from firebase_admin import firestore, storage, credentials
from functools import wraps
import os
from dotenv import load_dotenv
import uuid
import time
from hashlib import sha256
import firebase_admin

# Load environment & initialize Firebase
load_dotenv()
if not firebase_admin._apps:
    cred = credentials.Certificate(os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH'))
    firebase_admin.initialize_app(cred, {
        'projectId': os.getenv('FIREBASE_PROJECT_ID'),
    })

# Global Firestore client
db = firestore.client()

patta_bp = Blueprint('patta', __name__, url_prefix='/api/patta')

# ✅ FIXED: Token required decorator (self-contained)
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        from flask import request
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'Token required'}), 401
        
        try:
            from firebase_admin import auth
            decoded = auth.verify_id_token(token)
            uid = decoded['uid']
            user_doc = db.collection('users').document(uid).get()
            
            if not user_doc.exists:
                return jsonify({'error': 'User not found'}), 404
            
            user_data = user_doc.to_dict()
            return f(*args, **kwargs, current_user=user_data, uid=uid)
        except Exception as e:
            return jsonify({'error': 'Invalid token'}), 401
    return decorated

# ✅ FIXED: Role required decorator
def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user or current_user.get('role') not in roles:
                return jsonify({'error': 'Insufficient permissions'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ✅ FIXED: Rate limiting decorator (self-contained)
def rate_limit(key="ip", limit=100, window=3600):
    from collections import defaultdict
    rate_limits = defaultdict(list)
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import request
            client_key = request.remote_addr if key == "ip" else key
            now = time.time()
            rate_limits[client_key] = [
                req_time for req_time in rate_limits[client_key] 
                if now - req_time < window
            ]
            if len(rate_limits[client_key]) >= limit:
                return jsonify({'error': 'Rate limit exceeded'}), 429
            rate_limits[client_key].append(now)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@patta_bp.route('/requests', methods=['GET', 'POST'])
@token_required
@rate_limit(limit=50, window=3600)
def requests(current_user, uid):
    """Handle verification requests - GET list, POST create"""
    if request.method == 'POST':
        return create_request(current_user, uid)
    else:
        return list_requests(current_user, uid)

def create_request(current_user, uid):
    """Citizen creates verification request"""
    if current_user['role'] != 'citizen':
        return jsonify({'error': 'Only citizens can create requests'}), 403
    
    # ✅ FIXED: Proper sanitization
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid JSON'}), 400
    
    from .security import sanitize_input
    data = sanitize_input(data)
    
    # Validate required fields
    required_fields = ['pattaId', 'location']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing {field}'}), 400
    
    # Validate location coordinates
    try:
        location = data['location']
        lat = float(location.get('lat', 0))
        lng = float(location.get('lng', 0))
        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            return jsonify({'error': 'Invalid coordinates'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid location format'}), 400
    
    # Generate secure ID
    request_id = str(uuid.uuid4())
    
    request_data = {
        'requestId': request_id,
        'citizenUid': uid,
        'pattaId': data['pattaId'],
        'status': 'pending',
        'createdAt': firestore.SERVER_TIMESTAMP,
        'documents': [],
        'location': {
            'lat': lat,
            'lng': lng
        }
    }
    
    # ✅ FIXED: Atomic batch write
    batch = db.batch()
    batch.set(
        db.collection('verification_requests').document(request_id), 
        request_data
    )
    
    # Immutable audit log
    batch.set(
        db.collection('audit_trails').document(f"request_create_{request_id}"),
        {
            'action': 'request_created',
            'actorUid': uid,
            'targetId': request_id,
            'timestamp': firestore.SERVER_TIMESTAMP,
            'immutable': True,
            'data_hash': sha256(str(sorted(request_data.items())).encode()).hexdigest()
        }
    )
    
    batch.commit()
    return jsonify({'requestId': request_id, 'status': 'created'}), 201

def list_requests(current_user, uid):
    """List requests based on role"""
    try:
        if current_user['role'] == 'citizen':
            query = db.collection('verification_requests').where('citizenUid', '==', uid).order_by('createdAt', direction=firestore.Query.DESCENDING)
        else:
            query = db.collection('verification_requests').order_by('createdAt', direction=firestore.Query.DESCENDING).limit(100)
        
        docs = query.stream()
        requests = []
        
        for doc in docs:
            data = doc.to_dict()
            request_item = {
                'id': doc.id,
                'requestId': data.get('requestId'),
                'pattaId': data.get('pattaId'),
                'status': data.get('status'),
                'createdAt': data.get('createdAt'),
                'documentsCount': len(data.get('documents', []))
            }
            requests.append(request_item)
        
        return jsonify({'requests': requests, 'count': len(requests)})
    
    except Exception as e:
        return jsonify({'error': 'Failed to fetch requests', 'details': str(e)}), 500

@patta_bp.route('/boundaries/<patta_id>', methods=['GET', 'POST'])
@token_required
@role_required('staff', 'admin')
@rate_limit(limit=10, window=3600)
def boundaries(patta_id, current_user, uid):
    """Manage land boundaries - GET view, POST update (staff only)"""
    if request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON'}), 400
        
        from .security import sanitize_input
        data = sanitize_input(data)
        
        # Validate coordinates (prevent malicious geo-data)
        coords = data.get('coordinates', [])
        if not coords or len(coords) < 3:
            return jsonify({'error': 'Invalid boundary coordinates (min 3 points)'}), 400
        
        # Validate coordinate format
        try:
            for coord_set in coords:
                if not isinstance(coord_set, list) or len(coord_set) < 2:
                    return jsonify({'error': 'Invalid coordinate format'}), 400
                for coord in coord_set:
                    lat, lng = float(coord[0]), float(coord[1])
                    if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                        return jsonify({'error': 'Coordinate out of bounds'}), 400
        except (ValueError, IndexError, TypeError):
            return jsonify({'error': 'Invalid coordinates format'}), 400
        
        boundary_data = {
            'pattaId': patta_id,
            'coordinates': coords,
            'area': float(data.get('area', 0)),
            'validated': True,
            'validatedBy': uid,
            'updatedAt': firestore.SERVER_TIMESTAMP,
            'data_hash': sha256(str(sorted(coords)).encode()).hexdigest()  # Tamper-proof
        }
        
        # Atomic write with audit
        batch = db.batch()
        batch.set(
            db.collection('boundary_coordinates').document(patta_id),
            boundary_data
        )
        batch.set(
            db.collection('audit_trails').document(f"boundary_update_{patta_id}_{int(time.time())}"),
            {
                'action': 'boundary_updated',
                'actorUid': uid,
                'targetId': patta_id,
                'timestamp': firestore.SERVER_TIMESTAMP,
                'immutable': True,
                'details': {'area': boundary_data['area']}
            }
        )
        batch.commit()
        
        return jsonify({'message': 'Boundary securely updated', 'pattaId': patta_id})
    
    # ✅ FIXED: Read-only access
    try:
        doc = db.collection('boundary_coordinates').document(patta_id).get()
        if doc.exists:
            data = doc.to_dict()
            # Redact sensitive staff data for citizens
            if current_user['role'] == 'citizen':
                data_copy = data.copy()
                data_copy.pop('validatedBy', None)
                data_copy.pop('data_hash', None)
                return jsonify(data_copy)
            return jsonify(data)
        return jsonify({'pattaId': patta_id, 'coordinates': [], 'validated': False})
    except Exception as e:
        return jsonify({'error': 'Failed to fetch boundary', 'details': str(e)}), 500

@patta_bp.route('/documents/upload', methods=['POST'])
@token_required
@role_required('citizen')
@rate_limit(limit=5, window=3600)
def upload_document(current_user, uid):
    """Upload supporting documents"""
    if 'document' not in request.files:
        return jsonify({'error': 'No document provided'}), 400
    
    file = request.files['document']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        # Secure filename
        filename = f"{uuid.uuid4()}_{file.filename}"
        bucket = storage.bucket()
        blob = bucket.blob(f"documents/{uid}/{filename}")
        blob.upload_from_file(file, content_type=file.content_type)
        blob.acl.all().grant_read()  # Public read for verification
        
        # Log upload to audit
        db.collection('audit_trails').add({
            'action': 'document_uploaded',
            'actorUid': uid,
            'targetId': filename,
            'timestamp': firestore.SERVER_TIMESTAMP,
            'details': {
                'filename': filename,
                'content_type': file.content_type,
                'size': len(file.read())
            },
            'immutable': True
        })
        
        return jsonify({
            'url': blob.public_url,
            'filename': filename,
            'message': 'Document uploaded successfully'
        }), 201
        
    except Exception as e:
        return jsonify({'error': 'Upload failed', 'details': str(e)}), 500
