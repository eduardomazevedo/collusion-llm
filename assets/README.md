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
- **30+ Prompt Variations**: Each with a unique identifier
- **Two Main Components per Prompt**:
  - `system_message`: Instructions for the LLM to analyze transcripts
  - `response_format`: Expected response structure

### Prompt Categories:

#### 1. Price-Capacity Combined Prompts
- Focus on both price-fixing and capacity limitation
- Versions: PriceCapacity_V1 through V6

#### 2. Capacity-Focused Prompts
- Target capacity discipline and supply limitation
- Versions: SimpleCapacity_V1 through V8.4

#### 3. Price-Focused Prompts
- Target price coordination and increases
- Versions: SimplePrice_V1 through V9

#### 4. Specialized Prompts
- **Signal Detection**: Look for various signals of collusive intent
- **Contingent Behavior**: Focus on conditional market responses (V1-V2)
- **Comprehensive Analysis**: Include excerpts and detailed reasoning (V1-V3)
- **Binary Detection**: Simple yes/no collusion detection
- **Special Formats**: Indicators, JSON output, and other structured formats

### Response Formats:
- `PriceCapacity`: Combined price and capacity scores
- `CapacityScoreReasoning`: Capacity score with explanation
- `SimplePrice`: Price coordination score only
- `ComprehensiveAnalysis`: Detailed analysis with excerpts
- Various other specialized formats

Each prompt is designed to detect different aspects of potential collusive behavior in corporate communications, with varying levels of sophistication and focus areas.