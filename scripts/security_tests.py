import requests
import time
import os
import concurrent.futures

BASE_URL_BACKEND = "http://localhost:8000"
BASE_URL_FRONTEND = "http://localhost:3000"

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def log(status, message):
    color = GREEN if status == "PASS" else RED if status == "FAIL" else YELLOW
    print(f"[{color}{status}{RESET}] {message}")

def test_security_headers():
    print(f"\n--- Testing Security Headers ({BASE_URL_BACKEND}) ---")
    try:
        r = requests.get(f"{BASE_URL_BACKEND}/health")
        headers = r.headers
        
        checks = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'"
        }
        
        for header, expected in checks.items():
            if header in headers and expected in headers[header]:
                log("PASS", f"{header} is present and correct.")
            else:
                log("FAIL", f"{header} missing or incorrect. Got: {headers.get(header)}")
                
    except Exception as e:
        log("FAIL", f"Could not connect to backend: {e}")

def test_auth_protection():
    print(f"\n--- Testing Frontend Auth Protection ({BASE_URL_FRONTEND}) ---")
    protected_routes = ["/", "/history"]
    
    for route in protected_routes:
        try:
            # We don't follow redirects to see the 307/302
            r = requests.get(f"{BASE_URL_FRONTEND}{route}", allow_redirects=False)
            if r.status_code in [307, 302, 308] and "/auth/login" in r.headers.get("Location", ""):
                log("PASS", f"Route {route} redirects to login (Status: {r.status_code})")
            elif r.status_code == 200:
                # If it's 200, it MIGHT be the login page itself if Next.js did an internal rewrite
                # But typically middleware does a redirect.
                # Let's check content to see if it looks like a login page
                if "Sign in" in r.text or "Iniciar Sesión" in r.text:
                     log("PASS", f"Route {route} shows Login Page.")
                else:
                     log("FAIL", f"Route {route} accessible without auth! (Status: 200)")
            else:
                log("WARN", f"Route {route} returned status {r.status_code}")
        except Exception as e:
             log("FAIL", f"Could not connect to frontend: {e}")

def test_file_upload_security():
    print(f"\n--- Testing File Upload Security ---")
    upload_url = f"{BASE_URL_BACKEND}/api/v1/invoices/upload"
    
    # 1. Test Bad Extension
    try:
        files = {'file': ('malware.exe', b'bad_content', 'application/octet-stream')}
        r = requests.post(upload_url, files=files)
        if r.status_code == 400 and "extension" in r.text.lower():
            log("PASS", "Blocked .exe extension")
        else:
            log("FAIL", f"Allowed .exe extension! Status: {r.status_code}")
    except Exception as e: log("FAIL", f"Upload check failed: {e}")

    # 2. Test Fake Magic Bytes (PDF extension but bad content)
    try:
        files = {'file': ('fake.pdf', b'NOT A PDF', 'application/pdf')}
        r = requests.post(upload_url, files=files)
        # Assuming we implemented magic byte check
        if r.status_code == 400: # OR 500 if strict check fails hard
            log("PASS", "Blocked invalid Magic Bytes in .pdf")
        else:
            log("FAIL", f"Allowed fake .pdf! Status: {r.status_code}")
    except Exception as e: log("FAIL", f"Upload check failed: {e}")

    # 3. Test Valid File
    try:
        files = {'file': ('valid.xml', b'<invoice>test</invoice>', 'application/xml')}
        r = requests.post(upload_url, files=files)
        if r.status_code == 200:
            log("PASS", "Allowed valid .xml file")
        else:
            log("FAIL", f"Blocked valid .xml file! Status: {r.status_code} {r.text}")
    except Exception as e: log("FAIL", f"Upload check failed: {e}")

def run_load_test(n_requests=50):
    print(f"\n--- Running Mini Load Test ({n_requests} requests) ---")
    start_time = time.time()
    success_count = 0
    
    def make_request():
        try:
            return requests.get(f"{BASE_URL_BACKEND}/health").status_code
        except:
            return 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(lambda _: make_request(), range(n_requests)))
    
    success_count = results.count(200)
    duration = time.time() - start_time
    
    log("INFO", f"Completed {n_requests} requests in {duration:.2f}s")
    log("INFO", f"Success Rate: {(success_count/n_requests)*100:.1f}%")
    if success_count == n_requests:
        log("PASS", "Load test passed with 100% success")
    else:
        log("FAIL", "Load test had failures")

if __name__ == "__main__":
    print("Beginning VeriAgent Comprehensive Security Test Suite...")
    test_security_headers()
    test_auth_protection()
    test_file_upload_security()
    run_load_test(100)
    print("\nTest Suite Completed.")
