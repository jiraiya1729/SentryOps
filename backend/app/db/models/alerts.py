import uuid
from datetime import datetime, timezone

from sqlalchemy import (Column, String, Integer, Float, Boolean, DateTime, JSON, Enum, ForeignKey, Text, Index)
from sqlalchemy.orm import relationship

from app.db.database import Base


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(String, primary_key=True, default = lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    enabled = Column(Boolean, default=True)
    severity = Column(String(20), default = "warning")

    condition_type = Column(String(50), nullable=False)
    condition_config = Column(JSON, nullable=False)

    evaluation_interval_seconds = Column(Integer, default=60)
    for_duration_seconds = Column(Integer, default = 0)


    namespace = Column(String(255), nullable=True)
    labels = Column(JSON, default=dict)

    notification_channels = Column(JSON, default=list)
    notify_on_resolve = Column(Boolean, default=True)
    repeat_interval_seconds = Column(String, nullable=True)

    auto_investigate = Column(Boolean, default=False)
    runbook_id = Column(String, nullable = True)


    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    last_evaluated_at = Column(DateTime, nullable = True)

    instances = relationship("AlertInstance", back_populates = "rule", cascade = "all, delete-orphan")

    __table_args__ = (
        Index("idx_alert_rules_enabled", "enabled"),
        Index("idx_alert_rules_condition_type", "condition-type"),
    )


class AlertInstance(Base):
    __tablename__ = "alert_instances"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_id = Column(String, ForeignKey("alert_rules.id"), nullable=False)
    state = Column(String(20), default="pending") 
    severity = Column(String(20), nullable=False)


    labels = Column(JSON, default=dict)  
    annotations = Column(JSON, default=dict)  
    value = Column(Float, nullable=True)

   
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    fired_at = Column(DateTime, nullable=True)  
    resolved_at = Column(DateTime, nullable=True)
    last_notified_at = Column(DateTime, nullable=True)
    investigation_id = Column(String, nullable=True)
    rule = relationship("AlertRule", back_populates="instances")

    __table_args__ = (
        Index("idx_alert_instances_state", "state"),
        Index("idx_alert_instances_rule", "rule_id"),
    )


class AlertHistory(Base):
    __tablename__ = "alert_history"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_id = Column(String, nullable=False)
    instance_id = Column(String, nullable=False)
    previous_state = Column(String(20))
    new_state = Column(String(20), nullable=False)
    timestamp = Column(DateTime, default = lambda:datetime.now(timezone.utc))
    value = Column(Float, nullable=True)
    annotations = Column(JSON, default=dict)

    __table_args__ = (
        Index("idx_alert_history_rule", "rule_id"),
        Index("idx_alert_history_timestamp", timestamp)
    )



