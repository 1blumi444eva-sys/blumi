import os
import time
import json
from unittest import skipIf

from fastapi.testclient import TestClient


@skipIf(os.getenv("RUN_SLOW_INTEGRATION") is None, "integration test (set RUN_SLOW_INTEGRATION=1 to enable)")
def test_run_postbot_smoke():
    """Smoke test: POST /run and poll /status until done/failed (skipped by default).
    This is intended as a local integration test and is skipped in CI unless explicitly enabled.
    """
    from backend.api import create_app

    app = create_app()
    client = TestClient(app)

    # create job
    resp = client.post("/run", json={"topic": "integration test topic", "style": "post", "theme": "auto"})
    assert resp.status_code == 200
    data = resp.json()
    job_id = data.get("job_id")
    assert job_id

    # poll until done or timeout
    deadline = time.time() + 60  # 60s max in local runs
    status = None
    while time.time() < deadline:
        r = client.get(f"/status/{job_id}")
        assert r.status_code == 200
        status = r.json()
        if status.get("status") in ("done", "failed"):
            break
        time.sleep(1)

    assert status is not None
    assert status.get("status") in ("done", "failed")
