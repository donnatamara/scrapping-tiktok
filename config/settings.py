from dataclasses import dataclass, field
from typing import List


@dataclass
class Settings:
    SEARCH_KEYWORDS: List[str] = field(default_factory=lambda: [
        "Banyumas",
        "Purwokerto",
        "Ajibarang",
        "Sokaraja",
        "Baturraden",
        "Cilongok",
        "Wangon",
        "Kalibagor",
        "Kembaran",
        "Karanglewas",
        "Patikraja",
        "Sumbang",
        "Kemranjen",
        "Rawalo",
        "Lumbir",
        "Kebasen",
        "Banyumas Hits",
        "Purwokerto Hits",
        "Kuliner Purwokerto",
        "Kuliner Banyumas",
        "Cafe Purwokerto",
        "UMKM Banyumas",
        "Wisata Banyumas",
        "Explore Purwokerto",
        "Explore Banyumas",
        "Banyumas bisnis",
        "Banyumas jual",
        "Banyumas kreator",
        "Banyumas affiliate",
        "Banyumas usaha",
        "Banyumas dagang",
        "Banyumas produk",
        "Banyumas UMKM",
        "Purwokerto bisnis",
        "Purwokerto jual",
        "Purwokerto kreator",
        "Purwokerto affiliate",
        "Purwokerto usaha",
        "Purwokerto dagang",
        "Purwokerto produk",
        "Purwokerto UMKM",
        "jualan Banyumas",
        "jualan Purwokerto",
        "toko Banyumas",
        "toko Purwokerto",
        "usaha Banyumas",
        "usaha Purwokerto",
    ])

    HASHTAGS: List[str] = field(default_factory=lambda: [
        "banyumas",
        "purwokerto",
        "banyumashits",
        "purwokertohits",
        "kulinerpurwokerto",
        "kulinerbanyumas",
        "explorebanyumas",
        "explorepurwokerto",
        "fypbanyumas",
        "banyumasumkm",
        "waktunyabanyumas",
        "banyumasbisnis",
        "banyumasjual",
        "banyumaskreator",
        "banyumasaffiliate",
        "purwokertobisnis",
        "purwokertojual",
        "purwokertokreator",
        "purwokertoaffiliate",
        "affiliate",
        "marketing",
        "bisnis",
        "kontenkreator",
        "dagang",
        "contentcreator",
        "influencerindonesia",
        "jual",
        "promo",
        "usahamodal",
        "fypbisnis",
        "tiktokbisnis",
        "tiktokaffiliate",
        "tiktokshope",
        "promosi",
        "jualanonline",
    ])

    BANYUMAS_SUBDISTRICTS: List[str] = field(default_factory=lambda: [
        "Ajibarang",
        "Baturraden",
        "Banyumas",
        "Cilongok",
        "Gumelar",
        "Jatilawang",
        "Kalibagor",
        "Karanglewas",
        "Kebasen",
        "Kedung Banteng",
        "Kedungbanteng",
        "Kembaran",
        "Kemranjen",
        "Lumbir",
        "Pakuncen",
        "Patikraja",
        "Pekuncen",
        "Purwokerto Barat",
        "Purwokerto Selatan",
        "Purwokerto Timur",
        "Purwokerto Utara",
        "Purwojati",
        "Rawalo",
        "Simpiuh",
        "Sokaraja",
        "Somagede",
        "Sumbang",
        "Sumpyuh",
        "Tambak",
        "Wangon",
    ])

    CREATOR_KEYWORDS: List[str] = field(default_factory=lambda: [
        "creator",
        "content creator",
        "influencer",
        "affiliate",
        "host live",
        "ugc",
        "reviewer",
        "food reviewer",
        "beauty",
        "talent",
        "mcn",
        "endorsement",
        "collaboration",
        "business inquiry",
        "paid promote",
        "promotion",
        "review",
        "brand ambassador",
    ])

    BUSINESS_INDICATORS: List[str] = field(default_factory=lambda: [
        "email",
        "website",
        "instagram",
        "youtube",
        "linktree",
        "shopee",
        "tokopedia",
        "tiktok shop",
        "whatsapp",
        "telegram",
    ])

    MONETIZATION_KEYWORDS: List[str] = field(default_factory=lambda: [
        "creator marketplace",
        "creator next",
        "brand collaboration",
        "business inquiry",
        "endorsement",
        "affiliate",
        "commission",
        "sponsored",
        "partnership",
        "paid promote",
        "pr package",
        "pr review",
        "ugc",
        "collaboration",
        "brand deal",
    ])

    SHOP_KEYWORDS: List[str] = field(default_factory=lambda: [
        "tiktok shop",
        "tiktokshop",
        "shopee",
        "tokopedia",
        "keranjang kuning",
        "shop now",
        "link shop",
        "belanja",
        "order",
        "pesan",
    ])

    MAX_VIDEOS_PER_ACCOUNT: int = 99999
    HEADLESS: bool = False
    VIEWPORT_WIDTH: int = 1366
    VIEWPORT_HEIGHT: int = 768
    PAGE_LOAD_TIMEOUT: int = 30000
    ELEMENT_TIMEOUT: int = 10000
    MIN_DELAY: float = 2.0
    MAX_DELAY: float = 5.0
    MAX_RETRIES: int = 3
    DATABASE_PATH: str = "output/tiktok_data.db"
    ACCOUNTS_CSV: str = "output/accounts.csv"
    VIDEOS_CSV: str = "output/videos.csv"
    LOG_FILE: str = "logs/scraping.log"
    LOG_LEVEL: str = "INFO"
