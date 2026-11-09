from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.engine import create_engine, create_session_maker, init_models  # noqa: E402
from database.seed import seed_demo_data  # noqa: E402
from services.user_service import get_or_create_user  # noqa: E402


@pytest.fixture
async def session_maker(tmp_path):
    engine = create_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    await init_models(engine)
    maker = create_session_maker(engine)
    async with maker() as session:
        await seed_demo_data(session)
    yield maker
    await engine.dispose()


@pytest.fixture
async def session(session_maker):
    async with session_maker() as session:
        yield session


@pytest.fixture
async def user(session):
    user, _ = await get_or_create_user(session, 1001, "client", "Test Client")
    return user


@pytest.fixture
async def other_user(session):
    user, _ = await get_or_create_user(session, 2002, "other", "Other Client")
    return user
