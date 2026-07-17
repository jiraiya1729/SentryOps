import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, JSON, DateTime, Boolean, Text
from app.db.database import Base

class Dashboard(Base):
    __tablename__ = "dashboards"

    id = Column(String, primary_key=True, default = lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    layout = Column(JSON, default=list)

    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class DashboardPanel(Base):
    __tablename__ = "dashboard_panels"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    dashboard_id = Column(String, nullable=False)
    title = Column(String(255), nullable=False)
    panel_type = Column(String(50), nullable=False)
    query_config = Column(JSON, nullable=False)

    display_config = Column(JSON, default=dict)

    position = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    