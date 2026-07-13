from typing import List, Optional


class IndicatorDetector:
    def __init__(self, creator_keywords: List[str], business_indicators: List[str],
                 monetization_keywords: Optional[List[str]] = None,
                 shop_keywords: Optional[List[str]] = None):
        self.creator_keywords = creator_keywords
        self.business_indicators = business_indicators
        self.monetization_keywords = monetization_keywords or []
        self.shop_keywords = shop_keywords or []

    def detect_creator(self, bio: Optional[str]) -> List[str]:
        found = []
        if not bio:
            return found
        bio_lower = bio.lower()
        for kw in self.creator_keywords:
            if kw.lower() in bio_lower:
                found.append(kw)
        return found

    def detect_business(self, bio: Optional[str]) -> List[str]:
        found = []
        if not bio:
            return found
        bio_lower = bio.lower()
        for indicator in self.business_indicators:
            if indicator.lower() in bio_lower:
                found.append(indicator)
        return found

    def detect_monetization(self, bio: Optional[str]) -> bool:
        if not bio:
            return False
        bio_lower = bio.lower()
        for kw in self.monetization_keywords:
            if kw.lower() in bio_lower:
                return True
        return False

    def detect_shop(self, bio: Optional[str]) -> bool:
        if not bio:
            return False
        bio_lower = bio.lower()
        for kw in self.shop_keywords:
            if kw.lower() in bio_lower:
                return True
        return False

    def detect_shop_in_captions(self, captions: List[Optional[str]]) -> bool:
        for cap in captions:
            if not cap:
                continue
            cap_lower = cap.lower()
            for kw in self.shop_keywords:
                if kw.lower() in cap_lower:
                    return True
        return False

    def detect_sponsored_hashtags(self, captions: List[Optional[str]]) -> bool:
        sponsored = ["ad", "sponsored", "paidpartnership", "gifted", "berbayar"]
        for cap in captions:
            if not cap:
                continue
            cap_lower = cap.lower()
            for tag in sponsored:
                if f"#{tag}" in cap_lower:
                    return True
        return False
