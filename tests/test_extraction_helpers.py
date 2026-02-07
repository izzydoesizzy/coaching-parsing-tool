from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


def load_module(path: str, module_name: str):
    spec = spec_from_file_location(module_name, path)
    module = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


extract_mod = load_module("scripts/03_extract_llm.py", "extract_mod")
filter_mod = load_module("scripts/02_filter_jobsearch.py", "filter_mod")


def test_compile_keywords_uses_defaults_when_missing():
    keywords = filter_mod.compile_keywords(None)
    assert "resume" in keywords


def test_keyword_hits_finds_expected_terms():
    text = "We should update your resume and improve your LinkedIn profile."
    hits = filter_mod.keyword_hits(text, ["resume", "linkedin", "portfolio"])

    assert hits == ["resume", "linkedin"]


def test_classify_ask_type_resume_detection():
    ask_type = extract_mod.classify_ask_type("How can I improve my resume for ATS?")
    assert ask_type == "resume"


def test_heuristic_extract_builds_questions_concerns_and_advice():
    text = (
        "I am worried my application process is not working. "
        "What should I do next? "
        "You should focus on networking every week."
    )
    source_ref = {"chunk_id": "c1"}

    extracted = extract_mod.heuristic_extract(text, source_ref)

    assert len(extracted["questions"]) == 1
    assert len(extracted["concerns"]) >= 1
    assert len(extracted["advice"]) >= 1
