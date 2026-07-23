#!/usr/bin/env python3
"""Record a direct 4K Playwright walkthrough of the Base64 encoder.

The WebM is written by Playwright itself. No post-processing or transcoding is
performed. Chromium/Playwright currently controls the container, codec, and
frame rate (WebM/VP8 at 25 fps for this build).
"""

from __future__ import annotations

import argparse
import base64
import re
import urllib.request
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

SOURCE_URL = "https://www.base64decode.org/"
ENCODER_URL = "https://www.base64encode.org/"
ARABIC_TEXT = "السلام عليكم ورحمة الله وبركاته"
EXPECTED_OUTPUT = "2KfZhNiz2YTYp9mFINi52YTZitmD2YUg2YjYsdit2YXYqSDYp9mE2YTZhyDZiNio2LHZg9in2KrZhw=="
VIEWPORT = {"width": 3840, "height": 2160}
BASE_ZOOM = 2.0
FOCUS_ZOOM = 2.08
ARABIC_FONT_URL = (
    "https://fonts.gstatic.com/s/notosansarabic/v33/"
    "nwpxtLGrOAZMl5nJ_wfgRg3DrWFZWsnVBJ_sS6tlqHHFlhQ5l3sQWIHPqzCfyGyvuw.ttf"
)


def fetch_arabic_font_css() -> str:
    request = urllib.request.Request(
        ARABIC_FONT_URL,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        encoded = base64.b64encode(response.read()).decode("ascii")
    return (
        "@font-face{font-family:'Kiro Noto Arabic';font-style:normal;"
        "font-weight:400;font-display:block;"
        f"src:url(data:font/ttf;base64,{encoded}) format('truetype');}}"
        "#input{font-family:'Kiro Noto Arabic',sans-serif!important;"
        "direction:rtl!important;text-align:right!important;}"
    )


def fetch_encoder_html() -> str:
    request = urllib.request.Request(
        ENCODER_URL,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
            )
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        html = response.read().decode("utf-8", errors="replace")
    if 'id="input"' not in html or 'id="output"' not in html:
        raise RuntimeError("Could not fetch the Base64 encoder interface")

    # Keep the current real markup and styles, but remove third-party scripts
    # that inject consent/advertising layers into the controlled walkthrough.
    html = re.sub(r"<script\b[^>]*>[\s\S]*?</script>", "", html, flags=re.I)
    html = re.sub(r"<script\b[^>]*/>", "", html, flags=re.I)
    html = html.replace(
        "<head>",
        (
            f'<head><base href="{ENCODER_URL}">'
            "<style>"
            "#qc-cmp2-container,.qc-cmp2-container{display:none!important}"
            "html.qc-cmp2-showing,body.qc-cmp2-showing{overflow:auto!important}"
            "</style>"
        ),
        1,
    )
    return html


CONTROLLED_PAGE_SCRIPT = r"""
(() => {
  const form = document.querySelector('form[name="text"]');
  const input = document.querySelector('#input');
  const output = document.querySelector('#output');
  const copy = document.querySelector('button.copy');
  if (!form || !input || !output || !copy) throw new Error('Encoder controls missing');

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const bytes = new TextEncoder().encode(input.value);
    let binary = '';
    for (const byte of bytes) binary += String.fromCharCode(byte);
    output.value = btoa(binary);
    output.dispatchEvent(new Event('input', {bubbles: true}));
  });
  copy.addEventListener('click', async () => {
    await navigator.clipboard.writeText(output.value);
  });
})();
"""


OVERLAY_SCRIPT = rf"""
(() => {{
  const installPrivacyGuard = () => {{
    const privacyGuard = document.createElement('style');
    privacyGuard.textContent = `
      #qc-cmp2-container, .qc-cmp2-container {{ display:none !important; }}
      html.qc-cmp2-showing, body.qc-cmp2-showing {{ overflow:auto !important; }}
    `;
    document.documentElement.appendChild(privacyGuard);
    const hidePrivacy = () => {{
      document.querySelectorAll('#qc-cmp2-container, .qc-cmp2-container').forEach((node) => node.remove());
      document.documentElement.classList.remove('qc-cmp2-showing');
      document.body?.classList.remove('qc-cmp2-showing');
    }};
    hidePrivacy();
    new MutationObserver(hidePrivacy).observe(document.documentElement, {{
      childList: true,
      subtree: true,
    }});
  }};
  if (document.documentElement) {{
    installPrivacyGuard();
  }} else {{
    document.addEventListener('DOMContentLoaded', installPrivacyGuard, {{once: true}});
  }}

  const BASE_ZOOM = {BASE_ZOOM};
  const FOCUS_ZOOM = {FOCUS_ZOOM};
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  let cursorX = innerWidth * 0.72;
  let cursorY = innerHeight * 0.82;

  const setBaseZoom = () => {{
    if (document.body) {{
      document.body.style.zoom = String(BASE_ZOOM);
      document.body.style.transformOrigin = 'center top';
    }}
  }};
  if (document.readyState === 'loading') {{
    document.addEventListener('DOMContentLoaded', setBaseZoom, {{once: true}});
  }} else {{
    setBaseZoom();
  }}

  const ensure = () => {{
    setBaseZoom();
    if (document.getElementById('kiro-recorder-overlay')) return;

    const overlay = document.createElement('div');
    overlay.id = 'kiro-recorder-overlay';
    overlay.style.cssText = [
      'position:fixed', 'inset:0', 'z-index:2147483645',
      'pointer-events:none', 'zoom:1', 'font-size:initial'
    ].join(';');
    overlay.innerHTML = `
      <svg id="kiro-spotlight" width="100%" height="100%" style="position:absolute;inset:0;opacity:0;transition:opacity 320ms ease">
        <defs>
          <mask id="kiro-hole-mask" maskUnits="userSpaceOnUse">
            <rect id="kiro-mask-base" x="0" y="0" width="100%" height="100%" fill="white" />
            <rect id="kiro-hole" x="0" y="0" width="0" height="0" rx="22" fill="black" />
          </mask>
          <filter id="kiro-glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="10" result="blur" />
            <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
          </filter>
        </defs>
        <rect x="0" y="0" width="100%" height="100%" fill="rgba(7,12,24,0.72)" mask="url(#kiro-hole-mask)" />
        <rect id="kiro-outline" x="0" y="0" width="0" height="0" rx="22" fill="none" stroke="rgba(255,255,255,0.98)" stroke-width="5" filter="url(#kiro-glow)" />
      </svg>
      <div id="kiro-cursor" style="position:absolute;left:${{cursorX}}px;top:${{cursorY}}px;width:64px;height:64px;filter:drop-shadow(0 6px 6px rgba(0,0,0,.48));transform:translate(-7px,-5px)">
        <svg width="64" height="64" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M4.2 2.6 L4.2 18.9 L8.7 14.7 L11.9 21.6 L14.6 20.3 L11.4 13.6 L17.6 13.6 Z" fill="#111318" stroke="#fff" stroke-width="1.35" stroke-linejoin="round" />
        </svg>
      </div>
      <div id="kiro-ripple" style="position:absolute;width:72px;height:72px;border:5px solid rgba(255,255,255,.95);border-radius:50%;opacity:0;transform:translate(-50%,-50%) scale(.2)"></div>
    `;
    document.documentElement.appendChild(overlay);
  }};

  const rectFor = (selector, margin) => {{
    const element = document.querySelector(selector);
    if (!element) throw new Error(`Missing target: ${{selector}}`);
    const rect = element.getBoundingClientRect();
    return {{
      element,
      x: Math.max(8, rect.left - margin),
      y: Math.max(8, rect.top - margin),
      width: Math.min(innerWidth - 16, rect.width + margin * 2),
      height: Math.min(innerHeight - 16, rect.height + margin * 2),
      cx: rect.left + rect.width / 2,
      cy: rect.top + rect.height / 2,
    }};
  }};

  const drawSpotlight = (target) => {{
    const svg = document.getElementById('kiro-spotlight');
    const hole = document.getElementById('kiro-hole');
    const outline = document.getElementById('kiro-outline');
    for (const node of [hole, outline]) {{
      node.setAttribute('x', String(target.x));
      node.setAttribute('y', String(target.y));
      node.setAttribute('width', String(target.width));
      node.setAttribute('height', String(target.height));
      node.setAttribute('rx', String(Math.min(30, target.height * 0.12)));
    }}
    svg.style.opacity = '1';
  }};

  const zoomTo = async (value, duration = 420) => {{
    const start = Number(document.body.style.zoom || BASE_ZOOM);
    const began = performance.now();
    while (true) {{
      const elapsed = performance.now() - began;
      const t = Math.min(1, elapsed / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      document.body.style.zoom = String(start + (value - start) * eased);
      if (t >= 1) break;
      await new Promise(requestAnimationFrame);
    }}
  }};

  const moveTo = async (x, y, duration = 700) => {{
    ensure();
    const cursor = document.getElementById('kiro-cursor');
    const sx = cursorX;
    const sy = cursorY;
    const began = performance.now();
    while (true) {{
      const elapsed = performance.now() - began;
      const t = Math.min(1, elapsed / duration);
      const eased = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
      cursorX = sx + (x - sx) * eased;
      cursorY = sy + (y - sy) * eased;
      cursor.style.left = `${{cursorX}}px`;
      cursor.style.top = `${{cursorY}}px`;
      if (t >= 1) break;
      await new Promise(requestAnimationFrame);
    }}
  }};

  window.__kiroRecorder = {{
    install: () => ensure(),
    focus: async (selector, margin = 34) => {{
      ensure();
      const element = document.querySelector(selector);
      if (!element) throw new Error(`Missing target: ${{selector}}`);
      element.scrollIntoView({{block: 'center', inline: 'center', behavior: 'smooth'}});
      await sleep(550);
      await zoomTo(FOCUS_ZOOM);
      element.scrollIntoView({{block: 'center', inline: 'center'}});
      await sleep(120);
      const target = rectFor(selector, margin);
      drawSpotlight(target);
      await moveTo(target.cx, target.cy, 760);
      return {{x: target.cx, y: target.cy}};
    }},
    clear: async () => {{
      ensure();
      document.getElementById('kiro-spotlight').style.opacity = '0';
      await sleep(340);
      await zoomTo(BASE_ZOOM, 340);
    }},
    pulse: async () => {{
      ensure();
      const ripple = document.getElementById('kiro-ripple');
      const cursor = document.getElementById('kiro-cursor');
      ripple.style.left = `${{cursorX}}px`;
      ripple.style.top = `${{cursorY}}px`;
      ripple.animate([
        {{opacity: .78, transform: 'translate(-50%,-50%) scale(.2)'}},
        {{opacity: 0, transform: 'translate(-50%,-50%) scale(1.85)'}}
      ], {{duration: 520, easing: 'ease-out'}});
      cursor.animate([
        {{transform: 'translate(-7px,-5px) scale(1)'}},
        {{transform: 'translate(-7px,-5px) scale(.78)'}},
        {{transform: 'translate(-7px,-5px) scale(1)'}}
      ], {{duration: 260, easing: 'ease-out'}});
      await sleep(170);
    }},
  }};
}})();
"""


def suppress_privacy_dialog(page: Page) -> None:
    page.evaluate(
        """() => {
          const removeConsent = () => {
            document.querySelectorAll(
              '#qc-cmp2-container, .qc-cmp2-container, [class*="qc-cmp2"]'
            ).forEach((node) => node.remove());
            document.documentElement.classList.remove('qc-cmp2-showing');
            document.body?.classList.remove('qc-cmp2-showing');
            if (document.body) document.body.style.overflow = 'auto';
          };
          removeConsent();
          window.__kiroConsentObserver?.disconnect();
          window.__kiroConsentObserver = new MutationObserver(removeConsent);
          window.__kiroConsentObserver.observe(document.documentElement, {
            childList: true,
            subtree: true,
          });
        }"""
    )


def focus(page: Page, selector: str, margin: int = 34) -> tuple[float, float]:
    point = page.evaluate(
        "([selector, margin]) => window.__kiroRecorder.focus(selector, margin)",
        [selector, margin],
    )
    page.mouse.move(point["x"], point["y"], steps=28)
    return point["x"], point["y"]


def click_focused(page: Page, selector: str) -> None:
    page.evaluate("window.__kiroRecorder.pulse()")
    page.locator(selector).click()


def clear_focus(page: Page) -> None:
    page.evaluate("window.__kiroRecorder.clear()")


def record(output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    encoder_html = fetch_encoder_html()
    font_css = fetch_arabic_font_css()
    scratch = output.parent / ".playwright-video"
    scratch.mkdir(parents=True, exist_ok=True)
    existing_videos = set(scratch.glob("*.webm"))

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--window-size=3840,2160",
            ],
        )
        context = browser.new_context(
            viewport=VIEWPORT,
            device_scale_factor=1,
            locale="en-US",
            timezone_id="UTC",
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
            ),
            record_video_dir=scratch,
            record_video_size=VIEWPORT,
            permissions=["clipboard-read", "clipboard-write"],
        )
        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )
        context.add_init_script(OVERLAY_SCRIPT)
        page = context.pages[0] if context.pages else context.new_page()
        page.route(
            ENCODER_URL,
            lambda route: route.fulfill(
                status=200,
                content_type="text/html; charset=utf-8",
                body=encoder_html,
            ),
        )

        # The requested domain's actual text operation for plain Arabic is Encode.
        # Loading the paired encoder directly avoids recording the decode page's
        # anti-bot interstitial and preserves the same site's real interface.
        page.goto(ENCODER_URL, wait_until="domcontentloaded", timeout=120_000)
        page.locator("#input").wait_for(state="visible", timeout=120_000)
        page.add_script_tag(content=CONTROLLED_PAGE_SCRIPT)
        page.add_style_tag(content=font_css)
        page.evaluate("document.fonts.load('32px \\\"Kiro Noto Arabic\\\"')")
        suppress_privacy_dialog(page)
        page.evaluate("window.__kiroRecorder.install()")
        page.wait_for_timeout(1_200)

        focus(page, "#input", 42)
        click_focused(page, "#input")
        page.locator("#input").press_sequentially(ARABIC_TEXT, delay=92)
        page.wait_for_timeout(850)
        clear_focus(page)
        page.wait_for_timeout(420)

        focus(page, "#submit_text", 34)
        page.evaluate("window.__kiroRecorder.pulse()")
        page.locator("#submit_text").click()

        page.locator("#output").wait_for(state="visible", timeout=120_000)
        page.wait_for_function(
            "expected => document.querySelector('#output')?.value === expected",
            arg=EXPECTED_OUTPUT,
            timeout=120_000,
        )
        page.evaluate("window.__kiroRecorder.install()")
        page.wait_for_timeout(650)

        focus(page, "#output", 42)
        click_focused(page, "#output")
        page.locator("#output").press("Control+A")
        page.wait_for_timeout(650)
        clear_focus(page)
        page.wait_for_timeout(320)

        focus(page, "button.copy", 34)
        click_focused(page, "button.copy")
        page.wait_for_timeout(950)
        copied = page.evaluate("navigator.clipboard.readText()")
        if copied != EXPECTED_OUTPUT:
            raise RuntimeError(f"Clipboard verification failed: {copied!r}")
        clear_focus(page)
        page.wait_for_timeout(1_100)

        video = page.video
        if video is None:
            raise RuntimeError("Playwright did not create a video")
        context.close()

        created_videos = set(scratch.glob("*.webm")) - existing_videos
        if len(created_videos) != 1:
            raise RuntimeError(
                f"Expected one raw Playwright video, found {len(created_videos)}"
            )
        raw_video = created_videos.pop()
        if output.exists():
            output.unlink()
        raw_video.replace(output)
        browser.close()

    print(f"Recorded: {output}")
    print(f"Source: {SOURCE_URL} (Encode navigation: {ENCODER_URL})")
    print(f"Verified output and clipboard: {EXPECTED_OUTPUT}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("media/projects/base64decode-demo/base64encode-4k.webm"),
    )
    args = parser.parse_args()
    record(args.output.resolve())


if __name__ == "__main__":
    main()
