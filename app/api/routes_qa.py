from fastapi import APIRouter, Request

from app.schemas.qa import QAResponse, Question
from app.services.qa_service import answer_question

router = APIRouter(prefix="/api/v1", tags=["question answering"])


@router.post(
    "/ask",
    summary="Ask an evidence-grounded educational question",
    description="This service does not diagnose, prescribe, or provide treatment. Unsupported questions safely abstain.",
    response_model=QAResponse,
)
def ask(payload: Question, request: Request):
    result = answer_question(payload.question, payload.retrieval_mode)
    request.state.retrieval_count = result["observability"].get("retrieval_count", 0)
    return result
