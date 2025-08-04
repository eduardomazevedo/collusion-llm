# Assets Directory

This directory contains configuration files for the collusion detection LLM project.

## llm_config.json

Contains configuration data for various LLM providers and models, specifically focused on OpenAI models.

### Structure:
- **Provider Configuration**: Currently supports OpenAI as the primary provider
- **Model Specifications**: Detailed information for 10 different OpenAI models

### Model Information Includes:
- `input_token_price`: Cost per input token (in dollars)
- `output_token_price`: Cost per output token (in dollars)
- `supports_structured_output`: Boolean indicating structured output support
- `supports_json_output`: Boolean indicating JSON mode support
- `supports_batch`: Boolean indicating batch API processing support

### Available Models:
- **GPT-4.1 Series**: gpt-4.1-nano, gpt-4.1-mini, gpt-4.1
- **GPT-4 Optimized**: gpt-4o-mini, gpt-4o
- **GPT-4 Standard**: gpt-4-turbo, gpt-4
- **Legacy**: gpt-3.5-turbo
- **Completion Models**: davinci-002, babbage-002

## prompts.json

Contains a comprehensive collection of prompt variations for collusion detection analysis in earnings call transcripts.

### Structure:
- **Many Prompt Variations**: Each with a unique name used to identify the corresponding class.
- **Two Main Components per Prompt**:
  - `system_message`: Instructions for the LLM to analyze transcripts. This is the actual prompt text passed to a LLM.
  - `response_format`: Expected response structure. Corresponding classes are defined in the llm module to include a set of variables.

One response_format might work for many prompts. The response_format variables just need to correspond to what the prompt asks for.