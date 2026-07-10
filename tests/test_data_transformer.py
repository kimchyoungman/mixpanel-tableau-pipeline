from datetime import datetime

from src.data_transformer import DataTransformer


def test_flatten_event_and_filter_properties():
    transformer = DataTransformer()
    event = {
        "event": "Page View",
        "properties": {
            "distinct_id": "user-1",
            "time": 1_700_000_000,
            "$insert_id": "insert-1",
            "$browser": "Firefox",
            "plan-name": "pro",
        },
    }

    flattened = transformer.flatten_event(event)

    assert flattened["event_name"] == "Page View"
    assert flattened["distinct_id"] == "user-1"
    assert flattened["insert_id"] == "insert-1"
    assert flattened["mp_browser"] == "Firefox"
    assert flattened["plan_name"] == "pro"
    assert isinstance(flattened["event_time"], datetime)
    assert transformer.filter_events([flattened], ["plan-name=pro"]) == [flattened]
    assert transformer.filter_events([flattened], ["plan-name=free"]) == []


def test_invalid_filters_do_not_remove_events():
    transformer = DataTransformer()
    events = [{"event_name": "Page View"}]

    assert transformer.filter_events(events, ["missing-equals-sign"]) == events
