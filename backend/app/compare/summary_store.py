from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compare_summary import CompareSummary


async def get_summary(
    db: AsyncSession,
    user_id: uuid.UUID,
    config_signature: str,
) -> Optional[str]:
    stmt = select(CompareSummary).where(
        CompareSummary.user_id == user_id,
        CompareSummary.config_signature == config_signature,
    )
    record = (await db.execute(stmt)).scalars().first()
    return record.summary if record else None


async def upsert_summary(
    db: AsyncSession,
    user_id: uuid.UUID,
    config_signature: str,
    summary: str,
) -> CompareSummary:
    stmt = select(CompareSummary).where(
        CompareSummary.user_id == user_id,
        CompareSummary.config_signature == config_signature,
    )
    record = (await db.execute(stmt)).scalars().first()

    if record is None:
        record = CompareSummary(
            user_id=user_id,
            config_signature=config_signature,
            summary=summary,
        )
        db.add(record)
    else:
        record.summary = summary
        db.add(record)

    await db.flush()
    return record