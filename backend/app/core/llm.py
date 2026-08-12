from functools import lru_cache
from typing import Type, TypeVar

from langchain_core.exceptions import OutputParserException
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.models.schemas import AuditFinding, FindingsResult

T = TypeVar("T", bound=BaseModel)

MAX_FIX_ATTEMPTS = 2


@lru_cache(maxsize=1)
def get_chat_model() -> BaseChatModel:
    """Provider is `settings.LLM_PROVIDER` if set, else the first of
    openai/anthropic/gemini with an API key present, else local Ollama
    (Phase 2, Railway private network). All branches return a plain
    BaseChatModel, so agent code never depends on which one is active.
    """
    provider = settings.LLM_PROVIDER or _infer_provider()

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=settings.OPENAI_MODEL, api_key=settings.OPENAI_API_KEY, temperature=0)

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        # Claude Sonnet 5 / Opus 5 reject non-default temperature/top_p/top_k
        # with a 400 -- omit sampling params rather than pinning temperature=0.
        return ChatAnthropic(model=settings.ANTHROPIC_MODEL, api_key=settings.ANTHROPIC_API_KEY)

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(model=settings.GEMINI_MODEL, google_api_key=settings.GOOGLE_API_KEY, temperature=0)

    from langchain_ollama import ChatOllama

    return ChatOllama(model=settings.OLLAMA_MODEL, base_url=settings.OLLAMA_BASE_URL, temperature=0)


def _infer_provider() -> str:
    if settings.OPENAI_API_KEY:
        return "openai"
    if settings.ANTHROPIC_API_KEY:
        return "anthropic"
    if settings.GOOGLE_API_KEY:
        return "gemini"
    return "ollama"


def invoke_structured(
    pydantic_model: Type[T],
    system_prompt: str,
    user_input: str,
    llm: BaseChatModel | None = None,
) -> T:
    """System prompt + input -> LLM -> PydanticOutputParser, with a manual
    retry-on-parse-error loop: on invalid JSON/schema mismatch, the raw
    output and the parser's own error are fed back to the model and it is
    asked to correct it. A quantized 8B model will not reliably emit valid
    structured JSON on the first try, so this retry is not optional.

    (langchain's legacy OutputFixingParser did the same thing, but lives in
    the now-deprecated langchain-classic package as of langchain 1.x --
    this reimplements just the retry loop against langchain-core directly.)
    """
    model = llm or get_chat_model()
    parser = PydanticOutputParser(pydantic_object=pydantic_model)

    messages = [
        SystemMessage(content=f"{system_prompt}\n\n{parser.get_format_instructions()}"),
        HumanMessage(content=user_input),
    ]

    last_error: Exception | None = None
    for attempt in range(MAX_FIX_ATTEMPTS + 1):
        response = model.invoke(messages)
        raw_text = response.content if isinstance(response.content, str) else str(response.content)
        try:
            return parser.parse(raw_text)
        except (OutputParserException, ValidationError) as exc:
            last_error = exc
            if attempt == MAX_FIX_ATTEMPTS:
                break
            messages.append(response)
            messages.append(
                HumanMessage(
                    content=(
                        "That output did not match the required schema. "
                        f"Parser error: {exc}\n\n"
                        "Re-emit ONLY the corrected JSON, matching the schema exactly."
                    )
                )
            )

    raise ValueError(f"Failed to obtain valid structured output after {MAX_FIX_ATTEMPTS + 1} attempts: {last_error}")


def run_structured_findings(system_prompt: str, evidence: str) -> tuple[list[AuditFinding], str | None]:
    """Invoke an LLM findings pass. Never raises -- a model/network/parse
    failure must not take down the whole parallel evaluation fan-out, so
    failures are reported as an error string and an empty findings list.
    """
    try:
        result = invoke_structured(FindingsResult, system_prompt, evidence)
        return result.findings, None
    except Exception as exc:  # noqa: BLE001 -- intentionally broad, see docstring
        return [], f"LLM structured-output call failed: {exc}"
