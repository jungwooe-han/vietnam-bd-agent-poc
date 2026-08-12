from src.vietnam_bd.history import get_analysis, list_analyses, save_analysis


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
