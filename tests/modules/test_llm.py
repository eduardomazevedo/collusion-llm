import pytest
from modules.llm import LLMQuery

@pytest.fixture
def llm_query():
    """Fixture to initialize LLMQuery."""
    return LLMQuery()

def test_apply_prompt_to_transcripts(llm_query):
    """Test apply_prompt_to_transcripts with a real transcript ID."""
    
    transcript_ids = [23993]
    
    # Run the function
    responses = llm_query.apply_prompt_to_transcripts("SimpleCapacityV8", transcript_ids)
    
    # Assertions
    assert isinstance(responses, dict), "Response should be a dictionary."
    assert transcript_ids[0] in responses, "Transcript ID should be in the response."
    assert isinstance(responses[transcript_ids[0]], str), "Response should be a string."
    assert len(responses[transcript_ids[0]]) > 0, "Response should not be empty."
