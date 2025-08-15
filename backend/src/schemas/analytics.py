"""
Pydantic schemas for analytics API responses.
"""
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime


class BotMetrics(BaseModel):
    """Basic bot usage metrics."""
    total_conversations: int
    total_messages: int
    user_messages: int
    assistant_messages: int
    unique_users: int
    documents_count: int
    avg_response_time: Optional[float] = None
    total_tokens: Optional[int] = None


class DailyActivity(BaseModel):
    """Daily activity data point."""
    date: str
    message_count: int


class TopUser(BaseModel):
    """Top user by activity."""
    username: str
    full_name: Optional[str]
    message_count: int


class BotAnalytics(BaseModel):
    """Comprehensive bot analytics response."""
    bot_id: str
    period_days: int
    metrics: BotMetrics
    daily_activity: List[DailyActivity]
    top_users: List[TopUser]


class UserMetrics(BaseModel):
    """User dashboard metrics."""
    total_bots: int
    owned_bots: int
    total_conversations: int
    total_messages: int
    messages_sent: int
    messages_received: int


class BotActivity(BaseModel):
    """Bot activity summary."""
    bot_id: str
    bot_name: str
    message_count: int
    conversation_count: int


class RecentConversation(BaseModel):
    """Recent conversation summary."""
    session_id: str
    title: Optional[str]
    bot_name: str
    message_count: int
    created_at: str
    updated_at: str


class UserDashboardAnalytics(BaseModel):
    """User dashboard analytics response."""
    user_id: str
    period_days: int
    metrics: UserMetrics
    bot_activity: List[BotActivity]
    recent_conversations: List[RecentConversation]


class ActivityLogUser(BaseModel):
    """User information in activity log."""
    username: Optional[str]
    full_name: Optional[str]


class ActivityLogEntry(BaseModel):
    """Activity log entry."""
    id: str
    action: str
    details: Optional[Dict[str, Any]]
    created_at: str
    user: Optional[ActivityLogUser]


class ActivityLogsResponse(BaseModel):
    """Activity logs response."""
    activity_logs: List[ActivityLogEntry]


class SystemMetrics(BaseModel):
    """System-wide metrics."""
    total_users: int
    total_bots: int
    total_conversations: int
    total_messages: int
    total_documents: int
    active_users: int


class MostActiveBot(BaseModel):
    """Most active bot summary."""
    bot_id: str
    bot_name: str
    message_count: int


class SystemDailyActivity(BaseModel):
    """System daily activity."""
    date: str
    message_count: int
    active_users: int


class SystemAnalytics(BaseModel):
    """System-wide analytics response."""
    period_days: int
    metrics: SystemMetrics
    most_active_bots: List[MostActiveBot]
    daily_activity: List[SystemDailyActivity]


class ExportMessage(BaseModel):
    """Exported message data."""
    id: str
    role: str
    content: str
    metadata: Optional[Dict[str, Any]]
    created_at: str


class ExportConversation(BaseModel):
    """Exported conversation data."""
    session_id: str
    title: Optional[str]
    created_at: str
    messages: List[ExportMessage]


class ExportDocument(BaseModel):
    """Exported document metadata."""
    id: str
    filename: str
    file_size: Optional[int]
    mime_type: Optional[str]
    chunk_count: int
    created_at: str


class ExportActivityLog(BaseModel):
    """Exported activity log entry."""
    id: str
    action: str
    details: Optional[Dict[str, Any]]
    created_at: str


class ExportBot(BaseModel):
    """Exported bot data."""
    id: str
    name: str
    description: Optional[str]
    system_prompt: str
    llm_provider: str
    llm_model: str
    created_at: str
    updated_at: str


class ExportMetadata(BaseModel):
    """Export metadata."""
    exported_at: str
    exported_by: str
    format: str


class BotExportData(BaseModel):
    """Complete bot export data."""
    bot: ExportBot
    export_metadata: ExportMetadata
    conversations: Optional[List[ExportConversation]] = None
    documents: Optional[List[ExportDocument]] = None
    activity_logs: Optional[List[ExportActivityLog]] = None


class AnalyticsSummaryMetrics(BaseModel):
    """Analytics summary metrics."""
    total_bots: int
    owned_bots: int
    messages_this_week: int
    messages_this_month: int
    conversations_this_week: int
    conversations_this_month: int


class AnalyticsSummary(BaseModel):
    """Analytics summary response."""
    summary: AnalyticsSummaryMetrics
    recent_activity: List[RecentConversation]