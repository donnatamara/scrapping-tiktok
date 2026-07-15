from typing import Optional, Tuple, List


class LocationDetector:
    def __init__(self, subdistricts: List[str]):
        self.subdistricts_lower = {s.lower(): s for s in subdistricts}
        self.keywords = [
            "banyumas", "purwokerto",
        ]

    def detect(self, profile_location: Optional[str] = None,
               video_locations: Optional[List[str]] = None,
               bio: Optional[str] = None, nickname: Optional[str] = None,
               username: Optional[str] = None,
               captions: Optional[List[str]] = None,
               hashtags: Optional[List[str]] = None) -> Tuple[Optional[str], Optional[str]]:

        if profile_location:
            loc = self._match_location(profile_location)
            if loc:
                return loc, "profile_location"

        if video_locations:
            for loc_text in video_locations:
                loc = self._match_location(loc_text)
                if loc:
                    return loc, "video_location"

        if username:
            loc = self._match_location(username)
            if loc:
                return loc, "username"

        if bio:
            loc = self._match_location(bio)
            if loc:
                return loc, "bio"

        if nickname:
            loc = self._match_location(nickname)
            if loc:
                return loc, "nickname"

        if captions:
            for caption in captions:
                if caption:
                    loc = self._match_location(caption)
                    if loc:
                        return loc, "caption"

        if hashtags:
            for tag in hashtags:
                if tag:
                    loc = self._match_location(tag)
                    if loc:
                        return loc, "hashtag"

        return None, None

    def _match_location(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        for sub_lower, sub_orig in self.subdistricts_lower.items():
            if sub_lower in text_lower:
                return sub_orig

        for kw in self.keywords:
            if kw in text_lower:
                return kw.capitalize()

        return None

    def contains_banyumas_keyword(self, text: str) -> bool:
        if not text:
            return False
        text_lower = text.lower()
        if "banyumas" in text_lower:
            return True
        for sub_lower in self.subdistricts_lower:
            if sub_lower in text_lower:
                return True
        return False
