import pytest

from app.llm import AllProvidersFailed, GroundingError
from app.pipeline import Doc, answer_question, chapter_range, generate_section, make_quiz_validator
from app.schemas import GenerateRequest, TranscriptIn
from tests.conftest import FakeProvider, make_client


def doc_of(tr):
    return Doc(TranscriptIn(**tr))


def find_seg(doc, needle):
    return next(s["id"] for s in doc.segments if needle in s["text"])


def req(tr, section, **kw):
    return GenerateRequest(transcript=TranscriptIn(**tr), section=section, **kw)


# ------------------------------------------------------------ quote verification
def test_quote_verification(sample_transcript):
    d = doc_of(sample_transcript)
    sid = find_seg(d, "Ebbinghaus")
    assert d.quote_supported("In 1885 a German psychologist named Hermann Ebbinghaus", sid)
    assert d.quote_supported("in 1885, a german psychologist named hermann ebbinghaus!", sid)  # case/punct tolerant
    assert d.quote_supported("Hermann Ebbinghaus tested his own memory", None)  # found anywhere
    assert not d.quote_supported("Ebbinghaus invented the telephone in 1901 in Paris", sid)
    assert not d.quote_supported("too short", sid)
    assert not d.quote_supported("", sid)


def test_quote_tolerates_one_dropped_word(sample_transcript):
    d = doc_of(sample_transcript)
    sid = find_seg(d, "spacing effect")
    # the model dropped the word 'same' -- a trivial deviation we accept
    assert d.quote_supported("the amount of study spread over several days produces much better recall weeks later", sid)


# ------------------------------------------------------------ overview
def overview_json(d):
    a, b = find_seg(d, "Ebbinghaus"), find_seg(d, "spaced repetition")
    return {
        "title": "Why we forget and how to stop",
        "one_line": "An episode about the forgetting curve and study techniques.",
        "summary": "The episode explains the forgetting curve.\n\nIt then covers spacing, retrieval practice and sleep.",
        "themes": [{"name": "Forgetting", "description": "Memory fades fast."}],
        "takeaways": [
            {"text": "Forgetting is fastest right after learning.", "evidence": [a, "S%d" % a]},
            {"text": "Review at growing intervals.", "evidence": [b]},
            {"text": "Made up claim.", "evidence": [9999]},
            {"text": "Another one.", "evidence": [a]},
        ],
    }


async def test_overview_drops_takeaways_with_bad_citations(sample_transcript):
    d = doc_of(sample_transcript)
    llm = make_client([FakeProvider("gemini", [overview_json(d)])])
    res, info = await generate_section(llm, req(sample_transcript, "overview"))
    assert len(res["takeaways"]) == 3
    assert all(t["evidence"] for t in res["takeaways"]) and res["takeaways"][0]["evidence"] == [find_seg(d, "Ebbinghaus")]
    assert any("removed" in w for w in info.warnings)


async def test_overview_missing_fields_triggers_repair_with_specific_message(sample_transcript):
    d = doc_of(sample_transcript)
    bad = {"title": "x"}
    p = FakeProvider("gemini", [bad, overview_json(d)])
    await generate_section(make_client([p]), req(sample_transcript, "overview"))
    assert "summary" in p.calls[1]["user"] and "themes" in p.calls[1]["user"]


# ------------------------------------------------------------ chapters
async def test_chapters_timestamps_come_from_segments_not_model(sample_transcript):
    n = len(sample_transcript["segments"])
    out = {"chapters": [
        {"title": "Intro", "summary": "s", "start_segment": 3, "start_time": "99:99"},  # not at 0 -> forced to 0; invented time ignored
        {"title": "Middle", "summary": "s", "start_segment": n // 2},
        {"title": "Dup", "summary": "s", "start_segment": n // 2},
        {"title": "Out of range", "summary": "s", "start_segment": n + 50},
        {"title": "End", "summary": "s", "start_segment": "S%d" % (n - 1)},
    ]}
    res, _ = await generate_section(make_client([FakeProvider("gemini", [out])]), req(sample_transcript, "chapters"))
    ch = res["chapters"]
    assert [c["start_segment"] for c in ch] == [0, n // 2, n - 1]
    assert ch[0]["end_segment"] == n // 2 - 1 and ch[-1]["end_segment"] == n - 1
    assert res["has_timestamps"] is False and all(c["start_time"] is None for c in ch)


async def test_chapters_have_real_times_for_timestamped_input():
    segs = [{"id": i, "start": i * 30.0, "end": i * 30.0 + 29, "text": f"Segment number {i} contains some spoken words for the test."} for i in range(12)]
    tr = {"segments": segs, "has_timestamps": True, "source": "audio"}
    out = {"chapters": [{"title": "A", "start_segment": 0}, {"title": "B", "start_segment": 4}, {"title": "C", "start_segment": 8}]}
    res, _ = await generate_section(make_client([FakeProvider("gemini", [out])]), req(tr, "chapters"))
    assert res["has_timestamps"] and res["chapters"][1]["start_time"] == 120.0 and res["chapters"][1]["end_time"] == 239.0


async def test_chapters_too_few_triggers_retry(sample_transcript):
    n = len(sample_transcript["segments"])
    lo, _ = chapter_range(doc_of(sample_transcript))
    one = {"chapters": [{"title": "Everything", "start_segment": 0}]}
    good = {"chapters": [{"title": f"C{i}", "start_segment": i * (n // 3)} for i in range(3)]}
    p = FakeProvider("gemini", [one, good])
    res, info = await generate_section(make_client([p]), req(sample_transcript, "chapters"))
    assert lo >= 2 and len(res["chapters"]) == 3 and info.attempts == 2 and "at least" in p.calls[1]["user"]


# ------------------------------------------------------------ quiz
def quiz_q(d, needle, quote, correct=0, **kw):
    q = {
        "question": f"Question about {needle}?", "options": ["A) right answer", "B) wrong one", "C) wrong two", "D) wrong three"],
        "correct_index": correct, "explanation": "Because.", "evidence_segment": find_seg(d, needle),
        "evidence_quote": quote, "difficulty": "medium",
    }
    q.update(kw)
    return q


def good_quiz(d):
    return {"questions": [
        quiz_q(d, "Ebbinghaus", "Hermann Ebbinghaus tested his own memory by learning lists of nonsense syllables"),
        quiz_q(d, "spacing effect", "This is called the spacing effect"),
        quiz_q(d, "desirable difficulties", "Researchers call these desirable difficulties"),
        quiz_q(d, "Interleaving", "you mix different types in the same session"),
    ]}


async def test_quiz_keeps_verified_questions_and_drops_invented_ones(sample_transcript):
    d = doc_of(sample_transcript)
    q = good_quiz(d)
    q["questions"].append(quiz_q(d, "Ebbinghaus", "Ebbinghaus won a Nobel prize for his work on memory in 1901"))
    res, info = await generate_section(make_client([FakeProvider("gemini", [q])]), req(sample_transcript, "quiz"))
    assert len(res["questions"]) == 4 and all(x["verified"] for x in res["questions"])
    assert any("discarded" in w for w in info.warnings)


async def test_quiz_strips_letter_prefixes_and_shuffles_but_keeps_correct_answer(sample_transcript):
    d = doc_of(sample_transcript)
    res, _ = await generate_section(make_client([FakeProvider("gemini", [good_quiz(d)])]), req(sample_transcript, "quiz"))
    for q in res["questions"]:
        assert q["options"][q["correct_index"]] == "right answer"
        assert not any(o.startswith(("A)", "B)")) for o in q["options"])
    positions = {q["correct_index"] for q in res["questions"]}
    assert len(positions) > 1  # not always the same slot


async def test_quiz_all_invented_fails_after_repair_then_falls_back(sample_transcript):
    d = doc_of(sample_transcript)
    bad = {"questions": [quiz_q(d, "Ebbinghaus", "completely invented sentence that is nowhere in the text") for _ in range(4)]}
    a = FakeProvider("gemini", [bad, bad])
    b = FakeProvider("groq", [good_quiz(d)])
    res, info = await generate_section(make_client([a, b]), req(sample_transcript, "quiz"))
    assert info.provider == "groq" and info.fallback_used and "evidence_quote" in a.calls[1]["user"]


async def test_quiz_all_providers_ungrounded_raises(sample_transcript):
    d = doc_of(sample_transcript)
    bad = {"questions": [quiz_q(d, "Ebbinghaus", "completely invented sentence that is nowhere in the text")]}
    with pytest.raises(AllProvidersFailed):
        await generate_section(make_client([FakeProvider("gemini", [bad, bad])]), req(sample_transcript, "quiz"))


def test_quiz_rejects_bad_options_and_index(sample_transcript):
    d = doc_of(sample_transcript)
    v = make_quiz_validator(d, 3)
    qs = good_quiz(d)["questions"]
    qs[0]["correct_index"] = 9
    qs[1]["options"] = ["same", "same", "x", "y"]
    with pytest.raises(GroundingError, match="Only 2"):
        v({"questions": qs})


# ------------------------------------------------------------ revision
async def test_revision_prompt_contains_instruction_and_previous_and_is_validated(sample_transcript):
    d = doc_of(sample_transcript)
    first = overview_json(d)
    p = FakeProvider("gemini", [first])
    res, info = await generate_section(make_client([p]), req(sample_transcript, "overview", instruction="Make it much shorter", previous=first))
    user = p.calls[0]["user"]
    assert "Make it much shorter" in user and "REVISION MODE" in user and "<previous>" in user
    assert info.attempts == 1 and res["title"]


async def test_revision_requires_previous(sample_transcript):
    with pytest.raises(GroundingError):
        await generate_section(make_client([FakeProvider("gemini", [])]), req(sample_transcript, "overview", instruction="shorter"))


# ------------------------------------------------------------ ask
async def test_ask_with_verified_evidence(sample_transcript):
    d = doc_of(sample_transcript)
    sid = find_seg(d, "Ebbinghaus")
    out = {"answerable": True, "answer": "In 1885.", "evidence": [{"segment": sid, "quote": "In 1885 a German psychologist named Hermann Ebbinghaus"}]}
    res, _ = await answer_question(make_client([FakeProvider("gemini", [out])]), TranscriptIn(**sample_transcript), "When?")
    assert res["answerable"] and res["evidence"][0]["segment"] == sid


async def test_ask_unsupported_answer_is_downgraded(sample_transcript):
    out = {"answerable": True, "answer": "Paris is the capital of France.", "evidence": [{"segment": 0, "quote": "Paris is the capital of France and always was"}]}
    res, _ = await answer_question(make_client([FakeProvider("gemini", [out])]), TranscriptIn(**sample_transcript), "Capital of France?")
    assert res["answerable"] is False and res.get("downgraded")


async def test_ask_unanswerable_passes_through(sample_transcript):
    out = {"answerable": False, "answer": "The episode does not cover this.", "evidence": []}
    res, _ = await answer_question(make_client([FakeProvider("gemini", [out])]), TranscriptIn(**sample_transcript), "Who won?")
    assert res["answerable"] is False and not res.get("downgraded")


def test_doc_reindexes_and_skips_empty_segments():
    tr = TranscriptIn(segments=[{"id": 7, "text": "  "}, {"id": 9, "text": "hello world again"}, {"id": 2, "text": "second one here"}])
    d = Doc(tr)
    assert [s["id"] for s in d.segments] == [0, 1] and d.n == 2


async def test_chapter_revision_may_use_fewer_chapters_than_the_default_minimum(sample_transcript):
    n = len(sample_transcript["segments"])
    two = {"chapters": [{"title": "A", "start_segment": 0}, {"title": "B", "start_segment": n // 2}]}
    prev = {"chapters": [{"title": "x", "start_segment": 0}]}
    res, _ = await generate_section(make_client([FakeProvider("gemini", [two])]),
                                    req(sample_transcript, "chapters", instruction="fewer, broader chapters", previous=prev))
    assert len(res["chapters"]) == 2
