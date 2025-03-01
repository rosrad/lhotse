from pathlib import Path
from typing import Dict, List

import pytest

from lhotse.supervision import AlignmentItem, SupervisionSegment, SupervisionSet
from lhotse.testing.dummies import DummyManifest, remove_spaces_from_segment_text
from lhotse.utils import fastcopy


@pytest.fixture
def external_supervision_set() -> SupervisionSet:
    return SupervisionSet.from_json(
        "test/fixtures/supervision.json"
    ).with_alignment_from_ctm("test/fixtures/supervision.ctm")


@pytest.fixture
def external_alignment() -> Dict[str, List[AlignmentItem]]:
    return {
        "word": [
            AlignmentItem("transcript", 0.1, 0.08),
            AlignmentItem("of", 0.18, 0.02),
            AlignmentItem("the", 0.2, 0.03),
            AlignmentItem("first", 0.23, 0.07),
            AlignmentItem("segment", 0.3, 0.1),
        ]
    }


def test_supervision_map(external_supervision_set):
    for s in external_supervision_set.map(remove_spaces_from_segment_text):
        if s.text is not None:
            assert " " not in s.text


def test_supervision_transform_text(external_supervision_set):
    for s in external_supervision_set.transform_text(lambda text: "dummy"):
        if s.text is not None:
            assert s.text == "dummy"


def test_supervision_transform_alignment(external_supervision_set, type="word"):
    for s in external_supervision_set.transform_alignment(lambda symbol: "dummy"):
        if s.alignment is not None:
            assert all([a.symbol == "dummy" for a in s.alignment[type]])


def test_supervision_segment_with_full_metadata(
    external_supervision_set, external_alignment
):
    segment = external_supervision_set["segment-1"]
    assert "segment-1" == segment.id
    assert "recording-1" == segment.recording_id
    assert 0 == segment.channel
    assert 0.1 == segment.start
    assert 0.3 == segment.duration
    assert 0.4 == segment.end
    assert "transcript of the first segment" == segment.text
    assert "english" == segment.language
    assert "Norman Dyhrentfurth" == segment.speaker
    assert external_alignment == segment.alignment


def test_supervision_segment_with_no_metadata(external_supervision_set):
    segment = external_supervision_set["segment-2"]
    assert "segment-2" == segment.id
    assert "recording-1" == segment.recording_id
    assert 0 == segment.channel  # implicitly filled default value
    assert 0.5 == segment.start
    assert 0.4 == segment.duration
    assert 0.9 == segment.end
    assert segment.text is None
    assert segment.language is None
    assert segment.speaker is None


def test_create_supervision_segment_with_minimum_metadata():
    SupervisionSegment(id="X", recording_id="X", start=0.0, duration=0.1)


def test_supervision_custom_attributes():
    sup = SupervisionSegment(id="X", recording_id="X", start=0.0, duration=0.1)
    sup.eye_color = "green"
    sup.wer = 0.41

    assert sup.eye_color == "green"
    assert sup.custom["eye_color"] == "green"

    assert sup.wer == 0.41
    assert sup.custom["wer"] == 0.41

    with pytest.raises(AttributeError):
        sup.nonexistent_attr


def test_supervision_custom_attributes_serialization():
    sup = SupervisionSegment(id="X", recording_id="X", start=0.0, duration=0.1)
    sup.eye_color = "green"
    sup.wer = 0.41

    sup2 = SupervisionSegment.from_dict(sup.to_dict())

    assert sup2.eye_color == "green"
    assert sup2.custom["eye_color"] == "green"

    assert sup2.wer == 0.41
    assert sup2.custom["wer"] == 0.41

    with pytest.raises(AttributeError):
        sup.nonexistent_attr


def test_create_supervision_segment_with_all_metadata():
    SupervisionSegment(
        id="X",
        recording_id="X",
        start=0.0,
        duration=0.1,
        channel=0,
        text="wysokie szczyty",
        language="polish",
        speaker="Janusz",
        gender="male",
        alignment={
            "word": [
                AlignmentItem(symbol="wysokie", start=0.0, duration=0.05),
                AlignmentItem(symbol="szczyty", start=0.05, duration=0.05),
            ]
        },
    )


def test_supervision_set_with_alignment_from_ctm(
    external_supervision_set, external_alignment
):
    segment = external_supervision_set["segment-1"]
    assert external_alignment == segment.alignment


def test_supervision_set_write_alignment_to_ctm(external_supervision_set, tmp_path):
    tmp_ctm_file = tmp_path / "alignment.ctm"
    external_supervision_set.write_alignment_to_ctm(tmp_ctm_file)
    assert tmp_ctm_file.read_text() == Path("test/fixtures/supervision.ctm").read_text()


def test_supervision_set_iteration():
    supervision_set = SupervisionSet(
        segments={
            "X": SupervisionSegment(
                id="X", recording_id="X", channel=0, start=2.0, duration=2.5
            ),
            "Y": SupervisionSegment(
                id="Y", recording_id="X", channel=0, start=5.0, duration=5.0
            ),
        }
    )
    assert 2 == len(supervision_set)
    assert 2 == len(list(supervision_set))


def test_add_supervision_sets():
    expected = DummyManifest(SupervisionSet, begin_id=0, end_id=10)
    supervision_set_1 = DummyManifest(SupervisionSet, begin_id=0, end_id=5)
    supervision_set_2 = DummyManifest(SupervisionSet, begin_id=5, end_id=10)
    combined = supervision_set_1 + supervision_set_2
    assert combined == expected


@pytest.fixture
def search_supervision_set():
    return SupervisionSet.from_segments(
        [
            SupervisionSegment(
                id="s1", recording_id="r1", start=0, duration=5.0, channel=0
            ),
            SupervisionSegment(
                id="s2", recording_id="r1", start=4.5, duration=2.0, channel=1
            ),
            SupervisionSegment(
                id="s3", recording_id="r1", start=8.0, duration=3.0, channel=0
            ),
            SupervisionSegment(
                id="s4", recording_id="r2", start=1, duration=5.0, channel=0
            ),
        ]
    )


@pytest.mark.parametrize("adjust_offset", [False, True])
def test_supervision_set_find_recording_id(search_supervision_set, adjust_offset):
    segments = list(
        search_supervision_set.find(recording_id="r1", adjust_offset=adjust_offset)
    )
    assert len(segments) == 3
    assert segments[0].id == "s1"
    assert segments[0].start == 0
    assert segments[1].id == "s2"
    assert segments[1].start == 4.5
    assert segments[2].id == "s3"
    assert segments[2].start == 8.0


@pytest.mark.parametrize("adjust_offset", [False, True])
def test_supervision_set_find_channel(search_supervision_set, adjust_offset):
    segments = list(
        search_supervision_set.find(
            recording_id="r1", channel=0, adjust_offset=adjust_offset
        )
    )
    assert len(segments) == 2
    assert segments[0].id == "s1"
    assert segments[0].start == 0
    assert segments[1].id == "s3"
    assert segments[1].start == 8.0


@pytest.mark.parametrize(
    ["adjust_offset", "expected_start0", "expected_start1"],
    [(False, 4.5, 8.0), (True, 4.0, 7.5)],
)
def test_supervision_set_find_start_after(
    search_supervision_set, adjust_offset, expected_start0, expected_start1
):
    segments = list(
        search_supervision_set.find(
            recording_id="r1", start_after=0.5, adjust_offset=adjust_offset
        )
    )
    assert len(segments) == 2
    assert segments[0].id == "s2"
    assert segments[0].start == expected_start0
    assert segments[1].id == "s3"
    assert segments[1].start == expected_start1


@pytest.mark.parametrize(
    ["adjust_offset", "expected_start"], [(False, 4.5), (True, 4.0)]
)
def test_supervision_set_find_start_after_end_before(
    search_supervision_set, adjust_offset, expected_start
):
    segments = list(
        search_supervision_set.find(
            recording_id="r1",
            start_after=0.5,
            end_before=10.0,
            adjust_offset=adjust_offset,
        )
    )
    assert len(segments) == 1
    assert segments[0].id == "s2"
    assert segments[0].start == expected_start


@pytest.fixture
def supervision():
    return SupervisionSegment("sup", "rec", start=-5, duration=18)


@pytest.mark.parametrize(
    ["trim_end", "expected_end"],
    [
        (10, 10),
        (18, 13),
        (20, 13),
    ],
)
def test_supervision_trim(supervision, trim_end, expected_end):
    trimmed = supervision.trim(trim_end)
    assert trimmed.start == 0
    assert trimmed.duration == expected_end


@pytest.mark.parametrize("start", [0, 5])
def test_supervision_trim_does_not_affect_nonnegative_start(supervision, start):
    supervision = fastcopy(supervision, start=start)
    trimmed = supervision.trim(50)
    assert trimmed.start == start
