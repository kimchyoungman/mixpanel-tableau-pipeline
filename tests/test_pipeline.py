from pathlib import Path

from tableauhyperapi import Connection, HyperProcess, TableName, Telemetry

from src.pipeline import Pipeline


def _assert_empty_extract(path: Path):
    assert path.exists()
    assert path.stat().st_size > 0
    with HyperProcess(Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as process:
        with Connection(process.endpoint, str(path)) as connection:
            assert connection.catalog.has_table(TableName("Extract", "events"))
            assert connection.execute_scalar_query(
                'SELECT COUNT(*) FROM "Extract"."events"'
            ) == 0


def test_no_events_produces_a_valid_empty_extract(tmp_path):
    pipeline = Pipeline(api_secret="test", project_id="test")
    pipeline.mixpanel_client.export_events = lambda *args, **kwargs: iter(())
    output_path = tmp_path / "empty.hyper"

    result = pipeline.run("2026-01-01", "2026-01-01", str(output_path))

    assert result == str(output_path)
    _assert_empty_extract(output_path)


def test_filtered_out_events_produce_a_valid_empty_extract(tmp_path):
    pipeline = Pipeline(api_secret="test", project_id="test")
    pipeline.mixpanel_client.export_events = lambda *args, **kwargs: iter(
        [
            {
                "event": "Page View",
                "properties": {
                    "distinct_id": "user-1",
                    "time": 1_700_000_000,
                    "$insert_id": "insert-1",
                    "plan": "free",
                },
            }
        ]
    )
    output_path = tmp_path / "filtered.hyper"

    pipeline.run(
        "2026-01-01",
        "2026-01-01",
        str(output_path),
        filters=["plan=pro"],
    )

    _assert_empty_extract(output_path)
