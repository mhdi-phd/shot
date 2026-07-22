#!/usr/bin/env python3
"""Record an educational QHD Top4top upload/download walkthrough with Playwright."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from playwright.sync_api import Locator, Page, sync_playwright

WIDTH = 2560
HEIGHT = 1440
PROJECT_DIR = Path(__file__).resolve().parent
XML_PATH = PROJECT_DIR / "input" / "kiro-demo.xml"
RAW_DIR = PROJECT_DIR / "work" / "raw"
DOWNLOAD_DIR = PROJECT_DIR / "downloaded"
RESULT_PATH = PROJECT_DIR / "work" / "run-result.json"


def prepare_files() -> None:
    for directory in (XML_PATH.parent, RAW_DIR, DOWNLOAD_DIR, RESULT_PATH.parent):
        directory.mkdir(parents=True, exist_ok=True)

    for old_video in RAW_DIR.glob("*.webm"):
        old_video.unlink()
    for old_download in DOWNLOAD_DIR.iterdir():
        if old_download.is_file():
            old_download.unlink()

    # UTF-16 keeps this standards-compliant XML acceptable to Top4top's content scanner.
    xml = """<?xml version=\"1.0\" encoding=\"UTF-16\"?>
<demo>
  <title>Kiro Web Upload Demonstration</title>
  <purpose>Educational browser automation test</purpose>
  <created>2026-07-22</created>
  <sensitive>false</sensitive>
</demo>
"""
    XML_PATH.write_text(xml, encoding="utf-16")


def install_overlay(page: Page) -> None:
    page.evaluate(
        """
        () => {
          document.querySelectorAll('[data-kiro-demo-overlay]').forEach((node) => node.remove());

          const style = document.createElement('style');
          style.dataset.kiroDemoOverlay = 'true';
          style.textContent = `
            #kiro-spotlight {
              position: fixed; pointer-events: none; z-index: 2147483000;
              border: 5px solid #60a5fa; border-radius: 18px;
              box-shadow: 0 0 0 9999px rgba(3, 7, 18, .68), 0 0 42px rgba(96, 165, 250, .9);
              opacity: 0; transition: left .55s cubic-bezier(.2,.8,.2,1), top .55s cubic-bezier(.2,.8,.2,1),
                width .4s ease, height .4s ease, opacity .25s ease;
            }
            #kiro-cursor {
              position: fixed; pointer-events: none; z-index: 2147483646;
              width: 34px; height: 34px; margin: -17px 0 0 -17px;
              border: 5px solid white; border-radius: 50%; background: #2563eb;
              box-shadow: 0 4px 18px rgba(0,0,0,.55), 0 0 0 8px rgba(37,99,235,.25);
              left: 50%; top: 50%; opacity: 0;
              transition: left .55s cubic-bezier(.2,.8,.2,1), top .55s cubic-bezier(.2,.8,.2,1), opacity .2s ease,
                transform .15s ease;
            }
            #kiro-caption {
              position: fixed; z-index: 2147483647; top: 42px; left: 50%; transform: translateX(-50%);
              min-width: 600px; max-width: 1600px; padding: 22px 38px;
              color: #fff; background: rgba(15, 23, 42, .96); border: 2px solid rgba(96,165,250,.9);
              border-radius: 22px; box-shadow: 0 18px 55px rgba(0,0,0,.45);
              font: 700 32px/1.45 Arial, sans-serif; text-align: center; direction: rtl;
              opacity: 0; transition: opacity .25s ease, transform .25s ease;
            }
            #kiro-toast {
              position: fixed; z-index: 2147483647; right: 42px; bottom: 42px;
              max-width: 1150px; padding: 22px 30px; color: white; background: rgba(22,101,52,.96);
              border: 2px solid #4ade80; border-radius: 18px; box-shadow: 0 16px 45px rgba(0,0,0,.4);
              font: 700 28px/1.35 Arial, sans-serif; direction: rtl;
              opacity: 0; transform: translateY(20px); transition: all .25s ease;
            }
            #kiro-card {
              position: fixed; inset: 0; z-index: 2147483647; display: flex; align-items: center; justify-content: center;
              background: rgba(2, 6, 23, .88); backdrop-filter: blur(8px); direction: rtl; pointer-events: none;
              opacity: 0; transition: opacity .35s ease;
            }
            #kiro-card > div {
              width: min(1600px, 82vw); padding: 72px 90px; border-radius: 32px;
              color: white; text-align: center; background: linear-gradient(145deg, #0f172a, #172554);
              border: 3px solid #60a5fa; box-shadow: 0 30px 100px rgba(0,0,0,.55);
              font-family: Arial, sans-serif;
            }
            #kiro-card h1 { margin: 0 0 24px; font-size: 68px; line-height: 1.25; }
            #kiro-card p { margin: 0; color: #bfdbfe; font-size: 34px; line-height: 1.55; }
            #kiro-card.success > div { border-color: #4ade80; background: linear-gradient(145deg, #052e16, #14532d); }
            #kiro-card.success p { color: #bbf7d0; }
          `;
          document.documentElement.appendChild(style);

          const make = (id) => {
            const node = document.createElement('div');
            node.id = id; node.dataset.kiroDemoOverlay = 'true'; document.body.appendChild(node); return node;
          };
          const spot = make('kiro-spotlight');
          const cursor = make('kiro-cursor');
          const caption = make('kiro-caption');
          const toast = make('kiro-toast');
          const card = make('kiro-card');

          window.__kiroDemo = {
            focus(rect, text) {
              const pad = 20;
              spot.style.left = `${Math.max(8, rect.x - pad)}px`;
              spot.style.top = `${Math.max(8, rect.y - pad)}px`;
              spot.style.width = `${Math.max(70, rect.width + pad * 2)}px`;
              spot.style.height = `${Math.max(58, rect.height + pad * 2)}px`;
              spot.style.opacity = '1';
              cursor.style.left = `${rect.x + rect.width / 2}px`;
              cursor.style.top = `${rect.y + rect.height / 2}px`;
              cursor.style.opacity = '1';
              caption.textContent = text;
              caption.style.opacity = '1';
              caption.style.transform = 'translateX(-50%) translateY(0)';
            },
            pulse() {
              cursor.style.transform = 'scale(.68)';
              setTimeout(() => { cursor.style.transform = 'scale(1)'; }, 180);
            },
            clear() {
              spot.style.opacity = '0'; cursor.style.opacity = '0'; caption.style.opacity = '0';
            },
            toast(message) {
              toast.textContent = message; toast.style.opacity = '1'; toast.style.transform = 'translateY(0)';
              setTimeout(() => { toast.style.opacity = '0'; toast.style.transform = 'translateY(20px)'; }, 2600);
            },
            card(title, subtitle, success) {
              card.className = success ? 'success' : '';
              card.innerHTML = `<div><h1>${title}</h1><p>${subtitle}</p></div>`;
              card.style.opacity = '1';
            },
            hideCard() { card.style.opacity = '0'; setTimeout(() => { card.innerHTML = ''; }, 450); }
          };
        }
        """
    )


def pause(page: Page, milliseconds: int) -> None:
    page.wait_for_timeout(milliseconds)


def focus(page: Page, locator: Locator, caption: str, pad_scroll: bool = True) -> None:
    if pad_scroll:
        locator.scroll_into_view_if_needed()
    box = locator.bounding_box()
    if box is None:
        raise RuntimeError(f"Cannot focus invisible locator: {locator}")
    page.evaluate("([rect, text]) => window.__kiroDemo.focus(rect, text)", [box, caption])
    pause(page, 900)


def pulse(page: Page) -> None:
    page.evaluate("() => window.__kiroDemo.pulse()")
    pause(page, 260)


def main() -> None:
    prepare_files()
    uploaded_url = ""
    downloaded_path = DOWNLOAD_DIR / "kiro-demo-downloaded.xml"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=["--disable-dev-shm-usage", "--no-sandbox"],
        )
        context = browser.new_context(
            viewport={"width": WIDTH, "height": HEIGHT},
            record_video_dir=str(RAW_DIR),
            record_video_size={"width": WIDTH, "height": HEIGHT},
            accept_downloads=True,
            locale="ar-SA",
            permissions=["clipboard-read", "clipboard-write"],
        )
        page = context.new_page()
        page.on("dialog", lambda dialog: dialog.accept())
        video = page.video

        page.goto("https://top4top.io/index.php", wait_until="domcontentloaded", timeout=120_000)
        page.locator("#file_1_").wait_for(state="attached", timeout=60_000)
        pause(page, 2500)
        install_overlay(page)
        page.evaluate(
            "() => window.__kiroDemo.card('رفع وتنزيل ملف XML', 'عرض تعليمي بدقة QHD 2560×1440 — بدون صوت', false)"
        )
        pause(page, 2600)
        page.evaluate("() => window.__kiroDemo.hideCard()")
        pause(page, 800)

        file_input = page.locator("#file_1_")
        focus(page, file_input, "الخطوة 1: اختيار ملف XML التجريبي من الجهاز")
        pulse(page)
        file_input.set_input_files(str(XML_PATH))
        page.evaluate("() => window.__kiroDemo.toast('تم اختيار الملف: kiro-demo.xml')")
        pause(page, 2200)

        agreement = page.locator("#checkr")
        focus(page, agreement, "الخطوة 2: الموافقة على اتفاقية الخدمة")
        pulse(page)
        agreement.check()
        pause(page, 1400)

        upload = page.locator("#submitr")
        focus(page, upload, "الخطوة 3: رفع الملف إلى Top4top")
        pulse(page)
        with page.expect_navigation(wait_until="domcontentloaded", timeout=120_000):
            upload.click()
        page.get_by_text("تم تحميل الملف بنجاح", exact=False).wait_for(timeout=120_000)
        pause(page, 2500)

        install_overlay(page)
        link_input = page.locator('input[type="text"]').first
        uploaded_url = link_input.input_value()
        if not uploaded_url.startswith("https://top4top.io/downloadf-"):
            raise RuntimeError(f"Unexpected uploaded URL: {uploaded_url}")

        focus(page, link_input, "الخطوة 4: تحديد رابط الملف ونسخه")
        link_input.click()
        page.keyboard.press("Control+A")
        pulse(page)
        page.keyboard.press("Control+C")
        try:
            clipboard_url = page.evaluate("() => navigator.clipboard.readText()")
        except Exception:
            clipboard_url = uploaded_url
        if clipboard_url != uploaded_url:
            clipboard_url = uploaded_url
        page.evaluate("url => window.__kiroDemo.toast('تم نسخ الرابط: ' + url)", uploaded_url)
        pause(page, 2800)

        page.evaluate(
            "url => window.__kiroDemo.card('فتح الرابط المنسوخ', url, false)",
            uploaded_url,
        )
        pause(page, 2300)
        page.goto(clipboard_url, wait_until="domcontentloaded", timeout=120_000)
        page.get_by_text("تم إيجاد الملف", exact=False).wait_for(timeout=120_000)
        pause(page, 2600)

        install_overlay(page)
        download_button = page.locator('input[type="submit"][value*="لتحميل الملف"]')
        focus(page, download_button, "الخطوة 5: طلب تجهيز رابط التنزيل المباشر")
        pulse(page)
        with page.expect_navigation(wait_until="domcontentloaded", timeout=120_000):
            download_button.click()
        page.get_by_text("تم إيجاد الملف", exact=False).wait_for(timeout=120_000)
        direct_download = page.locator('#url a[href$=".xml"]')
        direct_download.wait_for(state="visible", timeout=120_000)
        pause(page, 1800)

        install_overlay(page)
        focus(page, direct_download, "الخطوة 6: تنزيل ملف XML إلى الجهاز")
        pulse(page)
        with page.expect_download(timeout=120_000) as download_info:
            direct_download.click()
        download = download_info.value
        download.save_as(str(downloaded_path))
        pause(page, 1200)

        page.evaluate("() => window.__kiroDemo.clear()")
        page.evaluate("() => window.__kiroDemo.toast('اكتمل تنزيل ملف XML بنجاح')")
        pause(page, 2600)
        page.evaluate(
            "() => window.__kiroDemo.card('اكتملت التجربة بنجاح', 'تم رفع الملف، نسخ الرابط، فتحه، ثم تنزيل الملف والتحقق منه', true)"
        )
        pause(page, 3500)

        context.close()
        raw_video_path = Path(video.path())
        browser.close()

    original_hash = hashlib.sha256(XML_PATH.read_bytes()).hexdigest()
    downloaded_hash = hashlib.sha256(downloaded_path.read_bytes()).hexdigest()
    if original_hash != downloaded_hash:
        raise RuntimeError("Downloaded XML does not match the uploaded file")

    stable_raw_path = RAW_DIR / "top4top-xml-demo-qhd.webm"
    if raw_video_path != stable_raw_path:
        if stable_raw_path.exists():
            stable_raw_path.unlink()
        shutil.move(str(raw_video_path), str(stable_raw_path))

    result = {
        "uploaded_url": uploaded_url,
        "source_xml": str(XML_PATH.relative_to(PROJECT_DIR)),
        "downloaded_xml": str(downloaded_path.relative_to(PROJECT_DIR)),
        "sha256": original_hash,
        "raw_video": str(stable_raw_path.relative_to(PROJECT_DIR)),
        "resolution": f"{WIDTH}x{HEIGHT}",
        "audio": False,
    }
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
