from fastapi import APIRouter, Cookie, HTTPException, Request

from app.schemas.qa import QAResponse, Question
from app.services import account_service as accounts
from app.services.qa_service import answer_question

router = APIRouter(prefix="/api/v1", tags=["question answering"])


@router.post(
    "/ask",
    summary="Ask an evidence-grounded educational question",
    description="This service does not diagnose, prescribe, or provide treatment. Unsupported questions safely abstain.",
    response_model=QAResponse,
)
def ask(
    payload: Question,
    request: Request,
    medguide_session: str | None = Cookie(default=None),
):
    user = accounts.get_user_for_session(medguide_session)
    if user and user["history_enabled"]:
        try:
            accounts.ensure_encryption_available()
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from None
    try:
        result = answer_question(payload.question, payload.retrieval_mode)
    except Exception:
        raise HTTPException(
            status_code=503, detail="The retrieval or generation service is unavailable."
        ) from None
    request.state.retrieval_count = result["observability"].get("retrieval_count", 0)
    if user and user["history_enabled"]:
        accounts.save_conversation(user["id"], payload.question, result)
    return result
