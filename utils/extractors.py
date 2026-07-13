import re
from typing import Optional, Dict, List


def extract_email(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    match = re.search(pattern, text)
    return match.group(0) if match else None


def extract_website(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    pattern = r"https?://[^\s,;]+"
    match = re.search(pattern, text)
    return match.group(0) if match else None


def extract_links(text: Optional[str]) -> List[str]:
    if not text:
        return []
    pattern = r"https?://[^\s,;]+"
    return re.findall(pattern, text)


def extract_social_media(text: Optional[str]) -> Dict[str, Optional[str]]:
    result = {
        "instagram": None,
        "youtube": None,
        "linktree": None,
        "whatsapp": None,
        "facebook": None,
        "shopee": None,
        "tokopedia": None,
        "telegram": None,
        "website": None,
    }
    if not text:
        return result

    text_lower = text.lower()

    insta_match = re.search(
        r"(?:instagram|ig)\s*[:：]?\s*@?(\w[\w.]*)",
        text,
        re.IGNORECASE,
    )
    if insta_match:
        result["instagram"] = insta_match.group(1)

    insta_link = re.search(
        r"https?://(?:www\.)?instagram\.com/([^\s/]+)",
        text,
        re.IGNORECASE,
    )
    if insta_link:
        result["instagram"] = insta_link.group(1)

    yt_match = re.search(
        r"(?:youtube|yt)\s*[:：]?\s*@?(\w[\w.]*)",
        text,
        re.IGNORECASE,
    )
    if yt_match:
        result["youtube"] = yt_match.group(1)

    yt_link = re.search(
        r"https?://(?:www\.)?(?:youtube\.com|youtu\.be)/([@\w-]+)",
        text,
        re.IGNORECASE,
    )
    if yt_link:
        result["youtube"] = yt_link.group(1)

    linktree_link = re.search(
        r"https?://(?:www\.)?linktr\.ee/([^\s/]+)",
        text,
        re.IGNORECASE,
    )
    if linktree_link:
        result["linktree"] = linktree_link.group(1)
    elif "linktr.ee" in text_lower:
        result["linktree"] = "yes"

    wa_match = re.search(
        r"(?:whatsapp|wa)\s*[:：]?\s*(\+?\d[\d\s-]{8,})",
        text,
        re.IGNORECASE,
    )
    if wa_match:
        result["whatsapp"] = wa_match.group(1).strip()

    wa_link = re.search(
        r"https?://(?:api\.)?wa\.me/([^\s/]+)",
        text,
        re.IGNORECASE,
    )
    if wa_link:
        result["whatsapp"] = wa_link.group(1)

    fb_match = re.search(
        r"(?:facebook|fb)\s*[:：]?\s*@?(\w[\w.]*)",
        text,
        re.IGNORECASE,
    )
    if fb_match:
        result["facebook"] = fb_match.group(1)

    fb_link = re.search(
        r"https?://(?:www\.)?(?:facebook\.com|fb\.com)/([^\s/]+)",
        text,
        re.IGNORECASE,
    )
    if fb_link:
        result["facebook"] = fb_link.group(1)

    shopee_match = re.search(
        r"https?://(?:www\.)?shopee\.co\.id/([^\s/]+)",
        text,
        re.IGNORECASE,
    )
    if shopee_match:
        result["shopee"] = shopee_match.group(1)
    elif "shopee" in text_lower:
        result["shopee"] = "yes"

    toko_match = re.search(
        r"https?://(?:www\.)?tokopedia\.com/([^\s/]+)",
        text,
        re.IGNORECASE,
    )
    if toko_match:
        result["tokopedia"] = toko_match.group(1)
    elif "tokopedia" in text_lower:
        result["tokopedia"] = "yes"

    telegram_match = re.search(
        r"(?:telegram|t\.me)\s*[:：]?\s*@?(\w[\w.]*)",
        text,
        re.IGNORECASE,
    )
    if telegram_match:
        result["telegram"] = telegram_match.group(1)

    tg_link = re.search(
        r"https?://(?:www\.)?t\.me/([^\s/]+)",
        text,
        re.IGNORECASE,
    )
    if tg_link:
        result["telegram"] = tg_link.group(1)

    website = extract_website(text)
    if website:
        result["website"] = website

    return result
