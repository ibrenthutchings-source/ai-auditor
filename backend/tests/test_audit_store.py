from app.core.audit_store import persist_audit_record
from app.models.schemas import AuditState


def test_persist_audit_record_never_raises_on_unreachable_db(monkeypatch):
    def _boom():
        raise ConnectionError("db unreachable")

    monkeypatch.setattr("app.core.audit_store.get_session", _boom)

    state = AuditState(
        audit_id="a1",
        target_system_logs=[],
        regulatory_context="default",
        current_status="COMPLETE",
    )
    # Must not raise.
    persist_audit_record(state)
