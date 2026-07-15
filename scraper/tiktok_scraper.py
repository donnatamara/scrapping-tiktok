import json
import re
import random
import time
from collections import deque
from typing import List, Optional, Set, Dict, Any
from urllib.parse import urljoin

from playwright.sync_api import Page, TimeoutError as PwTimeout

from config import Settings
from models import Account, Video
from database import Database
from utils import (
    extract_email,
    extract_social_media,
    LocationDetector,
    IndicatorDetector,
)
from .browser import BrowserManager


MONETIZATION_API_FIELDS = {
    "tiktokShop": "TikTok Shop",
    "shopTab": "Shop tab",
    "businessAccount": "Akun bisnis",
    "isADVirtual": "Iklan TikTok",
    "isStar": "Creator Star",
    "liveAgreement": "Live streaming",
    "isCreator": "Creator terverifikasi",
    "platformVerified": "Platform terverifikasi",
    "creatorNode": "Creator Node",
}


COMMERCE_VIDEO_KEYS = [
    "ecommerceInfo", "commerceInfo", "productId", "productIds",
    "shopInfo", "promote", "isCommerce", "isAffiliated",
    "affiliate", "commerce",
]

CLASSIFICATION_KEYWORDS = {
    "travel": [
        "travel", "wisata", "liburan", "vacation", "hotel", "pantai", "gunung",
        "destinasi", "jalan-jalan", "tour", "trip", "holiday", "beach", "mountain",
        "explore", "adventure", "travelling", "backpacker", "roadtrip", "getaway",
        "wanderlust", "libur", "tiket", "pesawat", "bandara", "penginapan",
        "resort", "villa", "wisata alam", "wisata kuliner", "wisata budaya",
        "candi", "air terjun", "danau", "pulau", "snorkeling", "diving",
    ],
    "foodvloger": [
        "food", "makanan", "kuliner", "resep", "recipe", "restaurant", "cafe",
        "masak", "cooking", "makan", "minum", "kopi", "coffee", "street food",
        "foodie", "makanan enak", "jajanan", "snack", "cemilan", "bakso", "soto",
        "nasi", "mie", "ayam", "sate", "seafood", "dimsum", "roti", "kue",
        "bakery", "dessert", "minuman", "es", "pedas", "enak", "nyobain",
        "cobain", "review makanan", "food review", "mukbang", "kulineran",
    ],
    "lifestyle": [
        "lifestyle", "fashion", "outfit", "ootd", "style", "daily", "vlog",
        "rutinitas", "morning routine", "skincare", "makeup", "beauty",
        "gym", "workout", "fitness", "health", "healthy", "tips",
        "dekorasi", "home", "interior", "review", "haul", "shopping",
        "fashion", "grooming", "bodycare", "haircare", "perawatan",
        "daily life", "my day", "productive", "self care", "wellness",
        "motivasi", "inspirasi", "quote", "self improvement",
    ],
    "affiliate": [
        "affiliate", "link", "promo", "diskon", "discount", "cod",
        "belanja", "shop", "order", "pesan", "shopee", "tokopedia",
        "tiktok shop", "keranjang kuning", "link di bio", "linktree",
        "free ongkir", "voucher", "flash sale", "murah", "hemat", "promosi",
        "jual", "jualan", "produk", "barang", "rekomendasi", "recommended",
        "checkout", "bundling", "paket hemat", "gratis", "bonus",
    ],
}

PRODUCT_COUNT_FIELDS = [
    "productCount", "shopProductCount", "tiktokShopCount",
    "productCountInShop", "sellerProductCount",
]


class TikTokScraper:
    BASE_URL = "https://www.tiktok.com"

    def __init__(self, settings: Settings, db: Database, logger):
        self.settings = settings
        self.db = db
        self.logger = logger
        self.browser = BrowserManager(
            headless=settings.HEADLESS,
            viewport_width=settings.VIEWPORT_WIDTH,
            viewport_height=settings.VIEWPORT_HEIGHT,
            logger=logger,
            cdp_url=settings.REMOTE_CDP,
        )
        self.location_detector = LocationDetector(settings.BANYUMAS_SUBDISTRICTS)
        self.indicator_detector = IndicatorDetector(
            settings.CREATOR_KEYWORDS, settings.BUSINESS_INDICATORS,
            settings.MONETIZATION_KEYWORDS, settings.SHOP_KEYWORDS,
        )
        self.scraped_accounts: Set[str] = set()
        self._warmed_up = False

    def _warmup(self):
        if self._warmed_up:
            return
        self.logger.info("Warm-up: kunjungi TikTok homepage...")
        try:
            page = self.browser.new_page()
            page.goto(self.BASE_URL, wait_until="domcontentloaded", timeout=30000)
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass
            page.wait_for_timeout(3000)
            self._handle_popups(page)
            page.close()
            self._warmed_up = True
            self.logger.info("Warm-up selesai")
        except Exception as e:
            self.logger.warning(f"Warm-up gagal: {e}")
            self._warmed_up = True

    def run(self):
        self.logger.info("=" * 60)
        self.logger.info("MEMULAI SCRAPING TIKTOK BANYUMAS")
        self.logger.info("=" * 60)

        self.browser.start()
        if self.browser.is_connected:
            self.logger.info(f"Browser remote terhubung ({self.browser.cdp_url})")
        else:
            self.logger.info("Browser lokal berhasil dimulai")

        try:
            self._warmup()

            keywords = self.settings.SEARCH_KEYWORDS + [
                f"#{h}" for h in self.settings.HASHTAGS
            ]

            for keyword in keywords:
                try:
                    self._scrape_keyword(keyword)
                except Exception as e:
                    self.logger.error(f"Error keyword '{keyword}': {e}")
                self.browser.random_delay(
                    self.settings.MIN_DELAY, self.settings.MAX_DELAY
                )

            if self.settings.ENABLE_NETWORK_EXPANSION:
                self._expand_network()

            self.logger.info("=" * 60)
            self.logger.info("SCRAPING SELESAI")
            self.logger.info(f"Total akun: {self.db.get_account_count()}")
            self.logger.info(f"Total video: {self.db.get_video_count()}")
            self.logger.info("=" * 60)

        finally:
            try:
                self.browser.stop()
            except Exception:
                pass

    def _scrape_keyword(self, keyword: str):
        self.logger.info(f"Mencari akun untuk keyword: {keyword}")

        usernames = set()

        hashtag_results = self._search_hashtag(keyword)
        usernames.update(hashtag_results)

        search_results = self._search_users(keyword)
        usernames.update(search_results)

        video_results = self._search_videos(keyword)
        usernames.update(video_results)

        if not usernames:
            self.logger.warning(f"Tidak ada hasil untuk keyword: {keyword}")
            return

        self.logger.info(
            f"Ditemukan {len(usernames)} akun untuk keyword: {keyword}"
            f" ({len(hashtag_results)} dari hashtag, {len(search_results)} user search, {len(video_results)} video search)"
        )

        for username in sorted(usernames):
            if username in self.scraped_accounts:
                continue
            if self.db.account_exists(username):
                self.scraped_accounts.add(username)
                continue

            try:
                self._scrape_account(username)
                self.scraped_accounts.add(username)
                self.browser.random_delay(
                    self.settings.MIN_DELAY, self.settings.MAX_DELAY
                )
            except Exception as e:
                self.logger.error(f"Gagal scrape @{username}: {e}")
                try:
                    self.browser._restart_context()
                except Exception:
                    pass

    def _check_verification(self, page: Page) -> bool:
        if self.browser.handle_verification(page):
            self.logger.warning(f"  Verification terdeteksi!")
            self.browser.save_debug_page(page, f"verify_{int(time.time())}")
            return True
        return False

    def _search_users(self, keyword: str) -> List[str]:
        page = self.browser.new_page()
        usernames: Set[str] = set()
        had_error = False

        def on_response(response):
            try:
                if not response.ok:
                    return
                ctype = response.headers.get("content-type", "")
                if "application/json" not in ctype:
                    return
                data = response.json()
                if not isinstance(data, dict):
                    return

                def _walk(obj):
                    if not isinstance(obj, dict):
                        return
                    uid = obj.get("uniqueId")
                    if isinstance(uid, str) and len(uid) > 1:
                        usernames.add(uid)
                    for v in obj.values():
                        if isinstance(v, list):
                            for item in v:
                                _walk(item)
                        elif isinstance(v, dict):
                            _walk(v)

                _walk(data)
            except Exception:
                pass

        page.on("response", on_response)

        try:
            search_url = f"{self.BASE_URL}/search?q={keyword}"
            self.logger.debug(f"User search via: {search_url}")
            page.goto(search_url, wait_until="domcontentloaded", timeout=self.settings.PAGE_LOAD_TIMEOUT)
            self._handle_popups(page)
            try:
                page.wait_for_load_state("networkidle", timeout=12000)
            except Exception:
                pass
            page.wait_for_timeout(3000)

            for tab_text in ("Users", "People", "Akun"):
                try:
                    tab = page.query_selector(f'div[role="tab"]:has-text("{tab_text}"), span:has-text("{tab_text}")')
                    if tab and tab.is_visible():
                        tab.click()
                        page.wait_for_timeout(3000)
                        self.logger.debug(f"  Clicked tab: {tab_text}")
                        break
                except Exception:
                    pass

            try:
                page.evaluate("window.scrollTo(0, 400)")
            except Exception:
                pass
            try:
                page.wait_for_timeout(2000)
            except Exception:
                pass

            blocked = self._is_blocked_or_login(page)
            verified = self._check_verification(page)

            if blocked:
                _debug_page(page, self.logger, f"blocked_user_{keyword}")

            try:
                links = page.evaluate("""() =>
                    Array.from(document.querySelectorAll('a[href*="/@"]'))
                        .map(a => a.getAttribute('href'))
                        .filter(Boolean)
                """)
                for link in links:
                    m = re.search(r'/@([a-zA-Z0-9_.]+)', link)
                    if m and len(m.group(1)) > 1:
                        usernames.add(m.group(1))
            except Exception:
                pass

            html_usernames = self._extract_usernames_from_page(page)
            usernames.update(html_usernames)

            self.logger.info(f"User search '{keyword}': {len(usernames)} akun (url={page.url[:50]}, blocked={blocked}, verify={verified})")

        except PwTimeout:
            self.logger.warning(f"Timeout user search '{keyword}'")
            had_error = True
        except Exception as e:
            self.logger.error(f"Error user search '{keyword}': {e}")
            had_error = True
        finally:
            try:
                page.remove_listener("response", on_response)
                page.close()
            except Exception:
                pass

        if had_error:
            self.browser._restart_context()

        return list(usernames)[:50]

    def _search_videos(self, keyword: str) -> List[str]:
        page = self.browser.new_page()
        usernames: Set[str] = set()
        had_error = False

        def on_response(response):
            try:
                if not response.ok:
                    return
                ctype = response.headers.get("content-type", "")
                if "application/json" not in ctype:
                    return
                data = response.json()
                if not isinstance(data, dict):
                    return

                def _walk(obj):
                    if not isinstance(obj, dict):
                        return
                    uid = obj.get("uniqueId")
                    if isinstance(uid, str) and len(uid) > 1:
                        usernames.add(uid)
                    for v in obj.values():
                        if isinstance(v, list):
                            for item in v:
                                _walk(item)
                        elif isinstance(v, dict):
                            _walk(v)

                _walk(data)
            except Exception:
                pass

        page.on("response", on_response)

        try:
            search_url = f"{self.BASE_URL}/search?q={keyword}"
            self.logger.debug(f"Video search via: {search_url}")
            page.goto(search_url, wait_until="domcontentloaded", timeout=self.settings.PAGE_LOAD_TIMEOUT)
            self._handle_popups(page)
            try:
                page.wait_for_load_state("networkidle", timeout=12000)
            except Exception:
                pass
            page.wait_for_timeout(3000)

            for tab_text in ("Videos", "Video"):
                try:
                    tab = page.query_selector(f'div[role="tab"]:has-text("{tab_text}"), span:has-text("{tab_text}")')
                    if tab and tab.is_visible():
                        tab.click()
                        page.wait_for_timeout(3000)
                        self.logger.debug(f"  Clicked tab: {tab_text}")
                        break
                except Exception:
                    pass

            try:
                page.evaluate("window.scrollTo(0, 400)")
            except Exception:
                pass
            try:
                page.wait_for_timeout(2000)
            except Exception:
                pass

            blocked = self._is_blocked_or_login(page)
            verified = self._check_verification(page)

            if blocked:
                _debug_page(page, self.logger, f"blocked_video_{keyword}")

            try:
                links = page.evaluate("""() =>
                    Array.from(document.querySelectorAll('a[href*="/@"]'))
                        .map(a => a.getAttribute('href'))
                        .filter(Boolean)
                """)
                for link in links:
                    m = re.search(r'/@([a-zA-Z0-9_.]+)', link)
                    if m and len(m.group(1)) > 1:
                        usernames.add(m.group(1))
            except Exception:
                pass

            html_usernames = self._extract_usernames_from_page(page)
            usernames.update(html_usernames)

            self.logger.info(f"Video search '{keyword}': {len(usernames)} akun (url={page.url[:50]}, blocked={blocked}, verify={verified})")

        except PwTimeout:
            self.logger.warning(f"Timeout video search '{keyword}'")
            had_error = True
        except Exception as e:
            self.logger.error(f"Error video search '{keyword}': {e}")
            had_error = True
        finally:
            try:
                page.remove_listener("response", on_response)
                page.close()
            except Exception:
                pass

        if had_error:
            self.browser._restart_context()

        return list(usernames)[:50]

    def _search_hashtag(self, keyword: str) -> List[str]:
        page = self.browser.new_page()
        usernames: Set[str] = set()
        had_error = False

        def on_response(response):
            try:
                if not response.ok:
                    return
                ctype = response.headers.get("content-type", "")
                if "application/json" not in ctype:
                    return
                data = response.json()
                if not isinstance(data, dict):
                    return

                def _walk(obj):
                    if not isinstance(obj, dict):
                        return
                    uid = obj.get("uniqueId")
                    if isinstance(uid, str) and len(uid) > 1:
                        usernames.add(uid)
                    for v in obj.values():
                        if isinstance(v, list):
                            for item in v:
                                _walk(item)
                        elif isinstance(v, dict):
                            _walk(v)

                _walk(data)
            except Exception:
                pass

        page.on("response", on_response)

        try:
            tag = keyword.lstrip("#").strip()
            url = f"{self.BASE_URL}/tag/{tag}"
            self.logger.debug(f"Hashtag page: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=self.settings.PAGE_LOAD_TIMEOUT)
            self._handle_popups(page)
            try:
                page.wait_for_load_state("networkidle", timeout=12000)
            except Exception:
                pass
            page.wait_for_timeout(3000)

            for i in range(15):
                try:
                    page.evaluate("window.scrollBy(0, window.innerHeight * 2)")
                except Exception:
                    break
                page.wait_for_timeout(2000)
                if len(usernames) >= 50:
                    break

            try:
                links = page.evaluate("""() =>
                    Array.from(document.querySelectorAll('a[href*="/@"]'))
                        .map(a => a.getAttribute('href'))
                        .filter(Boolean)
                """)
                for link in links:
                    m = re.search(r'/@([a-zA-Z0-9_.]+)', link)
                    if m and len(m.group(1)) > 1:
                        usernames.add(m.group(1))
            except Exception:
                pass

            self.logger.info(f"  Hashtag '{tag}': {len(usernames)} akun")

        except Exception as e:
            self.logger.error(f"  Error hashtag '{keyword}': {e}")
            had_error = True
        finally:
            try:
                page.remove_listener("response", on_response)
                page.close()
            except Exception:
                pass

        if had_error:
            self.browser._restart_context()

        return list(usernames)[:50]

    def _extract_usernames_from_page(self, page: Page) -> List[str]:
        usernames: set = set()
        html = ""

        try:
            html = page.content()
        except Exception:
            return []

        self.logger.debug(f"  Page HTML length: {len(html)} chars")

        try:
            page_text = page.inner_text("body") or ""
            self.logger.debug(f"  Page body text length: {len(page_text)} chars")
        except Exception:
            page_text = ""

        if len(html) < 500:
            self.logger.debug(f"  Page terlalu kecil, mungkin blocked")
            _debug_page(page, self.logger, "small_page")
            return []

        try:
            for match in re.finditer(r'/"uniqueId"\s*:\s*"([^"]+)"', html):
                uid = match.group(1)
                if uid and len(uid) > 1:
                    usernames.add(uid)
        except Exception:
            pass

        try:
            for match in re.finditer(r'"uniqueId"\s*:\s*"([^"]+)"', html):
                uid = match.group(1)
                if uid and len(uid) > 1:
                    usernames.add(uid)
        except Exception:
            pass

        try:
            for match in re.finditer(r'"author"\s*:\s*\{\s*"uniqueId"\s*:\s*"([^"]+)"', html):
                uid = match.group(1)
                if uid and len(uid) > 1:
                    usernames.add(uid)
        except Exception:
            pass

        try:
            for match in re.finditer(r'/@([a-zA-Z0-9_.]+)(?:\?|"|\'|<|\s|/|$)', html):
                uid = match.group(1)
                if uid and len(uid) > 1:
                    usernames.add(uid)
        except Exception:
            pass

        exclude = {"search", "login", "signup", "explore", "messages",
                    "settings", "feedback", "about", "tiktok", "trending",
                    "shop", "live", "upload", "business", "creator"}
        return [u for u in usernames if u and len(u) > 1 and u.lower() not in exclude][:50]

    def _scrape_account(self, username: str, max_retries: int = 1):
        self.logger.info(f"Scrape akun: @{username}")

        for attempt in range(max_retries + 1):
            page = self.browser.new_page()
            api_data: Dict[str, Any] = {"user": None, "videos": {}}
            api_call_count = [0]

            def intercept_response(response):
                try:
                    if not response.ok:
                        return
                    ctype = response.headers.get("content-type", "")
                    if "application/json" not in ctype and "text/json" not in ctype:
                        return
                    url = response.url
                    data = response.json()
                    if not isinstance(data, dict):
                        return

                    user_obj = None
                    if data.get("user") and isinstance(data["user"], dict):
                        user_obj = data["user"]
                    user_info = data.get("userInfo", {})
                    if isinstance(user_info, dict) and user_info.get("user"):
                        user_obj = user_info["user"]
                    if data.get("userDetail") and isinstance(data["userDetail"], dict):
                        user_obj = data["userDetail"]

                    if user_obj:
                        api_data["user"] = user_obj

                    item_list = data.get("itemList", [])
                    if isinstance(item_list, list):
                        for item in item_list:
                            vid = item.get("id") or item.get("video_id") or ""
                            if vid and isinstance(item, dict):
                                if vid not in api_data["videos"]:
                                    api_data["videos"][vid] = item
                                    api_call_count[0] += 1

                    posts = data.get("posts", [])
                    if isinstance(posts, list):
                        for item in posts:
                            vid = item.get("id") or item.get("video_id") or ""
                            if vid and isinstance(item, dict):
                                if vid not in api_data["videos"]:
                                    api_data["videos"][vid] = item
                                    api_call_count[0] += 1
                except Exception:
                    pass

            page.on("response", intercept_response)

            try:
                profile_url = f"{self.BASE_URL}/@{username}"
                page.goto(profile_url, wait_until="domcontentloaded", timeout=self.settings.PAGE_LOAD_TIMEOUT)
                self._handle_popups(page)
                try:
                    page.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    pass
                page.wait_for_timeout(5000)

                if self._is_blocked_or_login(page):
                    self.logger.warning(f"Redirect/login page @{username}")
                    page.remove_listener("response", intercept_response)
                    page.close()
                    return
                if self._is_user_not_found(page):
                    self.logger.warning(f"Akun @{username} tidak ditemukan")
                    page.remove_listener("response", intercept_response)
                    page.close()
                    return

                if self._check_verification(page):
                    self.logger.warning(f"  Verification attempt {attempt + 1}/{max_retries + 1}")
                    page.remove_listener("response", intercept_response)
                    page.close()
                    if attempt < max_retries:
                        self.browser._restart_context()
                        self.browser.random_delay(5, 10)
                        continue
                    else:
                        self.logger.error(f"  Verification max retries, skip @{username}")
                        return

                self.logger.debug(f"  API user data: {'ADA' if api_data['user'] else 'TIDAK ADA'}")
                self.logger.debug(f"  API videos awal: {len(api_data['videos'])}")

                account = None
                if api_data["user"]:
                    account = self._build_account(api_data["user"], username)

                if account is None:
                    account = self._parse_from_dom(page, username)

                if account is None:
                    self.logger.warning(f"Tidak bisa ambil data @{username}")
                    page.remove_listener("response", intercept_response)
                    page.close()
                    return

                max_videos = self.settings.MAX_VIDEOS_TO_SCRAPE
                self.logger.info(f"  Scroll untuk load {max_videos} video terbaru @{username}...")
                scrolls_without_new = 0
                max_scrolls_without_new = 3
                previous_count = len(api_data["videos"])

                for scroll_i in range(40):
                    try:
                        page.evaluate("window.scrollBy(0, window.innerHeight * 2)")
                        page.wait_for_timeout(2000)
                    except Exception:
                        break

                    current_count = len(api_data["videos"])

                    if current_count > previous_count:
                        new_vids = current_count - previous_count
                        self.logger.debug(f"    Scroll {scroll_i + 1}: +{new_vids} video (total: {current_count})")
                        previous_count = current_count
                        scrolls_without_new = 0
                    else:
                        scrolls_without_new += 1
                        self.logger.debug(f"    Scroll {scroll_i + 1}: tidak ada video baru (percobaan {scrolls_without_new}/{max_scrolls_without_new})")

                    if scrolls_without_new >= max_scrolls_without_new:
                        self.logger.info(f"  Berhenti scroll: {max_scrolls_without_new}x berturut-turut tanpa video baru")
                        break

                    if current_count >= max_videos:
                        self.logger.info(f"  Berhenti scroll: sudah cukup {max_videos} video")
                        break

                    self.browser.random_delay(0.5, 1.5)

                videos = []
                sorted_vids = sorted(
                    api_data["videos"].items(),
                    key=lambda x: x[1].get("createTime", 0) or 0,
                    reverse=True,
                )
                for vid, item in sorted_vids[:max_videos]:
                    v = self._build_video(item, username)
                    if v:
                        videos.append(v)

                if not videos:
                    self.logger.debug("  Fallback: extract video IDs dari HTML...")
                    try:
                        html = page.content()
                        vids = re.findall(r'/video/(\d+)', html)
                        vids = list(dict.fromkeys(vids))
                        for vid in vids:
                            videos.append(Video(
                                account_id=username,
                                video_url=f"{self.BASE_URL}/@{username}/video/{vid}",
                            ))
                    except Exception:
                        pass

                self._detect_attributes(account, videos)
                self._calculate_statistics(account, videos)
                self._detect_monetization(account, videos, api_data)

                raw_user = api_data.get("user") or {}
                for field in PRODUCT_COUNT_FIELDS:
                    val = raw_user.get(field)
                    if isinstance(val, (int, float)) and val > 0:
                        account.product_count = int(val)
                        break

                account.classification = self._classify_account(videos)

                self.db.save_account(account)
                for v in videos:
                    self.db.save_video(v)

                loc_info = f" | Lokasi: {account.location_detected or '-'} ({account.location_source or '-'})" if account.location_detected else ""
                monet_info = f" | Monetisasi: {'YA' if account.monetization else 'TIDAK'}"
                shop_info = f" | Shop: {'YA' if account.has_tiktok_shop else 'TIDAK'}"
                er_info = f" | ER: {account.engagement_rate:.2f}%" if account.engagement_rate is not None else ""
                cls_info = f" | Kelas: {account.classification or '-'}"
                vc_info = f" | Video: {account.video_count or 0}"
                self.logger.info(
                    f"Berhasil: @{username}"
                    f" | Followers: {account.followers or 0}"
                    f"{vc_info}"
                    f"{loc_info}{monet_info}{shop_info}{er_info}{cls_info}"
                )

                page.remove_listener("response", intercept_response)
                page.close()
                return

            except PwTimeout:
                self.logger.warning(f"Timeout @{username}")
                page.remove_listener("response", intercept_response)
                page.close()
                if attempt < max_retries:
                    self.browser._restart_context()
                    self.browser.random_delay(5, 10)
                    continue
                return
            except Exception as e:
                self.logger.error(f"Error @{username}: {e}")
                page.remove_listener("response", intercept_response)
                try:
                    page.close()
                except Exception:
                    pass
                if attempt < max_retries:
                    self.browser._restart_context()
                    self.browser.random_delay(5, 10)
                    continue
                return

    def _build_account(self, user: dict, username: str) -> Optional[Account]:
        try:
            bio = (user.get("signature") or user.get("bio") or "").strip()
            social = extract_social_media(bio)
            email = extract_email(bio)

            profile_location = user.get("location") or user.get("region") or None
            if isinstance(profile_location, dict):
                profile_location = profile_location.get("shortName") or profile_location.get("name") or str(profile_location)

            has_tiktok_shop = user.get("tiktokShop") or user.get("shopTab") or None
            if isinstance(has_tiktok_shop, int):
                has_tiktok_shop = bool(has_tiktok_shop)

            return Account(
                username=username,
                unique_id=user.get("uniqueId", username) or username,
                nickname=user.get("nickname"),
                bio=bio or None,
                profile_url=f"{self.BASE_URL}/@{username}",
                avatar_url=(
                    user.get("avatarLarger")
                    or user.get("avatarMedium")
                    or user.get("avatarThumb")
                ),
                followers=_safe_int(user.get("followerCount")),
                following=_safe_int(user.get("followingCount")),
                total_likes=_safe_int(user.get("heartCount")),
                video_count=_safe_int(user.get("videoCount")),
                verified=bool(user.get("verified", False)),
                private_account=bool(user.get("privateAccount", False)),
                business_account=user.get("businessAccount"),
                email=email,
                website=social.get("website"),
                instagram=social.get("instagram"),
                youtube=social.get("youtube"),
                linktree=social.get("linktree"),
                whatsapp=social.get("whatsapp"),
                facebook=social.get("facebook"),
                profile_location=profile_location,
                has_tiktok_shop=has_tiktok_shop,
            )
        except Exception as e:
            self.logger.error(f"Build account error @{username}: {e}")
            return None

    def _build_video(self, item: dict, username: str) -> Optional[Video]:
        try:
            if not item or not isinstance(item, dict):
                return None
            video = item.get("video", {}) or {}
            stats = item.get("stats", {}) or item.get("statistics", {}) or {}
            music_info = item.get("music", {}) or item.get("musicInfo", {}) or {}
            desc = item.get("desc", "") or item.get("description", "") or ""
            video_id = item.get("id", "") or item.get("video_id", "") or ""

            if not video_id:
                return None

            hashtags = []
            text_extra = item.get("textExtra", []) or item.get("text_extra", [])
            for te in text_extra:
                if isinstance(te, dict) and te.get("hashtagName"):
                    hashtags.append(te["hashtagName"])
            if not hashtags and desc:
                hashtags = re.findall(r"#(\w+)", desc)

            create_time = item.get("createTime", 0) or item.get("create_time", 0)
            if create_time:
                try:
                    from datetime import datetime
                    create_time = datetime.fromtimestamp(int(create_time)).strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    pass

            video_location = (
                item.get("location")
                or item.get("locationCreated")
                or item.get("place")
                or video.get("location")
                or video.get("place")
                or item.get("geolocation")
            )
            if isinstance(video_location, dict):
                video_location = video_location.get("shortName") or video_location.get("name") or video_location.get("address")

            return Video(
                account_id=username,
                caption=desc.strip() or None,
                upload_date=str(create_time) if create_time else None,
                video_url=(
                    video.get("playAddr", "")
                    or video.get("downloadAddr", "")
                    or f"{self.BASE_URL}/@{username}/video/{video_id}"
                ),
                views=_safe_int(stats.get("playCount") or stats.get("views")),
                likes=_safe_int(stats.get("diggCount") or stats.get("likes")),
                comments=_safe_int(stats.get("commentCount") or stats.get("comments")),
                shares=_safe_int(stats.get("shareCount") or stats.get("shares")),
                duration=_safe_int(video.get("duration")),
                hashtags=", ".join(hashtags) if hashtags else None,
                music=(
                    music_info.get("title")
                    or (music_info.get("music") or {}).get("title")
                    or music_info.get("name")
                    if isinstance(music_info, dict)
                    else None
                ),
                video_location=str(video_location) if video_location else None,
            )
        except Exception:
            return None

    def _parse_from_dom(self, page: Page, username: str) -> Optional[Account]:
        try:
            page_text = page.inner_text("body") or ""
            html = page.content()

            if "couldn't find this account" in page_text.lower() or "this account doesn't exist" in page_text.lower():
                return None

            nickname = self._extract_by_regex(html, [
                r'<title>(.*?)\s*\(@',
                r'<title>(.*?)\s*-\s*TikTok',
                r'"nickname"\s*:\s*"([^"]+)"',
            ]) or username

            if not nickname or len(nickname) > 100 or "<" in nickname or ">" in nickname:
                self.logger.debug(f"  Nickname tidak valid: {nickname[:50]}")
                return None

            bio = self._extract_by_regex(html, [
                r'"signature"\s*:\s*"((?:[^"\\]|\\.)*)"',
                r'"bio"\s*:\s*"((?:[^"\\]|\\.)*)"',
            ]) or ""
            if bio and len(bio) > 2000:
                bio = ""

            profile_location = self._extract_by_regex(html, [
                r'"location"\s*:\s*"((?:[^"\\]|\\.)*)"',
                r'"region"\s*:\s*"((?:[^"\\]|\\.)*)"',
            ])

            followers = self._extract_num(html, r'"followerCount"\s*:\s*(\d+)')
            following = self._extract_num(html, r'"followingCount"\s*:\s*(\d+)')
            total_likes = self._extract_num(html, r'"heartCount"\s*:\s*(\d+)')
            video_count = self._extract_num(html, r'"videoCount"\s*:\s*(\d+)')

            if followers is None:
                m = re.search(r'(\d[\d,.]*)\s*(?:Followers|Pengikut)', page_text, re.IGNORECASE)
                if m:
                    followers = self._parse_count(m.group(1))

            if following is None:
                m = re.search(r'(\d[\d,.]*)\s*(?:Following|Mengikuti)', page_text, re.IGNORECASE)
                if m:
                    following = self._parse_count(m.group(1))

            if total_likes is None:
                m = re.search(r'(\d[\d,.]*)\s*(?:Likes|Suka)', page_text, re.IGNORECASE)
                if m:
                    total_likes = self._parse_count(m.group(1))

            verified = bool(re.search(r'"verified"\s*:\s*true', html))
            private = bool(re.search(r'"privateAccount"\s*:\s*true', html))

            social = extract_social_media(bio)
            email = extract_email(bio)

            if followers is None and following is None and video_count is None:
                self.logger.debug(f"  Tidak ada data statistik di DOM untuk @{username}")
                return None

            return Account(
                username=username, unique_id=username,
                nickname=nickname or None, bio=bio.strip()[:500] or None,
                profile_url=f"{self.BASE_URL}/@{username}",
                followers=followers, following=following,
                total_likes=total_likes, video_count=video_count,
                verified=verified, private_account=private,
                email=email, website=social.get("website"),
                instagram=social.get("instagram"), youtube=social.get("youtube"),
                linktree=social.get("linktree"), whatsapp=social.get("whatsapp"),
                facebook=social.get("facebook"),
                profile_location=profile_location,
            )
        except Exception:
            return None

    def _handle_popups(self, page: Page):
        try:
            for sel in ['[data-e2e="close-modal"]', '[aria-label="Close"]', '[class*="close"]']:
                for el in page.query_selector_all(sel):
                    try:
                        if el.is_visible():
                            el.click()
                            page.wait_for_timeout(300)
                    except Exception:
                        pass
        except Exception:
            pass
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass

    def _is_blocked_or_login(self, page: Page) -> bool:
        try:
            url = page.url.lower()
            if url.startswith("https://www.tiktok.com/login"):
                return True
            body = ""
            try:
                body = (page.inner_text("body") or "").lower()
            except Exception:
                pass
            login_phrases = [
                "log in to continue",
                "please log in",
                "sign in to tiktok",
            ]
            for phrase in login_phrases:
                if phrase in body:
                    content_len = len(body)
                    self.logger.debug(f"  Login page detected (body length: {content_len})")
                    return True
            return False
        except Exception:
            return False

    def _is_user_not_found(self, page: Page) -> bool:
        try:
            body = (page.inner_text("body") or "").lower()
            for p in ["couldn't find this account", "this account doesn't exist",
                       "page not found", "user not found"]:
                if p in body:
                    return True
            return False
        except Exception:
            return False

    def _detect_attributes(self, account: Account, videos: List[Video]):
        captions = [v.caption for v in videos if v.caption]
        all_hashtags = []
        for v in videos:
            if v.hashtags:
                all_hashtags.extend(t.strip() for t in v.hashtags.split(","))

        video_locations = [v.video_location for v in videos if v.video_location]

        loc, src = self.location_detector.detect(
            profile_location=account.profile_location,
            video_locations=video_locations or None,
            bio=account.bio, nickname=account.nickname,
            username=account.username,
            captions=captions or None, hashtags=all_hashtags or None,
        )
        account.location_detected = loc
        account.location_source = src

        ck = self.indicator_detector.detect_creator(account.bio)
        if ck:
            account.creator_keywords_found = ", ".join(ck)
        bi = self.indicator_detector.detect_business(account.bio)
        if bi:
            account.business_indicators_found = ", ".join(bi)

    def _detect_monetization(self, account: Account, videos: List[Video],
                              api_data: Dict[str, Any]):
        monetized = False
        has_shop = account.has_tiktok_shop or False
        signals = []

        raw_user = api_data.get("user") or {}
        raw_videos = api_data.get("videos") or {}

        for field, label in MONETIZATION_API_FIELDS.items():
            val = raw_user.get(field)
            if val is True or val == 1 or (isinstance(val, str) and val.lower() == "true"):
                monetized = True
                signals.append(label)

        if raw_user.get("isUnderAge18") is False:
            monetized = True
            signals.append("Eligible monetisasi (18+)")

        if self.indicator_detector.detect_monetization(account.bio):
            monetized = True
            signals.append("Keyword monetisasi di bio")

        if account.email:
            monetized = True
            signals.append("Email bisnis")

        if account.business_account:
            monetized = True
            signals.append("Akun bisnis")

        sponsored_captions = self.indicator_detector.detect_sponsored_hashtags(
            [v.caption for v in videos]
        )
        if sponsored_captions:
            monetized = True
            signals.append("Hashtag sponsored di video")

        for vid, item in raw_videos.items():
            if not isinstance(item, dict):
                continue
            for key in COMMERCE_VIDEO_KEYS:
                if item.get(key):
                    monetized = True
                    signals.append(f"Commerce di video ({key})")
                    break

        if self.indicator_detector.detect_shop(account.bio):
            has_shop = True

        if self.indicator_detector.detect_shop_in_captions([v.caption for v in videos]):
            has_shop = True

        if signals:
            self.logger.debug(f"  Monetisasi signals: {', '.join(signals)}")

        account.monetization = monetized
        account.has_tiktok_shop = has_shop

    def _calculate_statistics(self, account: Account, videos: List[Video]):
        if not videos:
            return

        video_stats_count = 0
        total_engagement = 0

        for v in videos:
            likes = v.likes or 0
            comments = v.comments or 0
            shares = v.shares or 0
            if likes > 0 or comments > 0 or shares > 0:
                total_engagement += likes + comments + shares
                video_stats_count += 1

        views = [v.views for v in videos if v.views is not None]
        if views:
            account.average_views = round(sum(views) / len(views), 2)

        likes_list = [v.likes for v in videos if v.likes is not None]
        if likes_list:
            account.average_likes = round(sum(likes_list) / len(likes_list), 2)

        comments_list = [v.comments for v in videos if v.comments is not None]
        if comments_list:
            account.average_comments = round(sum(comments_list) / len(comments_list), 2)

        shares_list = [v.shares for v in videos if v.shares is not None]
        if shares_list:
            account.average_shares = round(sum(shares_list) / len(shares_list), 2)

        if video_stats_count > 0 and account.followers and account.followers > 0:
            avg_per_post = total_engagement / video_stats_count
            account.engagement_rate = round((avg_per_post / account.followers) * 100, 4)

    def _classify_account(self, videos: List[Video]) -> str:
        captions = []
        for v in videos:
            if v.caption:
                captions.append(v.caption.lower())
        if not captions:
            return "personal"

        scores = {"travel": 0, "foodvloger": 0, "lifestyle": 0, "affiliate": 0}

        for caption in captions:
            for cls_name, keywords in CLASSIFICATION_KEYWORDS.items():
                if not keywords:
                    continue
                words_lower = caption.lower()
                for kw in keywords:
                    if kw in words_lower:
                        scores[cls_name] += 1

        best = max(scores, key=scores.get)
        if scores[best] == 0:
            return "personal"
        return best

    def _scrape_follow_page(self, username: str, follow_type: str, max_users: int) -> List[str]:
        usernames: Set[str] = set()
        page = self.browser.new_page()

        def on_response(response):
            try:
                if not response.ok:
                    return
                ctype = response.headers.get("content-type", "")
                if "application/json" not in ctype:
                    return
                data = response.json()
                if not isinstance(data, dict):
                    return

                for key in ("userList", "followers", "following"):
                    ulist = data.get(key, [])
                    if isinstance(ulist, list):
                        for item in ulist:
                            if not isinstance(item, dict):
                                continue
                            user = item.get("user", item)
                            if isinstance(user, dict):
                                uid = user.get("uniqueId")
                                if uid and len(uid) > 1:
                                    usernames.add(uid)

                body = data.get("body")
                if isinstance(body, dict):
                    for key in ("userList", "followers", "following"):
                        ulist = body.get(key, [])
                        if isinstance(ulist, list):
                            for item in ulist:
                                if not isinstance(item, dict):
                                    continue
                                user = item.get("user", item)
                                if isinstance(user, dict):
                                    uid = user.get("uniqueId")
                                    if uid and len(uid) > 1:
                                        usernames.add(uid)
            except Exception:
                pass

        page.on("response", on_response)

        try:
            url = f"{self.BASE_URL}/@{username}/{follow_type}"
            self.logger.debug(f"  Navigasi {follow_type}: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=self.settings.PAGE_LOAD_TIMEOUT)
            self._handle_popups(page)
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass
            page.wait_for_timeout(3000)

            if self._is_blocked_or_login(page):
                self.logger.warning(f"  Login required for {follow_type} @{username}")
                page.remove_listener("response", on_response)
                page.close()
                return []

            scrolls_without_new = 0
            prev_count = len(usernames)

            for i in range(30):
                try:
                    page.evaluate("window.scrollBy(0, window.innerHeight * 2)")
                except Exception:
                    break
                page.wait_for_timeout(2000)

                current = len(usernames)
                if current > prev_count:
                    self.logger.debug(f"    Scroll {i+1}: +{current - prev_count} user (total: {current})")
                    scrolls_without_new = 0
                    prev_count = current
                else:
                    scrolls_without_new += 1
                    self.logger.debug(f"    Scroll {i+1}: tidak ada user baru ({scrolls_without_new}/3)")

                if scrolls_without_new >= 3:
                    break
                if current >= max_users:
                    break

        except Exception as e:
            self.logger.error(f"  Error {follow_type} @{username}: {e}")
        finally:
            try:
                page.remove_listener("response", on_response)
                page.close()
            except Exception:
                pass

        exclude = {"tiktok", "login", "signup", "explore", "messages",
                    "settings", "feedback", "about", "trending",
                    "shop", "live", "upload", "business", "creator"}
        return [u for u in usernames if u.lower() not in exclude and u.lower() != username.lower()][:max_users]

    def _scrape_followers(self, username: str) -> List[str]:
        return self._scrape_follow_page(username, "followers", self.settings.MAX_FOLLOWERS_PER_ACCOUNT)

    def _scrape_following(self, username: str) -> List[str]:
        return self._scrape_follow_page(username, "following", self.settings.MAX_FOLLOWING_PER_ACCOUNT)

    def _expand_network(self):
        self.logger.info("=" * 60)
        self.logger.info("NETWORK EXPANSION: BFS dari akun Banyumas")
        self.logger.info("=" * 60)

        seed_rows = self.db.conn.execute(
            "SELECT username FROM accounts WHERE location_detected IS NOT NULL"
        ).fetchall()

        if not seed_rows:
            self.logger.warning("Tidak ada akun Banyumas untuk di-expand")
            return

        queue = deque()
        seen = set(self.scraped_accounts)

        for (uname,) in seed_rows:
            if uname not in seen:
                queue.append((uname, 0))
                seen.add(uname)

        self.logger.info(f"Seed: {len(queue)} akun Banyumas untuk ekspansi (depth max: {self.settings.NETWORK_EXPANSION_DEPTH})")
        new_total = 0

        while queue and new_total < self.settings.MAX_NETWORK_ACCOUNTS:
            current_uname, depth = queue.popleft()
            self.logger.info(f"[Depth {depth+1}/{self.settings.NETWORK_EXPANSION_DEPTH}] @{current_uname}")

            followers = self._scrape_followers(current_uname)
            self.logger.info(f"  Followers: {len(followers)}")
            self.browser.random_delay(self.settings.MIN_DELAY, self.settings.MAX_DELAY)

            following = self._scrape_following(current_uname)
            self.logger.info(f"  Following: {len(following)}")

            for uid in set(followers + following):
                if uid in seen:
                    continue
                seen.add(uid)

                if self.db.account_exists(uid):
                    continue

                try:
                    self._scrape_account(uid)
                    self.scraped_accounts.add(uid)
                    new_total += 1
                    self.logger.info(f"  +1 akun baru ({new_total}/{self.settings.MAX_NETWORK_ACCOUNTS})")

                    row = self.db.conn.execute(
                        "SELECT location_detected FROM accounts WHERE username = ?", (uid,)
                    ).fetchone()
                    if row and row[0] and depth + 1 < self.settings.NETWORK_EXPANSION_DEPTH:
                        queue.append((uid, depth + 1))

                    self.browser.random_delay(self.settings.MIN_DELAY, self.settings.MAX_DELAY)
                except Exception as e:
                    self.logger.error(f"  Gagal scrape @{uid}: {e}")

            self.browser.random_delay(self.settings.MIN_DELAY, self.settings.MAX_DELAY)

        self.logger.info(f"Network expansion selesai. Total akun baru: {new_total}")

    @staticmethod
    def _extract_by_regex(html: str, patterns: List[str]) -> Optional[str]:
        for p in patterns:
            m = re.search(p, html, re.DOTALL)
            if m:
                v = m.group(1)
                v = v.replace("\\n", "\n").replace("\\t", "\t").replace("\\\"", "\"").replace("\\\\", "\\")
                v = re.sub(r'\\u[0-9a-fA-F]{4}', '', v)
                if v and not v.isspace():
                    return v
        return None

    @staticmethod
    def _extract_num(html: str, pattern: str) -> Optional[int]:
        m = re.search(pattern, html)
        if m:
            try:
                return int(m.group(1))
            except (ValueError, TypeError):
                pass
        return None

    @staticmethod
    def _parse_count(text: str) -> Optional[int]:
        if not text:
            return None
        raw = text.strip().lower().replace(" ", "")
        mult = 1
        if raw.endswith("jt"):
            mult = 1000000; raw = raw.replace("jt", "").replace(",", ".")
        elif raw.endswith("rb"):
            mult = 1000; raw = raw.replace("rb", "").replace(",", ".")
        elif raw.endswith("m"):
            mult = 1000000; raw = raw[:-1].replace(",", "")
        elif raw.endswith("k"):
            mult = 1000; raw = raw[:-1].replace(",", "")
        else:
            if any(c.isalpha() for c in raw):
                raw = re.sub(r'[^\d.,]', '', raw)
            raw = raw.replace(",", "")
            if "." in raw:
                raw = raw.replace(".", "")
        try:
            return int(float(raw) * mult)
        except (ValueError, TypeError):
            return None


def _safe_int(value) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _debug_page(page, logger, label: str):
    try:
        logger.debug(f"  DEBUG [{label}]: URL={page.url}")
        html = page.content()
        logger.debug(f"  DEBUG [{label}]: HTML length={len(html)}")
        body = page.inner_text("body")[:200]
        logger.debug(f"  DEBUG [{label}]: body start={body[:100]}")
    except Exception:
        pass
