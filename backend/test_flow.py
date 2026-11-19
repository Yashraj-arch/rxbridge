import sys
import os

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def run_tests():
    # 1. Staff Login
    r = client.post('/api/v1/auth/login', json={'email': 'staff@rxbridge.com', 'password': 'staff123'})
    assert r.status_code == 200, f'Staff login failed: {r.text}'
    staff_token = r.json()['access_token']
    print('1. Staff logged in successfully')

    # 2. Staff creates Intake
    intake_data = {
        'patient_name': 'Ramesh Kumar',
        'patient_age_gender': '45 / M',
        'patient_mobile': '9876543210',
        'patient_weight': 72.0,
        'diagnosis': 'Severe cough, body ache, fever for 2 days',
        'bp_sys': 130,
        'bp_dia': 85,
        'pulse': 82,
        'temperature': 100.2,
        'spo2': 97,
        'respiratory_rate': 18,
        'height': 170.0,
        'bmi': 24.9,
        'blood_sugar': 110,
        'sugar_type': 'Random',
        'consent_offers': True,
        'consent_refill': True
    }
    r = client.post('/api/v1/prescriptions/intake', json=intake_data, headers={'Authorization': f'Bearer {staff_token}'})
    assert r.status_code == 201, f'Intake failed: {r.text}'
    rx_intake = r.json()
    rx_id = rx_intake['id']
    rx_number = rx_intake['rx_number']
    print(f"2. Intake created: ID {rx_id}, RxNo {rx_number}, Status: {rx_intake['status']}")

    # 3. Doctor Login
    r = client.post('/api/v1/auth/login', json={'email': 'doctor@rxbridge.com', 'password': 'doctor123'})
    assert r.status_code == 200, f'Doctor login failed: {r.text}'
    doc_token = r.json()['access_token']
    print('3. Doctor logged in successfully')

    # 4. Doctor checks Waiting Queue
    r = client.get('/api/v1/prescriptions/waiting', headers={'Authorization': f'Bearer {doc_token}'})
    assert r.status_code == 200
    waiting_list = r.json()
    assert any(item['id'] == rx_id for item in waiting_list)
    print(f'4. Doctor waiting queue has {len(waiting_list)} patient(s), found intake {rx_id}')

    # 5. Doctor completes prescription
    rx_complete_data = {
        'diagnosis': 'Acute Upper Respiratory Tract Infection (URTI)',
        'medicines': [
            {'name': 'Augmentin 625', 'dose': '1 tab', 'duration': '5 days', 'frequency': 'BD', 'food_relation': 'After food', 'timing': ['morning', 'evening']},
            {'name': 'Dolo 650', 'dose': '1 tab', 'duration': '3 days', 'frequency': 'TDS', 'food_relation': 'After food', 'timing': ['morning', 'afternoon', 'evening']},
            {'name': 'Montair LC', 'dose': '1 tab', 'duration': '5 days', 'frequency': 'HS', 'food_relation': 'Before food', 'timing': ['evening']}
        ],
        'advice': 'Drink warm fluids, steam inhalation twice daily, adequate rest.',
        'follow_up_date': 'After 5 days'
    }
    r = client.post(f'/api/v1/prescriptions/{rx_id}/complete', json=rx_complete_data, headers={'Authorization': f'Bearer {doc_token}'})
    assert r.status_code == 200, f'Complete failed: {r.text}'
    completed_rx = r.json()
    print(f"5. Doctor completed Rx: {completed_rx['rx_number']}, Status: {completed_rx['status']}")

    # 6. Pharmacy Login
    r = client.post('/api/v1/auth/login', json={'email': 'pharmacy@rxbridge.com', 'password': 'pharmacy123'})
    assert r.status_code == 200, f'Pharmacy login failed: {r.text}'
    pharm_token = r.json()['access_token']
    print('6. Pharmacy logged in successfully')

    # 7. Pharmacy lists consented prescriptions
    r = client.get('/api/v1/pharmacy/prescriptions', headers={'Authorization': f'Bearer {pharm_token}'})
    assert r.status_code == 200
    pharm_list = r.json()
    assert any(item['id'] == rx_id for item in pharm_list)
    print(f'7. Pharmacy sees {len(pharm_list)} consented prescription(s)')

    # 8. Pharmacy marks as dispensed
    r = client.post(f'/api/v1/pharmacy/prescriptions/{rx_id}/dispense', headers={'Authorization': f'Bearer {pharm_token}'})
    assert r.status_code == 200
    dispensed_rx = r.json()
    print(f"8. Pharmacy marked dispensed: Status: {dispensed_rx['status']}")

    # 9. Public Verification
    r = client.get(f'/api/v1/verify/{rx_number}')
    assert r.status_code == 200
    verify_res = r.json()
    print(f"9. Public Verification result: Valid={verify_res['valid']}, Rx={verify_res['rxNumber']}, Doctor={verify_res['doctorName']}")

    print('\n*** ALL 9 INTEGRATION TESTS PASSED PERFECTLY! ***')

if __name__ == '__main__':
    run_tests()
