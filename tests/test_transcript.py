import pytest

from app.transcript import TranscriptError, fmt_time, normalize_for_match, parse_transcript


def parse(text):
    return parse_transcript(text, min_chars=50, max_chars=150_000)


def test_plain_text_has_no_timestamps(sample_transcript):
    assert sample_transcript["has_timestamps"] is False
    assert all(s["start"] is None for s in sample_transcript["segments"])
    assert [s["id"] for s in sample_transcript["segments"]] == list(range(len(sample_transcript["segments"])))
    assert 3 <= len(sample_transcript["segments"]) < 40


def test_srt_timestamps_are_parsed_and_merged():
    srt = "".join(
        f"{i}\n00:00:{i * 4:02d},000 --> 00:00:{i * 4 + 3:02d},500\nThis is subtitle line number {i} of the demo.\n\n"
        for i in range(1, 12)
    )
    t = parse(srt)
    assert t["has_timestamps"] is True
    assert t["segments"][0]["start"] == 4.0
    assert len(t["segments"]) < 11  # tiny cues were grouped
    assert all(s["end"] >= s["start"] for s in t["segments"])


def test_vtt_with_tags():
    vtt = "WEBVTT\n\n" + "".join(
        f"00:0{i}:00.000 --> 00:0{i}:05.000\n<v Host>Hello number {i}, this is a reasonably long line of speech.</v>\n\n" for i in range(1, 6)
    )
    t = parse(vtt)
    assert t["has_timestamps"] and "<v" not in t["segments"][0]["text"]


def test_inline_timestamps_detected_when_structural():
    lines = "\n".join(f"[{m:02d}:{s:02d}] Speaker talks about topic number {m}{s} in some depth." for m, s in [(0, 5), (0, 40), (1, 15), (2, 0), (3, 30)])
    t = parse(lines)
    assert t["has_timestamps"] is True and t["segments"][0]["start"] == 5.0


def test_incidental_times_in_prose_are_not_timestamps():
    text = "We met at 3:30 pm and talked for ages about many different things in the garden.\n\n" * 6
    t = parse(text)
    assert t["has_timestamps"] is False


def test_non_monotonic_stamps_rejected():
    lines = "\n".join(f"{m}:00 line {i} with enough words to count as speech here" for i, m in enumerate([9, 2, 8, 1, 7, 3]))
    assert parse(lines)["has_timestamps"] is False


def test_too_short_and_too_long_and_binaryish():
    with pytest.raises(TranscriptError, match="too short"):
        parse("hi there")
    with pytest.raises(TranscriptError, match="too long"):
        parse_transcript("word " * 100, min_chars=10, max_chars=50)
    with pytest.raises(TranscriptError, match="doesn't look like"):
        parse("1234567890 " * 20)


def test_control_characters_removed():
    t = parse("Hello\x00 there\x07 friend, this is a transcript with control characters inside of it. " * 4)
    assert "\x00" not in t["segments"][0]["text"]


def test_one_giant_line_is_split_into_segments():
    t = parse("This is a sentence about memory. " * 200)
    assert len(t["segments"]) > 5 and max(len(s["text"]) for s in t["segments"]) <= 950


def test_no_punctuation_blob_is_hard_split():
    t = parse("word " * 1000)
    assert len(t["segments"]) > 3


def test_fmt_time():
    assert fmt_time(5) == "0:05" and fmt_time(3725) == "1:02:05" and fmt_time(None) == ""


def test_normalize_keeps_bengali_marks():
    a = normalize_for_match("আমি ভাত খাই।")
    b = normalize_for_match("আমি  ভাত খাই")
    assert a == b and "ি" in a
