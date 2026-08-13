import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

import app.core.llm as llm_mod


@pytest.fixture
def stub_llm(monkeypatch):
    """Replace the LLM with a FakeListChatModel returning canned JSON strings.

    Usage: stub_llm(['{"findings": []}', ...]) -- one response per call,
    cycled if exhausted (langchain's FakeListChatModel loops the list).
    """

    def _set(responses: list[str]):
        fake = FakeListChatModel(responses=responses)
        monkeypatch.setattr(llm_mod, "get_chat_model", lambda: fake)
        return fake

    return _set
