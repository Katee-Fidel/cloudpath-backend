import pytest
from fastapi.testclient import TestClient
from app.main import app
@pytest.fixture()
def client(tmp_path,monkeypatch):
    monkeypatch.setenv("DATABASE_PATH",str(tmp_path/"test.db"))
    monkeypatch.setenv("JWT_SECRET","test-secret-that-is-at-least-32-characters")
    monkeypatch.setenv("AI_MODE","demo")
    with TestClient(app) as c: yield c
@pytest.fixture()
def auth(client):
    result=client.post('/auth/register',json={"email":"learner@example.com","password":"strong-password-123"})
    assert result.status_code==201
    return {"Authorization":"Bearer "+result.json()["access_token"]}

@pytest.fixture(autouse=True)
def isolated_proxy_environment(monkeypatch):
    # Unit tests mock HTTP calls and must not inherit host-specific proxy transports.
    for name in ['HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy']:
        monkeypatch.delenv(name,raising=False)
