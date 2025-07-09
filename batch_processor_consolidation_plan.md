# Batch Processor Consolidation Plan

## Current State
- `batch_processor_runner.py` (206 lines): Handles batch processing for specific company IDs
- `big_batch_runner.py` (861 lines): Handles large-scale batch processing with complex state management

## Key Differences
1. **Scope**: 
   - `batch_processor_runner`: Processes specific company IDs
   - `big_batch_runner`: Processes all companies in batches

2. **State Management**:
   - `batch_processor_runner`: Simple, relies on BatchProcessor module
   - `big_batch_runner`: Complex CSV-based tracking with resume capability

3. **Features**:
   - `big_batch_runner` has additional features:
     - Queue limit handling
     - Batch splitting based on token limits
     - Fallback to individual API calls
     - Progress tracking with CSV

## Consolidation Strategy

### Phase 1: Enhance modules/batch_processor.py
1. Add batch splitting logic from big_batch_runner
2. Add CSV tracking capability
3. Add queue limit handling
4. Add cost estimation features

### Phase 2: Create Unified Runner
Create a new `unified_batch_runner.py` that:
1. Accepts both company ID lists and "all companies" mode
2. Uses enhanced BatchProcessor module
3. Supports all operations: create, submit, status, process, resume
4. Handles both small and large batches efficiently

### Phase 3: Migration
1. Update shell scripts to use unified runner
2. Test thoroughly
3. Remove old runners

## Implementation Notes
- Keep backward compatibility with existing command-line interfaces
- Preserve all error handling and retry logic
- Maintain CSV tracking format for resume capability
- Add proper logging throughout

## Risk Mitigation
- Create comprehensive tests before removing old code
- Run parallel testing with production data
- Keep backups of original scripts until fully validated