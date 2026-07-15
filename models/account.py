from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class Account(BaseModel):
    username: str
    unique_id: str
    nickname: Optional[str] = None
    bio: Optional[str] = None
    profile_url: Optional[str] = None
    avatar_url: Optional[str] = None
    followers: Optional[int] = None
    following: Optional[int] = None
    total_likes: Optional[int] = None
    video_count: Optional[int] = None
    verified: bool = False
    private_account: bool = False
    business_account: Optional[bool] = None
    email: Optional[str] = None
    website: Optional[str] = None
    instagram: Optional[str] = None
    youtube: Optional[str] = None
    linktree: Optional[str] = None
    whatsapp: Optional[str] = None
    facebook: Optional[str] = None
    profile_location: Optional[str] = None
    location_detected: Optional[str] = None
    location_source: Optional[str] = None
    creator_keywords: Optional[str] = None
    creator_keywords_found: Optional[str] = None
    business_indicators_found: Optional[str] = None
    live_detected: Optional[bool] = None
    has_tiktok_shop: Optional[bool] = None
    monetization: Optional[bool] = None
    average_views: Optional[float] = None
    average_likes: Optional[float] = None
    average_comments: Optional[float] = None
    average_shares: Optional[float] = None
    engagement_rate: Optional[float] = None
    classification: Optional[str] = None
    product_count: Optional[int] = None
    scraped_at: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
