from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class AuditRecord(Base):
    """Append-only audit trail row (see TECH_SPEC.md Section 1:
    "Audit-log integrity"). Rows are written once and never updated in
    place -- a correction to a past audit is a new row with the same
    audit_id, not an UPDATE. No update/delete path exists in this codebase
    for this table by design.
    """

    __tablename__ = "audit_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    audit_id: Mapped[str] = mapped_column(String, index=True)
    regulatory_context: Mapped[str] = mapped_column(String)
    current_status: Mapped[str] = mapped_column(String)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
