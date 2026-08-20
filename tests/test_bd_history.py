from src.vietnam_bd.history import (
    export_analyses,
    get_analysis,
    import_analyses,
    list_analyses,
    save_analysis,
)


def test_analysis_history_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("BD_HISTORY_DB_PATH", str(tmp_path / "history.sqlite3"))
    history_id = save_analysis(
        seed="Vietnam factory expansion", result_version="v2",
        result={"opportunity_title": "Factory Expansion", "executive_summary": "Summary"},
        research_trace={"rounds": 2},
    )
    summaries = list_analyses()
    assert len(summaries) == 1
    assert summaries[0].history_id == history_id
    saved = get_analysis(history_id)
    assert saved is not None
    assert saved.result["executive_summary"] == "Summary"
    assert saved.research_trace == {"rounds": 2}


def test_history_is_newest_first(tmp_path, monkeypatch):
    monkeypatch.setenv("BD_HISTORY_DB_PATH", str(tmp_path / "history.sqlite3"))
    first_id = save_analysis(seed="first", result_version="legacy", result={})
    second_id = save_analysis(seed="second", result_version="v2", result={})
    assert [item.history_id for item in list_analyses()] == [second_id, first_id]


def test_history_export_import_is_idempotent(tmp_path, monkeypatch):
    source_path = tmp_path / "source.sqlite3"
    target_path = tmp_path / "target.sqlite3"
    monkeypatch.setenv("BD_HISTORY_DB_PATH", str(source_path))
    history_id = save_analysis(
        seed="Thermo Fisher NIC",
        result_version="v3",
        result={"opportunity_title": "Shared Lab"},
        research_trace={"sources": 8},
    )
    records = export_analyses()

    monkeypatch.setenv("BD_HISTORY_DB_PATH", str(target_path))
    assert import_analyses(records) == 1
    assert import_analyses(records) == 0
    assert get_analysis(history_id).result["opportunity_title"] == "Shared Lab"
