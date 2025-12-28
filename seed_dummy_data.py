import firebase_admin
from firebase_admin import credentials, firestore
import random
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Tamil Nadu Realistic Locations
DISTRICTS = ['Chennai', 'Coimbatore', 'Madurai', 'Tiruchirappalli', 'Salem']
TALUKS = ['Egmore', 'Pollachi', 'Melur', 'Thiruporur', 'Gobichettypalayam']
VILLAGES = ['Koyambedu', 'Perungudi', 'Velachery', 'Anna Nagar', 'T. Nagar']

# Initialize Firebase
cred = credentials.Certificate(os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH'))
firebase_admin.initialize_app(cred)
db = firestore.client()

def seed_users():
    users = {}
    for role in ['citizen', 'staff', 'admin']:
        for i in range(1, 6):
            user_id = f"{role}_{i}"
            users[user_id] = {
                'email': f'{role}_{i}@patta.tn.gov.in',
                'role': role,
                'phone': f'9{random.randint(1000000000, 9999999999)}',
                'created_at': firestore.SERVER_TIMESTAMP
            }
            db.collection('users').document(user_id).set(users[user_id])
            print(f"👤 Created {user_id}")
    print("✅ 15 users created")
    return users

def seed_patta(users):
    for i in range(1, 51):
        ref_id = f"PATTA-{i:04d}"
        lat = 13.0827 + random.uniform(-0.005, 0.005)
        lng = 80.2707 + random.uniform(-0.005, 0.005)
        
        # ✅ FIXED: Flat array of coordinates (no nesting)
        boundary_points = []
        for _ in range(random.randint(4, 8)):
            boundary_points.append({
                'lat': lat + random.uniform(-0.0002, 0.0002),
                'lng': lng + random.uniform(-0.0002, 0.0002)
            })
        
        db.collection('patta').document(ref_id).set({
            'ref_id': ref_id,
            'user_id': random.choice(list(users.keys())),
            'district': random.choice(DISTRICTS),
            'taluk': random.choice(TALUKS),
            'village': random.choice(VILLAGES),
            'lat': round(lat, 10),
            'lng': round(lng, 10),
            'surveyNo': f"{random.randint(100, 999)}/{random.choice(['1A','2B','3C'])}",
            'subdivNo': random.randint(1, 4),
            'boundary': boundary_points,  # ✅ Flat array of objects
            'status': random.choices(['pending', 'approved', 'rejected'], weights=[0.6, 0.3, 0.1])[0],
            'submitted_at': firestore.SERVER_TIMESTAMP,
            'staff_notes': random.choice(['Verified', 'Field visit needed', ''])
        })
        if i % 10 == 0:
            print(f"📄 Created {i}/50 Patta applications")
    print("✅ 50 Patta applications created")

if __name__ == "__main__":
    print("🌱 Seeding Patta App data...")
    users = seed_users()
    seed_patta(users)
    print("🎉 Firebase ready for testing!")
    print("\n👤 Test users:")
    print("  Citizen: citizen_1@patta.tn.gov.in")
    print("  Staff:   staff_1@patta.tn.gov.in")
    print("  Admin:   admin_1@patta.tn.gov.in")
