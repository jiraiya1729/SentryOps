"""Create alert tables.

Revision ID: 003
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "alert_rules",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), default=""),
        sa.Column("enabled", sa.Boolean(), default=True),
        sa.Column("severity", sa.String(20), default="warning"),
        sa.Column("condition_type", sa.String(50), nullable=False),
        sa.Column("condition_config", sa.JSON(), nullable=False),
        sa.Column("evaluation_interval_seconds", sa.Integer(), default=60),
        sa.Column("for_duration_seconds", sa.Integer(), default=0),
        sa.Column("namespace", sa.String(255), nullable=True),
        sa.Column("labels", sa.JSON(), default=dict),
        sa.Column("notification_channels", sa.JSON(), default=list),
        sa.Column("notify_on_resolve", sa.Boolean(), default=True),
        sa.Column("repeat_interval_minutes", sa.Integer(), default=60),
        sa.Column("auto_investigate", sa.Boolean(), default=False),
        sa.Column("runbook_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("last_evaluated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("idx_alert_rules_enabled", "alert_rules", ["enabled"])
    op.create_index("idx_alert_rules_condition_type", "alert_rules", ["condition_type"])

    op.create_table(
        "alert_instances",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("rule_id", sa.String(), sa.ForeignKey("alert_rules.id"), nullable=False),
        sa.Column("state", sa.String(20), default="pending"),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("labels", sa.JSON(), default=dict),
        sa.Column("annotations", sa.JSON(), default=dict),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("fired_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("last_notified_at", sa.DateTime(), nullable=True),
        sa.Column("investigation_id", sa.String(), nullable=True),
    )
    op.create_index("idx_alert_instances_state", "alert_instances", ["state"])
    op.create_index("idx_alert_instances_rule", "alert_instances", ["rule_id"])

    op.create_table(
        "alert_history",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("rule_id", sa.String(), nullable=False),
        sa.Column("instance_id", sa.String(), nullable=False),
        sa.Column("previous_state", sa.String(20), nullable=True),
        sa.Column("new_state", sa.String(20), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("annotations", sa.JSON(), default=dict),
    )
    op.create_index("idx_alert_history_rule", "alert_history", ["rule_id"])
    op.create_index("idx_alert_history_timestamp", "alert_history", ["timestamp"])


def downgrade():
    op.drop_table("alert_history")
    op.drop_table("alert_instances")
    op.drop_table("alert_rules")