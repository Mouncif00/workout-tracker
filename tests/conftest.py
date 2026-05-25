import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    import app.models
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def clean_tables():
    yield
    db = TestingSessionLocal()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()
    finally:
        db.close()


@pytest.fixture(autouse=True)
def mock_mongo():
    """Mock all MongoDB collections so tests don't need a real MongoDB."""
    mock_col = MagicMock()
    mock_col.insert_one = AsyncMock(return_value=MagicMock(inserted_id="mock_id"))
    mock_col.find = MagicMock(return_value=MagicMock(
        sort=MagicMock(return_value=MagicMock(
            to_list=AsyncMock(return_value=[])
        ))
    ))
    mock_col.find_one = AsyncMock(return_value=None)
    mock_col.delete_one = AsyncMock()

    with patch("app.core.mongodb.comments_collection", return_value=mock_col), \
         patch("app.core.mongodb.logs_collection", return_value=mock_col), \
         patch("app.core.mongodb.analytics_collection", return_value=mock_col), \
         patch("app.routers.auth.logs_collection", return_value=mock_col), \
         patch("app.routers.comments.comments_collection", return_value=mock_col), \
         patch("app.routers.reports.analytics_collection", return_value=mock_col):
        yield mock_col


@pytest.fixture
def db():
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def registered_user(client):
    resp = client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "username": "testuser",
        "password": "strongpassword123",
        "full_name": "Test User",
    })
    assert resp.status_code == 201, resp.json()
    return resp.json()


@pytest.fixture
def auth_headers(registered_user):
    return {"Authorization": f"Bearer {registered_user['access_token']}"}


@pytest.fixture
def sample_exercise(db):
    from app.models.exercise import Exercise
    ex = Exercise(
        name="Test Squat",
        category="strength",
        muscle_group="legs",
        equipment="barbell",
        description="A test squat exercise",
    )
    db.add(ex)
    db.commit()
    db.refresh(ex)
    return ex
