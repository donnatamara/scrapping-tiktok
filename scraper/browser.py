import os
import random
import time
from typing import Optional

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
]


STEALTH_SCRIPT = """
// Override webdriver
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

// Override plugins with realistic data
Object.defineProperty(navigator, 'plugins', {
    get: () => [
        { name: 'PDF Viewer', filename: 'internal-pdf-viewer' },
        { name: 'Chrome PDF Viewer', filename: 'chrome-pdf-viewer' },
        { name: 'Chromium PDF Viewer', filename: 'chromium-pdf-viewer' },
    ]
});

// Override languages
Object.defineProperty(navigator, 'languages', { get: () => ['id-ID', 'id', 'en-US', 'en'] });
Object.defineProperty(navigator, 'language', { get: () => 'id-ID' });

// Override platform
Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });

// Hardware info
Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
Object.defineProperty(navigator, 'maxTouchPoints', { get: () => 0 });

// Connection
Object.defineProperty(navigator, 'connection', {
    get: () => ({
        effectiveType: '4g',
        rtt: 50,
        downlink: 10,
        saveData: false,
    })
});

// Chrome runtime
window.chrome = {
    runtime: {
        connect: () => ({}),
        sendMessage: () => ({}),
        onMessage: { addListener: () => {} },
        onConnect: { addListener: () => {} },
    },
    loadTimes: () => ({}),
    csi: () => ({}),
    app: { isInstalled: false },
};

// Permissions
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (params) => (
    params.name === 'notifications' ? Promise.resolve({ state: 'prompt' }) : originalQuery(params)
);
"""


VERIFICATION_INDICATORS_URL = [
    "/challenge/", "/captcha/",
    "security-check", "human-verify",
]


class BrowserManager:
    def __init__(self, headless: bool = False,
                 viewport_width: int = 1366,
                 viewport_height: int = 768,
                 logger=None,
                 cdp_url: str = ""):
        self.headless = headless
        self.viewport = {"width": viewport_width, "height": viewport_height}
        self.playwright: Optional[sync_playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.logger = logger
        self.cdp_url = cdp_url
        self._connected = False

    @property
    def is_connected(self):
        return self._connected

    def _log(self, msg):
        if self.logger:
            self.logger.info(msg)

    def start(self):
        if self.cdp_url:
            self._connect_via_cdp(self.cdp_url)
        else:
            self._launch_browser()

    def _launch_browser(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-session-crashed-bubble",
                "--disable-infobars",
            ],
        )
        self._create_context()

    def _connect_via_cdp(self, url: str):
        self._log(f"Menghubungkan ke remote Chrome via CDP: {url}")
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.connect_over_cdp(url)
        self._connected = True
        if self.browser.contexts:
            self.context = self.browser.contexts[0]
            self._log(f"Menggunakan existing context ({len(self.context.pages)} pages)")
        else:
            self.context = self.browser.new_context(
                viewport=self.viewport,
                locale="id-ID",
                timezone_id="Asia/Jakarta",
            )
        self.context.add_init_script(STEALTH_SCRIPT)

    def _create_context(self):
        self.context = self.browser.new_context(
            viewport=self.viewport,
            user_agent=random.choice(USER_AGENTS),
            locale="id-ID",
            timezone_id="Asia/Jakarta",
            permissions=[],
            device_scale_factor=1,
            is_mobile=False,
            has_touch=False,
        )
        self.context.set_default_timeout(45000)
        self.context.add_init_script(STEALTH_SCRIPT)

    def new_page(self) -> Page:
        if not self.context:
            raise RuntimeError("Browser not started. Call start() first.")
        try:
            page = self.context.new_page()
            page.set_default_timeout(45000)
            return page
        except Exception:
            if self._connected:
                self._log("Gagal buat page di remote browser, coba lagi...")
                time.sleep(2)
                page = self.context.new_page()
                page.set_default_timeout(45000)
                return page
            self._restart_context()
            page = self.context.new_page()
            page.set_default_timeout(45000)
            return page

    def _restart_context(self):
        if self._connected:
            self._log("Tidak bisa restart context di remote browser (akan buat page baru)")
            return
        try:
            if self.context:
                try:
                    self.context.close()
                except Exception:
                    pass
        except Exception:
            pass
        time.sleep(random.uniform(3, 6))
        self._create_context()

    def handle_verification(self, page: Page) -> bool:
        try:
            if page.url == "about:blank":
                return False
            page_url = page.url.lower()

            for indicator in VERIFICATION_INDICATORS_URL:
                if indicator in page_url:
                    self.save_debug_page(page, f"verify_{int(time.time())}")
                    return True
        except Exception:
            pass
        return False

    def wait_verification_pass(self, page: Page, timeout: int = 60) -> bool:
        self._log(f"  Menunggu verification selesai ({timeout} detik)...")
        try:
            page.wait_for_timeout(timeout * 1000)
            return True
        except Exception:
            return False

    def human_scroll(self, page: Page, distance: Optional[int] = None):
        try:
            if distance is None:
                distance = random.randint(300, 800)
            steps = random.randint(3, 6)
            for _ in range(steps):
                step_dist = distance // steps + random.randint(-20, 20)
                page.evaluate(f"window.scrollBy(0, {step_dist})")
                time.sleep(random.uniform(0.1, 0.3))
        except Exception:
            pass

    def random_mouse_move(self, page: Page):
        try:
            x = random.randint(100, self.viewport["width"] - 100)
            y = random.randint(100, self.viewport["height"] - 100)
            page.mouse.move(x, y, steps=random.randint(5, 12))
        except Exception:
            pass

    def human_wait_before_action(self, page: Page):
        self.random_mouse_move(page)
        time.sleep(random.uniform(0.5, 2.0))

    def save_debug_page(self, page: Page, label: str):
        debug_dir = "logs/debug"
        os.makedirs(debug_dir, exist_ok=True)
        try:
            page.screenshot(path=f"{debug_dir}/{label}.png", full_page=True)
        except Exception:
            pass
        try:
            with open(f"{debug_dir}/{label}.html", "w", encoding="utf-8") as f:
                f.write(page.content())
        except Exception:
            pass

    def random_delay(self, min_sec: float = 2.0, max_sec: float = 5.0):
        time.sleep(random.uniform(min_sec, max_sec))

    def stop(self):
        if self._connected:
            self._log("Melepas koneksi dari remote browser (tanpa menutupnya)")
            try:
                if self.playwright:
                    self.playwright.stop()
            except Exception:
                pass
            return
        try:
            if self.context:
                try:
                    self.context.close()
                except Exception:
                    pass
        except Exception:
            pass
        try:
            if self.browser:
                try:
                    self.browser.close()
                except Exception:
                    pass
        except Exception:
            pass
        try:
            if self.playwright:
                try:
                    self.playwright.stop()
                except Exception:
                    pass
        except Exception:
            pass
