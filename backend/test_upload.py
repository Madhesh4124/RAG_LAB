import os
import requests
import io

API_URL = "http://localhost:8000"

# Create a session to handle cookies
session = requests.Session()

# Login (Payload based on app/models/user.py UserLoginRequest)
# identifier is username or email
login_payload = {"identifier": "admin", "password": "change-me"}
response = session.post(f"{API_URL}/api/auth/login", json=login_payload)

if response.status_code != 200:
    print("Login failed:", response.status_code, response.text)
    exit(1)

print("Logged in!")

# Upload a small dummy PDF
# We need to make sure it looks like a PDF for the magic byte check
pdf_content = b"%PDF-1.4\n% \n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n2 0 obj\n<</Type/Pages/Count 1/Kids[3 0 R]>>\nendobj\n3 0 obj\n<</Type/Page/Parent 2 0 R/Resources<<>>/Contents 4 0 R>>\nendobj\n4 0 obj\n<</Length 10>>\nstream\nhello world\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000052 00000 n \n0000000101 00000 n \n0000000178 00000 n \ntrailer\n<</Size 5/Root 1 0 R>>\nstartxref\n242\n%%EOF"

files = {"file": ("test.pdf", pdf_content, "application/pdf")}
# The endpoint is /api/documents/upload
res = session.post(f"{API_URL}/api/documents/upload", files=files)

print("Upload status:", res.status_code)
print("Upload response:", res.text)
