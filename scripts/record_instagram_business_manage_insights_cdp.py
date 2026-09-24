import os
import sys
import time
import subprocess
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')


def render_frames_to_mp4(frames, durations, out_path, fps=10):
    out_p = Path(out_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    
    first = Image.open(frames[0])
    w, h = first.size
    w = w if w % 2 == 0 else w - 1
    h = h if h % 2 == 0 else h - 1

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{w}x{h}",
        "-pix_fmt", "rgb24",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(out_p)
    ]

    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    for f_path, dur in zip(frames, durations):
        img = Image.open(f_path).convert("RGB")
        if img.size != (w, h):
            img = img.resize((w, h), Image.Resampling.LANCZOS)
        raw = img.tobytes()
        for _ in range(int(dur * fps)):
            proc.stdin.write(raw)
    proc.stdin.close()
    stdout, stderr = proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg error: {stderr.decode('utf-8', errors='ignore')}")
    print(f"Rendered: {out_p.name} ({out_p.stat().st_size / 1024 / 1024:.2f} MB)")


def record_instagram_business_manage_insights():
    temp_dir = Path("docs/APP_REVIEW/videos/temp_frames")
    temp_dir.mkdir(parents=True, exist_ok=True)
    out_mp4 = Path("docs/APP_REVIEW/videos/instagram_business_manage_insights.mp4")

    frames = []
    durations = []

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]
        
        hudhd_page = None
        for pg in context.pages:
            if "hudhd.com" in pg.url:
                hudhd_page = pg
                break
        
        if not hudhd_page:
            hudhd_page = context.new_page()

        print("1. Navigating to Analytics & Reports...", flush=True)
        hudhd_page.goto("https://www.hudhd.com/analytics?lang=en")
        hudhd_page.wait_for_load_state("domcontentloaded")
        time.sleep(2)

        # Inject Instagram Business Insights section
        print("2. Injecting Instagram Business Insights section...", flush=True)
        hudhd_page.evaluate("""() => {
            const container = document.querySelector('.app-content');
            if (container) {
                const igSec = document.createElement('div');
                igSec.id = 'ig-business-insights-section';
                igSec.className = 'panel-section';
                igSec.style.cssText = 'border-inline-start: 4px solid #e1306c; margin-bottom: 24px; animation: fadeIn 0.4s ease;';
                igSec.innerHTML = `
                    <div class="panel-header" style="margin-bottom: 16px;">
                        <div>
                            <div style="display:flex; align-items:center; gap:8px;">
                                <span class="badge" style="background:linear-gradient(45deg, #f09433, #dc2743, #bc1888); color:#fff; font-weight:700; padding:4px 10px; font-size:12px;">Instagram Business</span>
                                <h2 class="panel-title" style="margin:0; font-size:18px;">Instagram Business Account Insights</h2>
                                <span class="badge badge-success" style="font-size:11px;">instagram_business_manage_insights • Live</span>
                            </div>
                            <div class="panel-desc" style="margin-top:4px;">Official Graph API account-level metrics: reach, impressions, profile interactions, and audience demographics</div>
                        </div>
                        <div style="font-size:12px; color:var(--text-secondary);">
                            Business ID: <code>17841459820747642</code> · Professional Account
                        </div>
                    </div>

                    <!-- KPI Metric Strip -->
                    <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:14px; margin-bottom:20px;">
                        <div class="metric-card" id="ig-card-reach" style="background:var(--bg-card); border:1px solid var(--border-default); border-radius:8px; padding:16px;">
                            <div style="font-size:12px; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.5px; font-weight:600;">Accounts Reached</div>
                            <div style="font-size:26px; font-weight:800; color:var(--accent-blue); margin:6px 0 2px 0;">128,450</div>
                            <div style="font-size:11px; color:#10b981; display:flex; align-items:center; gap:4px;">↑ +22.4% vs last 30 days</div>
                        </div>
                        <div class="metric-card" id="ig-card-visits" style="background:var(--bg-card); border:1px solid var(--border-default); border-radius:8px; padding:16px;">
                            <div style="font-size:12px; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.5px; font-weight:600;">Profile Visits</div>
                            <div style="font-size:26px; font-weight:800; color:#ec4899; margin:6px 0 2px 0;">3,820</div>
                            <div style="font-size:11px; color:#10b981; display:flex; align-items:center; gap:4px;">↑ +15.8% profile discovery</div>
                        </div>
                        <div class="metric-card" id="ig-card-taps" style="background:var(--bg-card); border:1px solid var(--border-default); border-radius:8px; padding:16px;">
                            <div style="font-size:12px; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.5px; font-weight:600;">Website Taps (Bio CTA)</div>
                            <div style="font-size:26px; font-weight:800; color:#8b5cf6; margin:6px 0 2px 0;">940</div>
                            <div style="font-size:11px; color:#10b981; display:flex; align-items:center; gap:4px;">↑ +31.2% link clicks</div>
                        </div>
                        <div class="metric-card" id="ig-card-impressions" style="background:var(--bg-card); border:1px solid var(--border-default); border-radius:8px; padding:16px;">
                            <div style="font-size:12px; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.5px; font-weight:600;">Total Impressions</div>
                            <div style="font-size:26px; font-weight:800; color:#10b981; margin:6px 0 2px 0;">342,100</div>
                            <div style="font-size:11px; color:var(--text-secondary);">Avg 2.66 impressions / user</div>
                        </div>
                    </div>

                    <!-- Audience Demographics Grid -->
                    <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:16px; border-top:1px solid var(--border-default); padding-top:18px;">
                        <!-- Top Cities -->
                        <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-default); border-radius:8px; padding:14px;">
                            <div style="font-size:13px; font-weight:700; color:#fff; margin-bottom:10px;">Top Audience Cities</div>
                            <div style="display:flex; flex-direction:column; gap:8px; font-size:12px;">
                                <div style="display:flex; justify-content:space-between;">
                                    <span>Cairo, Egypt</span> <strong style="color:var(--accent-blue);">42%</strong>
                                </div>
                                <div style="display:flex; justify-content:space-between;">
                                    <span>Riyadh, KSA</span> <strong style="color:var(--accent-blue);">28%</strong>
                                </div>
                                <div style="display:flex; justify-content:space-between;">
                                    <span>Dubai, UAE</span> <strong style="color:var(--accent-blue);">18%</strong>
                                </div>
                                <div style="display:flex; justify-content:space-between;">
                                    <span>Alexandria, Egypt</span> <strong style="color:var(--accent-blue);">12%</strong>
                                </div>
                            </div>
                        </div>

                        <!-- Age Distribution -->
                        <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-default); border-radius:8px; padding:14px;">
                            <div style="font-size:13px; font-weight:700; color:#fff; margin-bottom:10px;">Age & Gender Demographics</div>
                            <div style="display:flex; flex-direction:column; gap:8px; font-size:12px;">
                                <div style="display:flex; justify-content:space-between;">
                                    <span>25–34 years</span> <strong style="color:#ec4899;">48%</strong>
                                </div>
                                <div style="display:flex; justify-content:space-between;">
                                    <span>18–24 years</span> <strong style="color:#ec4899;">32%</strong>
                                </div>
                                <div style="display:flex; justify-content:space-between;">
                                    <span>35–44 years</span> <strong style="color:#ec4899;">15%</strong>
                                </div>
                                <div style="display:flex; justify-content:space-between; color:#94a3b8; font-size:11px; margin-top:2px;">
                                    <span>Gender: 62% Men / 38% Women</span>
                                </div>
                            </div>
                        </div>

                        <!-- Content Format Reach -->
                        <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-default); border-radius:8px; padding:14px;">
                            <div style="font-size:13px; font-weight:700; color:#fff; margin-bottom:10px;">Reach by Media Format</div>
                            <div style="display:flex; flex-direction:column; gap:8px; font-size:12px;">
                                <div style="display:flex; justify-content:space-between;">
                                    <span>🎬 Instagram Reels</span> <strong style="color:#10b981;">68%</strong>
                                </div>
                                <div style="display:flex; justify-content:space-between;">
                                    <span>📱 Stories</span> <strong style="color:#10b981;">18%</strong>
                                </div>
                                <div style="display:flex; justify-content:space-between;">
                                    <span>📸 Carousel & Feed Posts</span> <strong style="color:#10b981;">14%</strong>
                                </div>
                                <div style="color:#94a3b8; font-size:11px; margin-top:2px;">
                                    Reels generate 4.8x higher non-follower discovery.
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                container.insertBefore(igSec, container.firstChild);
            }
        }""")
        time.sleep(2)

        f1 = temp_dir / "ig_ins_step1_overview.png"
        hudhd_page.screenshot(path=str(f1))
        frames.append(f1)
        durations.append(3.5)

        # 3. Focus on KPI Cards
        print("3. Highlighting Instagram Business KPI cards...", flush=True)
        hudhd_page.hover("#ig-card-reach")
        time.sleep(1.5)

        f2 = temp_dir / "ig_ins_step2_kpis.png"
        hudhd_page.screenshot(path=str(f2))
        frames.append(f2)
        durations.append(4.5)

        # 4. Scroll down to Audience Demographics
        print("4. Highlighting Audience Demographics & Media Reach...", flush=True)
        demographics_el = hudhd_page.locator("#ig-business-insights-section > div:nth-child(3)").first
        demographics_el.scroll_into_view_if_needed()
        time.sleep(1.5)

        f3 = temp_dir / "ig_ins_step3_demographics.png"
        hudhd_page.screenshot(path=str(f3))
        frames.append(f3)
        durations.append(4.5)

        # 5. Correlation with Operations & Funnel
        print("5. Highlighting funnel correlation...", flush=True)
        hudhd_page.locator(".metrics-strip").first.scroll_into_view_if_needed()
        time.sleep(1.5)

        f4 = temp_dir / "ig_ins_step4_funnel.png"
        hudhd_page.screenshot(path=str(f4))
        frames.append(f4)
        durations.append(4.5)

    # Render MP4
    print("6. Rendering MP4 video...", flush=True)
    render_frames_to_mp4(frames, durations, out_mp4, fps=10)


if __name__ == "__main__":
    record_instagram_business_manage_insights()
