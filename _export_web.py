import sqlite3
import json
import os
from collections import Counter

DB_PATH = "output/tiktok_data.db"
OUTPUT = "web"
WEB_SRC = os.path.join(os.path.dirname(__file__) or ".", "..", "web", "src")

STRING_FIELDS = [
    "username", "unique_id", "nickname", "bio", "profile_url", "avatar_url",
    "followers", "following", "total_likes", "video_count",
    "verified", "private_account", "business_account",
    "email", "website", "instagram", "youtube", "linktree", "whatsapp", "facebook",
    "profile_location", "location_detected", "location_source",
    "creator_keywords", "creator_keywords_found", "business_indicators_found",
    "live_detected", "has_tiktok_shop", "monetization",
    "average_views", "average_likes", "average_comments", "average_shares",
    "engagement_rate", "scraped_at",
]


def _str(val):
    if val is None:
        return ""
    if isinstance(val, bool):
        return "1" if val else "0"
    return str(val)


def main():
    os.makedirs(OUTPUT, exist_ok=True)
    if os.path.isdir(WEB_SRC):
        os.makedirs(WEB_SRC, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    accounts_rows = conn.execute("SELECT * FROM accounts ORDER BY followers DESC").fetchall()
    videos_rows = conn.execute("SELECT * FROM videos ORDER BY account_id, upload_date DESC").fetchall()

    accounts = []
    for r in accounts_rows:
        accounts.append({
            "username": r["username"],
            "unique_id": r["unique_id"],
            "nickname": r["nickname"],
            "bio": r["bio"] or "",
            "followers": r["followers"] or 0,
            "following": r["following"] or 0,
            "total_likes": r["total_likes"] or 0,
            "video_count": r["video_count"] or 0,
            "verified": bool(r["verified"]),
            "private_account": bool(r["private_account"]),
            "business_account": bool(r["business_account"]) if r["business_account"] is not None else "",
            "profile_url": r["profile_url"] or f"https://www.tiktok.com/@{r['username']}",
            "avatar_url": "",
            "profile_location": r["profile_location"],
            "location_detected": r["location_detected"],
            "location_source": r["location_source"],
            "email": r["email"] or "",
            "website": r["website"] or "",
            "instagram": r["instagram"] or "",
            "youtube": r["youtube"] or "",
            "linktree": r["linktree"] or "",
            "whatsapp": r["whatsapp"] or "",
            "facebook": r["facebook"] or "",
            "classification": r["classification"] or "personal",
            "product_count": r["product_count"] or 0,
            "creator_keywords_found": r["creator_keywords_found"] or "",
            "business_indicators_found": r["business_indicators_found"] or "",
            "live_detected": r["live_detected"],
            "has_tiktok_shop": bool(r["has_tiktok_shop"]),
            "monetization": bool(r["monetization"]),
            "engagement_rate": r["engagement_rate"],
            "average_views": r["average_views"],
            "average_likes": r["average_likes"],
            "average_comments": r["average_comments"],
            "average_shares": r["average_shares"],
            "scraped_at": r["scraped_at"],
        })
    with open(f"{OUTPUT}/accounts.json", "w", encoding="utf-8") as f:
        json.dump(accounts, f, ensure_ascii=False, indent=2)
    print(f"  accounts.json: {len(accounts)} akun")

    # Write web data.json (all string format for web app compatibility)
    web_accounts = []
    for a in accounts:
        obj = {k: _str(a.get(k)) for k in STRING_FIELDS}
        obj["classification"] = a["classification"] or "personal"
        obj["product_count"] = _str(a.get("product_count", 0))
        web_accounts.append(obj)
    web_path = os.path.join(WEB_SRC, "data.json")
    with open(web_path, "w", encoding="utf-8") as f:
        json.dump(web_accounts, f, ensure_ascii=False, indent=2)
    print(f"  {web_path}: {len(web_accounts)} akun (web format)")

    videos = []
    for r in videos_rows:
        videos.append({
            "account_id": r["account_id"],
            "caption": r["caption"],
            "video_url": r["video_url"],
            "views": r["views"] or 0,
            "likes": r["likes"] or 0,
            "comments": r["comments"] or 0,
            "shares": r["shares"] or 0,
            "upload_date": r["upload_date"],
            "hashtags": r["hashtags"],
            "video_location": r["video_location"],
            "scraped_at": r["scraped_at"],
        })
    with open(f"{OUTPUT}/videos.json", "w", encoding="utf-8") as f:
        json.dump(videos, f, ensure_ascii=False, indent=2)
    print(f"  videos.json: {len(videos)} video")

    active_accounts = [a for a in accounts if a["followers"] > 0]

    video_counts = Counter(a["classification"] for a in active_accounts)
    with_shop = sum(1 for a in active_accounts if a["has_tiktok_shop"])
    monetized = sum(1 for a in active_accounts if a["monetization"])

    with_location = [a for a in active_accounts if a["location_detected"]]
    top_locations = Counter(a["location_detected"] for a in with_location).most_common(20)
    top_followers = sorted(active_accounts, key=lambda a: a["followers"], reverse=True)[:20]

    per_class = dict(video_counts)
    for cls in ("travel", "foodvloger", "lifestyle", "affiliate", "personal"):
        per_class.setdefault(cls, 0)

    summary = {
        "total_accounts": len(active_accounts),
        "total_raw_accounts": len(accounts),
        "total_videos": len(videos),
        "accounts_per_class": per_class,
        "accounts_with_shop": with_shop,
        "accounts_monetized": monetized,
        "with_location": len(with_location),
        "classification_labels": list(per_class.keys()),
        "classification_values": list(per_class.values()),
        "top_locations": [{"name": loc, "count": cnt} for loc, cnt in top_locations],
        "top_accounts": [
            {
                "rank": i + 1,
                "username": a["username"],
                "followers": a["followers"],
                "nickname": a["nickname"],
                "classification": a["classification"],
                "location": a["location_detected"],
                "has_shop": a["has_tiktok_shop"],
                "monetization": a["monetization"],
            }
            for i, a in enumerate(top_followers)
        ],
    }
    with open(f"{OUTPUT}/summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"  summary.json: OK")

    conn.close()
    print(f"\nData siap di web/dashboard/ folder.")


if __name__ == "__main__":
    main()
