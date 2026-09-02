from pathlib import Path

import yaml


def test_compose_structure_and_local_binding() -> None:
    compose_path = Path("infra/docker-compose.yml")
    assert compose_path.exists(), "infra/docker-compose.yml must exist"
    data = yaml.safe_load(compose_path.read_text(encoding="utf-8"))

    services = data.get("services", {})
    assert "kafka" in services
    assert "redis" in services
    assert "postgres" in services

    for name, srv in services.items():
        assert "healthcheck" in srv, f"Service {name} missing healthcheck"
        ports = srv.get("ports", [])
        for p in ports:
            assert str(p).startswith("127.0.0.1:"), (
                f"Port mapping '{p}' in {name} must bind to 127.0.0.1"
            )

    kafka_srv = services["kafka"]
    assert kafka_srv["image"] == "bitnami/kafka:4.0"
    kafka_env = kafka_srv["environment"]
    assert "INTERNAL://kafka:9092" in kafka_env["KAFKA_CFG_ADVERTISED_LISTENERS"]
    assert "EXTERNAL://127.0.0.1:9092" in kafka_env["KAFKA_CFG_ADVERTISED_LISTENERS"]
    assert (
        kafka_env["KAFKA_CFG_LISTENER_SECURITY_PROTOCOL_MAP"]
        == "INTERNAL:PLAINTEXT,EXTERNAL:PLAINTEXT,CONTROLLER:PLAINTEXT"
    )

    redis_srv = services["redis"]
    assert redis_srv["image"] == "redis:8.0-alpine"

    postgres_srv = services["postgres"]
    assert postgres_srv["image"] == "postgres:17-alpine"
    postgres_env = postgres_srv["environment"]
    assert "${POSTGRES_PASSWORD:?" in str(postgres_env.get("POSTGRES_PASSWORD", ""))


def test_env_example_exists() -> None:
    env_example_path = Path("infra/.env.example")
    assert env_example_path.exists(), "infra/.env.example must exist"
    content = env_example_path.read_text(encoding="utf-8")
    assert "POSTGRES_PASSWORD" in content
