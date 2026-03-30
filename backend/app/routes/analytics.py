# backend/app/routes/analytics.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import io
from app.database import SessionDep
from app.models.test import Test
from app.schemas.response import AnalyticsResponse
from app.services.analytics_service import compute_analytics, generate_csv

router = APIRouter(prefix="/api/v1/tests", tags=["analytics"])


@router.get("/{test_id}/analytics", response_model=AnalyticsResponse)
def get_analytics(test_id: int, session: SessionDep):
    test = session.get(Test, test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    return compute_analytics(test, session)


@router.get("/{test_id}/export")
def export_csv(test_id: int, session: SessionDep):
    test = session.get(Test, test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    csv_content = generate_csv(test, session)
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="test-{test.slug}-responses.csv"'
        },
    )
