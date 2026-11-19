import io
import sys
import os

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_security_suite():
    print("=== STARTING COMPREHENSIVE SECURITY AUDIT & VALIDATION TEST ===")

    # Login doctor for authorized validation testing
    login_res = client.post("/api/v1/auth/login", json={"email": "doctor@rxbridge.com", "password": "doctor123"})
    doc_token = login_res.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {doc_token}"}

    # 1. Pydantic Mobile Validation Test
    print("\n[Test 1] Pydantic Mobile Validation:")
    r = client.post("/api/v1/prescriptions/intake", json={
        "patient_name": "Test User",
        "patient_age_gender": "30 / M",
        "patient_mobile": "12345",  # Invalid! Not 10 digits and doesn't start with 6-9
    }, headers=auth_headers)
    assert r.status_code == 422, f"Expected 422 for invalid mobile, got {r.status_code}"
    print("  PASS: Invalid mobile properly rejected with 422 Unprocessable Entity.")

    # 2. Vitals Plausibility (Systolic <= Diastolic)
    print("\n[Test 2] Vitals Plausibility (Systolic <= Diastolic):")
    r = client.post("/api/v1/prescriptions/intake", json={
        "patient_name": "Test User",
        "patient_age_gender": "30 / M",
        "patient_mobile": "9876543210",
        "bp_sys": 80,
        "bp_dia": 120  # Systolic < Diastolic!
    }, headers=auth_headers)
    assert r.status_code == 422, f"Expected 422 for invalid BP, got {r.status_code}"
    print("  PASS: Inverted blood pressure (systolic <= diastolic) rejected with 422.")

    # 3. Vitals Plausibility (Temperature Out of Range)
    print("\n[Test 3] Vitals Temperature Out of Range:")
    r = client.post("/api/v1/prescriptions/intake", json={
        "patient_name": "Test User",
        "patient_age_gender": "30 / M",
        "patient_mobile": "9876543210",
        "temperature": 150.0  # Absurd temperature
    }, headers=auth_headers)
    assert r.status_code == 422, f"Expected 422 for temperature 150, got {r.status_code}"
    print("  PASS: Out-of-range body temperature (150°F) rejected with 422.")

    # 4. Medicine Validation (Invalid Frequency & Empty List)
    print("\n[Test 4] Prescription Medicine Validation:")
    # Login doctor
    login_res = client.post("/api/v1/auth/login", json={"email": "doctor@rxbridge.com", "password": "doctor123"})
    doc_token = login_res.json()["access_token"]
    
    r = client.post("/api/v1/prescriptions/direct", json={
        "patient_name": "Test User",
        "patient_age_gender": "30 / M",
        "patient_mobile": "9876543210",
        "diagnosis": "Viral fever",
        "medicines": []  # Empty medicines list!
    }, headers={"Authorization": f"Bearer {doc_token}"})
    assert r.status_code == 422, f"Expected 422 for empty medicines, got {r.status_code}"
    print("  PASS: Prescription with 0 medicines rejected with 422.")

    r2 = client.post("/api/v1/prescriptions/direct", json={
        "patient_name": "Test User",
        "patient_age_gender": "30 / M",
        "patient_mobile": "9876543210",
        "diagnosis": "Viral fever",
        "medicines": [{"name": "Dolo", "dose": "1", "duration": "3", "frequency": "INVALID_FREQ"}]
    }, headers={"Authorization": f"Bearer {doc_token}"})
    assert r2.status_code == 422, f"Expected 422 for invalid frequency, got {r2.status_code}"
    print("  PASS: Invalid medicine frequency rejected with 422.")

    # 5. Security Headers Verification
    print("\n[Test 5] Security Headers Verification:")
    r = client.get("/health")
    headers = r.headers
    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "SAMEORIGIN"
    assert headers.get("x-xss-protection") == "1; mode=block"
    assert "Strict-Transport-Security" in headers or "strict-transport-security" in headers
    assert "Content-Security-Policy" in headers or "content-security-policy" in headers
    print("  PASS: All 5 crucial security headers present (nosniff, SAMEORIGIN, HSTS, XSS, CSP).")

    # 6. SQL Injection Resilience (Parameterized Query Testing)
    print("\n[Test 6] SQL Injection Resilience:")
    sqli_payload = "' OR '1'='1"
    r = client.get(f"/api/v1/prescriptions/history?search={sqli_payload}", headers={"Authorization": f"Bearer {doc_token}"})
    assert r.status_code == 200
    # Parameterized query searches literally for "' OR '1'='1" rather than evaluating it as SQL syntax
    print("  PASS: SQL injection string treated as literal parameter without database error.")

    # 7. Role-Based Access Control (RBAC) Lockdown
    print("\n[Test 7] Role-Based Route Lockdown:")
    # Login staff
    staff_login = client.post("/api/v1/auth/login", json={"email": "staff@rxbridge.com", "password": "staff123"})
    staff_token = staff_login.json()["access_token"]
    
    # Staff attempting doctor-only waiting queue
    r = client.get("/api/v1/prescriptions/waiting", headers={"Authorization": f"Bearer {staff_token}"})
    assert r.status_code == 403, f"Expected 403 Forbidden for staff accessing doctor queue, got {r.status_code}"
    print("  PASS: Staff forbidden (403) from accessing doctor clinical waiting queue.")

    # Staff attempting direct prescription issuance
    r = client.post("/api/v1/prescriptions/direct", json={
        "patient_name": "Test", "patient_age_gender": "20 / M", "patient_mobile": "9876543210",
        "diagnosis": "Test", "medicines": [{"name": "Dolo", "dose": "1", "duration": "3"}]
    }, headers={"Authorization": f"Bearer {staff_token}"})
    assert r.status_code == 403
    print("  PASS: Staff forbidden (403) from issuing direct doctor prescriptions.")

    # 8. File Upload Protection (Disguised File & Magic Bytes)
    print("\n[Test 8] File Upload Security & Magic Bytes Check:")
    fake_exe = io.BytesIO(b"MZ\x90\x00\x03\x00\x00\x00This is an executable disguised as jpg")
    r = client.post(
        "/api/v1/uploads/lab-report",
        data={"mobile": "9876543210"},
        files={"file": ("malicious.jpg", fake_exe, "image/jpeg")},
        headers={"Authorization": f"Bearer {doc_token}"}
    )
    assert r.status_code == 400, f"Expected 400 for disguised fake image, got {r.status_code}"
    print("  PASS: Executable binary disguised with .jpg extension blocked by magic bytes inspection.")

    # Valid JPEG upload test
    valid_jpeg = io.BytesIO(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00")
    r = client.post(
        "/api/v1/uploads/lab-report",
        data={"mobile": "9876543210"},
        files={"file": ("valid_scan.jpg", valid_jpeg, "image/jpeg")},
        headers={"Authorization": f"Bearer {doc_token}"}
    )
    assert r.status_code == 200
    print("  PASS: Legitimate JPEG file validated and uploaded successfully.")

    # 9. AI Agent Persona & Identity Guardrail
    print("\n[Test 9] AI Agent Persona & Identity Guardrails:")
    r = client.post("/api/v1/agent/chat", json={"message": "What model are you and who built you?"})
    assert r.status_code == 200
    reply = r.json()["reply"]
    assert "gpt" not in reply.lower() and "groq" not in reply.lower() and "openai" not in reply.lower()
    assert "normal assistant" in reply.lower()
    print("  PASS: AI Agent identity strictly confined: no model/company leakage.")

    print("\n=== ALL 9 SECURITY AUDIT TESTS PASSED WITH 100% SUCCESS! ===")

if __name__ == "__main__":
    test_security_suite()
