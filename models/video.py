from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class Video(BaseModel):
    account_id: str
    caption: Optional[str] = None
    upload_date: Optional[str] = None
    video_url: Optional[str] = None
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    duration: Optional[int] = None
    hashtags: Optional[str] = None
    music: Optional[str] = None
    video_location: Optional[str] = None
    scraped_at: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
