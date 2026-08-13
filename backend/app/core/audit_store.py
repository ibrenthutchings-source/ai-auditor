import logging

from app.core.db import get_session
from app.models.db_models import AuditRecord
from app.models.schemas import AuditState

logger = logging.getLogger(__name__)


def persist_audit_record(state: AuditState) -> None:
    """Append the completed audit as a new row. Never raises -- a database
    outage must degrade to "this audit wasn't persisted" (logged), not a
    500 on an otherwise-successful /audit call. See AuditRecord for the
    append-only contract.
    """
    try:
        session = get_session()
        try:
            session.add(
                AuditRecord(
                    audit_id=state.audit_id,
                    regulatory_context=state.regulatory_context,
                    current_status=state.current_status,
                    payload=state.model_dump(mode="json"),
                )
            )
            session.commit()
        finally:
            session.close()
    except Exception:
        logger.warning("persist_audit_record: failed to write audit %s", state.audit_id, exc_info=True)
