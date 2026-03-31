from fastapi import APIRouter
from flowa.database.db import init_db
from flowa.database.repository import get_stats

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("")
def stats():
    """Dashboard statistics."""
    init_db()
    return get_stats()
