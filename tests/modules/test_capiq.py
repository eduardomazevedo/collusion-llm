import pytest
from modules import capiq

# Sample valid transcript IDs
VALID_TRANSCRIPT_IDS = [65075, 103696, 164216, 129907]

def test_get_single_transcript():
    """Test fetching a single transcript using the real WRDS connection."""
    transcript_id = VALID_TRANSCRIPT_IDS[0]
    result = capiq.get_single_transcript(transcript_id)
    
    assert isinstance(result, str), "Expected a JSON string"
    assert len(result) > 0, "Transcript should not be empty"

def test_get_transcripts():
    """Test fetching multiple transcripts using the real WRDS connection."""
    result = capiq.get_transcripts(VALID_TRANSCRIPT_IDS)
    
    assert isinstance(result, dict), "Expected a dictionary"
    assert len(result) > 0, "Expected at least one transcript"
    
    for tid in VALID_TRANSCRIPT_IDS:
        assert tid in result, f"Transcript ID {tid} missing from result"
        assert isinstance(result[tid], str), "Expected JSON string for transcript"

def test_ciqtranscriptcomponenttype():
    """Test fetching the ciqtranscriptcomponenttype table."""
    df = capiq.ciqtranscriptcomponenttype()
    
    assert not df.empty, "Expected non-empty dataframe"
    assert "transcriptcomponenttypeid" in df.columns, "Missing expected column"

def test_disconnect():
    """Test WRDS disconnect function."""
    capiq.disconnect()
    assert capiq._conn is None, "WRDS connection should be closed"
