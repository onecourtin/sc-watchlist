"""Run: python -m pytest -q   (or python test_check_listings.py)"""
import datetime as dt
import json
import pathlib
import tempfile

from check_listings import case_in, check, clean_court, clean_judge, norm_case


def test_norm_case_variants():
    assert norm_case("W.P.(C) No. 276/2025") == norm_case("WP(C) NO.276/2025")
    assert norm_case("Diary No. 63858-2026") == norm_case("Diary No. 63858/2026")
    assert norm_case("SLP(Crl) No. 11761/2026") == "SLPCRL11761/2026"


def test_case_in_exact_not_prefix():
    assert case_in("W.P.(C) No. 276/2025", "W.P.(C) No. 276/2025")
    assert not case_in("W.P.(C) No. 276/2025", "W.P.(C) No. 1276/2025")
    assert not case_in("W.P.(C) No. 276/2025", "W.P.(Crl.) No. 276/2025")


def test_case_in_compound_and_range():
    assert case_in("W.P.(C) No. 704/2025", "MA 1357/2026 in W.P.(C) No. 704/2025")
    assert case_in("C.A. No. 8403/2024", "C.A. No. 8402-8403/2024")
    assert not case_in("C.A. No. 8404/2024", "C.A. No. 8402-8403/2024")
    assert case_in("Diary No. 64174/2026", "Diary No. 64174-2026")


def test_clean_names():
    assert clean_judge("HON'BLE THE CHIEF JUSTICE") == "Chief Justice"
    assert clean_judge("HON'BLE MRS. JUSTICE V. MOHANA") == "V. Mohana J"
    assert clean_court("CHIEF JUSTICE'S COURT") == "Chief Justice's Court"
    assert clean_court("COURT NO. : 12") == "Court No. 12"


CL = {
    "date": "2026-10-16",
    "lists": [{"name": "M_J_1", "url": "https://api.sci.gov.in/jonew/cl/2026-10-16/M_J_1.pdf"}],
    "benches": [{
        "list": "M_J_1", "court": "COURT NO. : 3",
        "judges": ["HON'BLE MR. JUSTICE J.B. PARDIWALA", "HON'BLE MR. JUSTICE K. VINOD CHANDRAN"],
        "time": "10:30 AM",
        "sections": [{"t": "X", "items": [
            {"n": "14", "c": "SLP(Crl) No. 11761/2026", "p": "ASHA RAM @ ASHUMAL", "r": "STATE OF RAJASTHAN"},
            {"n": "15", "c": "W.P.(C) No. 9/2026", "p": "JAYA THAKUR", "r": "UNION OF INDIA"},
        ]}],
    }],
}


def run(matters, today="2026-10-15"):
    with tempfile.TemporaryDirectory() as d:
        (pathlib.Path(d) / "2026-10-16.json").write_text(json.dumps(CL))
        return check(matters, dt.date.fromisoformat(today), 7, d)


def test_check_marks_listed_and_is_idempotent():
    m = [{"id": "a", "case_nos": ["SLP(Crl) No. 11761/2026"], "date_status": "tentative", "next_date": None},
         {"id": "b", "case_nos": ["W.P.(C) No. 1/2020"], "date_status": "not-fixed", "next_date": None},
         {"id": "c", "case_nos": [], "match_parties": ["JAYA THAKUR"], "date_status": "not-fixed"}]
    ch = run(m)
    assert [c["id"] for c in ch] == ["a", "c"]
    assert m[0]["next_date"] == "2026-10-16" and m[0]["date_status"] == "listed"
    assert m[0]["court"] == "Court No. 3"
    assert m[0]["bench"] == ["J.B. Pardiwala J", "K. Vinod Chandran J"]
    assert m[0]["listing"]["item"] == "14" and m[0]["listing"]["matched_by"] == "case"
    assert m[2]["listing"]["matched_by"] == "party"
    assert m[1]["next_date"] is None
    assert run(m) == []  # second run: nothing new


def test_decided_matters_ignored():
    m = [{"id": "a", "case_nos": ["SLP(Crl) No. 11761/2026"], "date_status": "decided"}]
    assert run(m) == []


if __name__ == "__main__":
    import sys
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
