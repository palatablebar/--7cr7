"""HTTP-level checks for the retirement API: auth/RBAC, reclaim manifest,
freeze -> execute -> restore round trip through the real FastAPI stack."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config.database import Base, get_db
import app.models  # noqa: F401
from app.main import app
from app.models import DataFile, LakeTable, User
from app.services import snapshot_service
from app.utils.jwt import create_access_token
from app.utils.lake import checksum_of


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


@pytest.fixture()
def client(session):
    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def _user(session, email, role):
    row = User(email=email, password_hash="x", display_name=email.split("@")[0], role=role)
    session.add(row)
    session.commit()
    return row


def _auth(user):
    return {"Authorization": f"Bearer {create_access_token(user)}"}


@pytest.fixture()
def scene(session):
    engineer = _user(session, "eng@lake.local", "engineer")
    analyst = _user(session, "analyst@lake.local", "analyst")
    table = LakeTable(
        db_name="ods", table_name="events", partition_key="dt", file_format="parquet",
        target_file_size_mb=256, small_file_threshold_mb=64, status="active",
    )
    session.add(table)
    session.commit()
    for index in range(2):
        size = 20 * 1024 * 1024
        path = f"s3://shiguang-lake/warehouse/ods/events/dt=20261101/part-{index:05d}.parquet"
        session.add(DataFile(
            table_id=table.id, partition_value="20261101", path=path,
            size_bytes=size, row_count=1000, checksum=checksum_of(path, 1000, size),
        ))
    session.commit()
    snapshot_service.create_snapshot(session, table, created_by=engineer.id, note="v1")
    size = 12 * 1024 * 1024
    late_path = "s3://shiguang-lake/warehouse/ods/events/dt=20261101/backfill-00000.parquet"
    session.add(DataFile(
        table_id=table.id, partition_value="20261101", path=late_path,
        size_bytes=size, row_count=600, checksum=checksum_of(late_path, 600, size),
        write_source="backfill",
    ))
    session.commit()
    return {"engineer": engineer, "analyst": analyst, "table": table, "late_path": late_path}


def test_retirement_roundtrip_over_http(client, scene):
    engineer_headers = _auth(scene["engineer"])
    analyst_headers = _auth(scene["analyst"])
    table_id = scene["table"].id

    # 回收清单：保护引用 + 可回收 == 分区文件总数
    resp = client.get(f"/api/tables/{table_id}/reclaim-manifest", headers=analyst_headers)
    assert resp.status_code == 200
    preview = resp.json()
    item = preview["items"][0]
    assert item["file_count"] == 3
    assert item["protected_count"] == 2
    assert item["reclaimable_count"] == 1
    assert item["invariant_ok"] is True

    # 只读角色不能创建退役单
    resp = client.post(
        f"/api/tables/{table_id}/retirements",
        json={"partition_values": ["20261101"]},
        headers=analyst_headers,
    )
    assert resp.status_code == 403

    # 创建退役单：分区冻结
    resp = client.post(
        f"/api/tables/{table_id}/retirements",
        json={"partition_values": ["20261101"], "note": "退役旧分区降本"},
        headers=engineer_headers,
    )
    assert resp.status_code == 200
    retirement = resp.json()["retirement"]
    assert retirement["status"] == "retiring"

    # 冻结分区停止新合并
    resp = client.post(
        "/api/plans",
        json={"table_id": table_id, "partition_values": ["20261101"]},
        headers=engineer_headers,
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "LAKE-2017"

    # 演练注入失败：整批回滚，文件一个不少
    resp = client.post(
        f"/api/retirements/{retirement['id']}/execute",
        json={"simulate_failure": True},
        headers=engineer_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is False
    assert resp.json()["retirement"]["status"] == "failed"
    files = client.get(f"/api/tables/{table_id}/files", headers=engineer_headers).json()
    assert files["total"] == 3

    # 恢复原分区后可以再次执行
    resp = client.post(f"/api/retirements/{retirement['id']}/restore", headers=engineer_headers)
    assert resp.json()["retirement"]["status"] == "restored"

    resp = client.post(
        f"/api/tables/{table_id}/retirements",
        json={"partition_values": ["20261101"]},
        headers=engineer_headers,
    )
    second = resp.json()["retirement"]
    resp = client.post(f"/api/retirements/{second['id']}/execute", json={}, headers=engineer_headers)
    assert resp.json()["ok"] is True
    assert resp.json()["retirement"]["status"] == "retired"
    assert resp.json()["retirement"]["result"]["reclaimed_file_count"] == 1

    # 重复执行不重复清理
    resp = client.post(f"/api/retirements/{second['id']}/execute", json={}, headers=engineer_headers)
    assert resp.json()["idempotent"] is True
    files = client.get(f"/api/tables/{table_id}/files", headers=engineer_headers).json()
    assert files["total"] == 2  # 只剩两个受保护文件
