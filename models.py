from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class Address:
    line1: str
    line2: Optional[str]
    city: str
    state: str
    zip: str
    country: str


@dataclass
class Submitter:
    name: str
    organization: Optional[str]
    representative: Optional[str]
    address: Address


@dataclass
class Attachment:
    title: str
    url: str


@dataclass
class CommentInfo:
    id: str
    tracking_number: str
    title: str
    agency: str
    dates: Dict[str, str]
    submitter: Submitter
    content: str
    attachments: List[Attachment]
    document_subtype: str
