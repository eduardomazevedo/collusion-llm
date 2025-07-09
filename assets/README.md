# Assets Directory

This directory contains configuration files and static assets used throughout the project.

## Files

### prompts.json
Contains all LLM prompt definitions:
- System messages and user prompts
- Response format specifications
- Model assignments per prompt
- Version tracking for prompt iterations

Example structure:
```json
{
  "SimpleCapacityV8.1.1": {
    "system_message": "You are an expert...",
    "user_message_template": "Analyze the following...",
    "response_format": "ScoreReasonExcerpts",
    "model": "gpt-4o-mini"
  }
}
```

### llm_config.json
OpenAI model specifications:
- Model capabilities (structured output support)
- Context window sizes
- Pricing information
- Rate limits
- Batch API limits

### Other Potential Assets
- Carrier mappings for airline analysis
- Industry classification codes
- Threshold configurations
- Prompt templates

## Usage

Assets are loaded by modules at runtime:
```python
# In modules/llm.py
with open('assets/prompts.json', 'r') as f:
    prompts = json.load(f)

# In modules/config.py  
with open('assets/llm_config.json', 'r') as f:
    llm_config = json.load(f)
```

## Maintenance

When updating prompts:
1. Create new version with incremented number (e.g., V8.1.1 → V8.1.2)
2. Test on benchmark set before production use
3. Document changes in commit message
4. Update CLAUDE.md if adding new prompt types