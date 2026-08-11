"""
Canonical Pydantic Data Schemas matching requirements.
"""

from enum import Enum
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class PricingModelEnum(str, Enum):
    FREE = "FREE"
    FREEMIUM = "FREEMIUM"
    PAID = "PAID"
    ENTERPRISE = "ENTERPRISE"


class SourceInfo(BaseModel):
    name: str = Field(..., description="Name of the source site")
    url: str = Field(..., description="Original source URL")


class StartupContentData(BaseModel):
    employeeCount: Optional[int] = Field(None, description="Number of employees if available")
    description: Optional[str] = Field(None, description="Brief startup description")
    category: Optional[str] = Field(None, description="Domain/Category (e.g. LLM, Vision, Infrastructure)")


class StartupContent(BaseModel):
    entityName: str = Field(..., description="Startup or company name")
    data: Optional[StartupContentData] = Field(default_factory=StartupContentData)


class StartupEntity(BaseModel):
    schemaVersion: str = "1.0"
    recordType: str = "STARTUP"
    source: SourceInfo
    content: StartupContent
    collectedAt: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class ProductContent(BaseModel):
    startupName: str = Field(..., description="Canonical parent startup name")
    productName: str = Field(..., description="Name of the product")
    pricingModel: PricingModelEnum = Field(PricingModelEnum.FREEMIUM, description="Pricing tier")
    description: Optional[str] = Field(None, description="Short product summary")


class ProductEntity(BaseModel):
    schemaVersion: str = "1.0"
    recordType: str = "PRODUCT"
    source: SourceInfo
    content: ProductContent
    collectedAt: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class ResearchPaperContent(BaseModel):
    title: str = Field(..., description="Title of the research paper")
    authors: List[str] = Field(default_factory=list, description="List of author names")
    paper_url: str = Field(..., description="Link to ArXiv/PDF page")
    github_url: Optional[str] = Field(None, description="Link to associated code repo")
    github_stars: Optional[int] = Field(0, description="Current number of stars on GitHub repo")
    published_date: str = Field(..., description="ISO-8601 publication date")


class ResearchPaperEntity(BaseModel):
    schemaVersion: str = "1.0"
    recordType: str = "RESEARCH_PAPER"
    source: SourceInfo
    content: ResearchPaperContent
    collectedAt: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class JobContent(BaseModel):
    company: str = Field(..., description="Canonical company name")
    title: str = Field(..., description="Job role title")
    date: str = Field(..., description="ISO-8601 publication date")
    is_remote: bool = Field(False, description="Remote eligibility")
    role_family: str = Field("Engineering", description="Functional category (e.g. Engineering, Research)")
    url: Optional[str] = Field(None, description="Job application / post link")


class JobEntity(BaseModel):
    schemaVersion: str = "1.0"
    recordType: str = "JOB"
    source: SourceInfo
    content: JobContent
    collectedAt: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class NewsContent(BaseModel):
    title: str = Field(..., description="Article title")
    source_name: str = Field(..., description="Publication source name")
    source_url: str = Field(..., description="Article URL")
    published_date: str = Field(..., description="ISO-8601 publication timestamp")
    full_text: Optional[str] = Field(None, description="Full-text content of the news article")
    summary: Optional[str] = Field(None, description="Brief summary")


class NewsEntity(BaseModel):
    schemaVersion: str = "1.0"
    recordType: str = "NEWS"
    source: SourceInfo
    content: NewsContent
    collectedAt: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class EntityMappingLog(BaseModel):
    raw_name: str
    canonical_name: str
    match_score: float
    method: str
    entity_type: str = "STARTUP"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
