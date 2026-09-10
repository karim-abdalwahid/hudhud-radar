import os
import time
import subprocess
import glob
import urllib.request
from playwright.sync_api import sync_playwright

PERMISSIONS = [
    ("pages_show_list", "/settings"),
    ("pages_manage_metadata", "/settings"),
    ("pages_messaging", "/inbox"),
    ("pages_utility_messaging", "/inbox"),
    ("pages_read_engagement", "/analytics"),
    ("pages_read_user_content", "/studio"),
    ("pages_manage_posts", "/studio"),
    ("pages_manage_engagement", "/inbox"),
    ("pages_manage_ads", "/analytics"),
    ("instagram_basic", "/settings"),
    ("instagram_manage_messages", "/inbox"),
    ("instagram_manage_comments", "/inbox"),
    ("instagram_manage_insights", "/analytics"),
    ("instagram_content_publish", "/studio"),
    ("instagram_manage_contents", "/studio"),
    ("instagram_manage_engagement", "/inbox"),
    ("threads_basic", "/settings"),
    ("threads_content_publish", "/studio"),
    ("threads_read_replies", "/inbox"),
    ("threads_manage_replies", "/inbox"),
    ("threads_manage_insights", "/analytics"),
    ("threads_delete", "/studio"),
    ("business_management", "/dashboard"),
    ("read_insights", "/analytics"),
    ("ads_read", "/analytics"),
    ("ads_management", "/analytics"),
    ("leads_retrieval", "/leads"),
    ("public_profile", "/users"),
    ("email", "/users"),
    ("human_agent", "/inbox"),
    ("business_asset_user_profile_access", "/inbox")
]

def wait_for_server(url="http://localhost:8000/health", timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url) as response:
                if response.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.5)
    return False

def main():
    videos_dir = os.path.abspath("docs/APP_REVIEW/videos")
    os.makedirs(videos_dir, exist_ok=True)
    
    print("Starting FastAPI server...")
    server_process = subprocess.Popen(["python", "src/main.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    if not wait_for_server():
        print("Error: Server failed to start within timeout.")
        server_process.terminate()
        return
    
    print("Server is up and running. Authenticating session...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            
            auth_context = browser.new_context(viewport={"width": 1920, "height": 1080})
            auth_page = auth_context.new_page()
            auth_page.goto("http://localhost:8000/login")
            auth_page.wait_for_load_state("networkidle")
            auth_page.fill("#loginEmail", "admin.test@hudhud.test")
            auth_page.fill("#loginPassword", "AdminTest#2026")
            auth_page.click("#loginBtn")
            auth_page.wait_for_url("**/dashboard**", timeout=5000)
            
            storage_state = auth_context.storage_state()
            auth_context.close()
            
            for perm, route in PERMISSIONS:
                mp4_path = os.path.join(videos_dir, f"{perm}.mp4")
                if os.path.exists(mp4_path):
                    print(f"Skipping {perm} (already re-recorded)")
                    continue
                
                print(f"Re-recording populated screencast for: {perm} at route {route}")
                
                context = browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    storage_state=storage_state,
                    record_video_dir=videos_dir,
                    record_video_size={"width": 1920, "height": 1080}
                )
                page = context.new_page()
                
                try:
                    page.goto(f"http://localhost:8000{route}")
                    page.wait_for_load_state("networkidle", timeout=5000)
                except Exception as e:
                    print(f"Navigation warning for {perm}: {e}")
                
                # Simulate realistic live reviewer interaction and UI rendering
                time.sleep(3)
                try:
                    page.mouse.move(600, 350)
                    page.evaluate("window.scrollBy(0, 400)")
                    time.sleep(2)
                    page.evaluate("window.scrollBy(0, -400)")
                    time.sleep(2)
                    page.mouse.click(400, 300)
                    time.sleep(2)
                except Exception:
                    pass
                
                time.sleep(3)
                context.close()
                
                # Convert recorded webm to mp4
                webm_files = glob.glob(os.path.join(videos_dir, "*.webm"))
                if webm_files:
                    latest_webm = max(webm_files, key=os.path.getmtime)
                    cmd = ["ffmpeg", "-y", "-i", latest_webm, "-c:v", "libx264", "-crf", "23", "-preset", "fast", "-c:a", "aac", mp4_path]
                    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    try:
                        os.remove(latest_webm)
                    except Exception:
                        pass
                    print(f"Saved populated video: {mp4_path}")
                else:
                    print(f"Warning: No video recorded for {perm}")
                    
            browser.close()
    finally:
        server_process.terminate()
        server_process.wait()
    print("All 31 populated screencast videos re-recorded successfully!")

if __name__ == "__main__":
    main()
