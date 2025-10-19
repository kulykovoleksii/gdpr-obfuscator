# Extension Plan: JSON and Parquet Support

## Status
**Current**: MVP complete (CSV support only)  
**Proposed**: Add JSON and Parquet format support  
**Estimated effort**: 3-5 days

---

## Overview

The current architecture is already designed for extensibility. Adding JSON and Parquet support requires minimal changes to the core obfuscation logic.

### Key Design Principle
**Format-specific logic is separated from obfuscation logic.** The core `obfuscate_value()` function remains unchanged; only the read/write adapters change.

---

## Architecture Changes

### Current Architecture (MVP)
```
┌─────────────────┐
│  CSV Input      │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│  obfuscate_csv_stream()     │
│  - Read CSV rows            │
│  - Call obfuscate_value()   │
│  - Write CSV rows           │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────┐
│  CSV Output     │
└─────────────────┘
```

### Proposed Architecture (With Extensions)
```
┌──────────────────────────────────┐
│  Input (CSV/JSON/Parquet)        │
└───────────────┬──────────────────┘
                │
                ▼
┌───────────────────────────────────┐
│  Format Detection / Selection     │
│  - Auto-detect from extension     │
│  - Or use explicit format param   │
└───────────────┬───────────────────┘
                │
                ▼
┌───────────────────────────────────┐
│  Format Adapter (Strategy Pattern)│
│  ┌─────────────────────────────┐  │
│  │  CSVAdapter                 │  │
│  │  JSONAdapter                │  │
│  │  ParquetAdapter             │  │
│  └─────────────────────────────┘  │
└───────────────┬───────────────────┘
                │
                ▼
┌───────────────────────────────────┐
│  Core Obfuscation Logic           │
│  obfuscate_value(key, pk, field)  │
│  - HMAC-SHA256 (unchanged)        │
└───────────────┬───────────────────┘
                │
                ▼
┌──────────────────────────────────┐
│  Output (same format as input)   │
└──────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Create Format Adapter Interface (1 day)

**New file**: `src/gdpr_obfuscator/format_adapters.py`

```python
from abc import ABC, abstractmethod

class FormatAdapter(ABC):
    """Abstract base class for file format handlers."""
    
    @abstractmethod
    def process_stream(
        self,
        input_stream: IO[bytes],
        output_stream: IO[bytes],
        sensitive_fields: List[str],
        primary_key_field: str,
        obfuscate_fn: Callable,  # Takes (pk_value, field_name) -> token
    ) -> int:
        """Process input, obfuscate, write output. Return record count."""
        pass
```

### Phase 2: Implement Format Adapters

#### CSV Adapter
- Refactor existing `obfuscate_csv_stream()` into `CSVAdapter` class
- No functional changes, just restructuring
- **No new dependencies**

#### JSON Adapter
- Support two modes:
  1. **JSON Array**: `[{"id":1,"email":"a@b.com"}, ...]`
  2. **JSONL** (line-delimited): One JSON object per line (better for large files)
- Use Python's built-in `json` module
- **No new dependencies**

#### Parquet Adapter
- Use `pyarrow` library for reading/writing Parquet files
- **New dependency**: `pyarrow>=10.0.0` (~30MB)
- Note: May need Lambda Layer for deployment

### Phase 3: Update Public API

**Modify**: `src/gdpr_obfuscator/obfuscator.py`

```python
def obfuscate_stream(
    input_stream: IO[bytes],
    output_stream: IO[bytes],
    sensitive_fields: List[str],
    file_format: str = "csv",  # NEW: csv|json|jsonl|parquet
    primary_key_field: str = "id",
    ...
) -> int:
    """Universal obfuscation function for any format."""
    adapter = get_adapter(file_format)
    return adapter.process_stream(...)
```

**Keep backward compatibility**: Existing `obfuscate_csv_stream()` continues to work.

### Phase 4: Update S3 Adapter

**Modify**: `src/gdpr_obfuscator/s3_adapter.py`

- Add optional `file_format` parameter
- Auto-detect format from S3 key extension if not specified
- Example: `s3://bucket/data.json` → auto-detect as JSON

### Phase 5: Update CLI

**Modify**: `src/gdpr_obfuscator/cli.py`

Add `--format` argument:
```bash
# Auto-detect from extension
python -m gdpr_obfuscator.cli --input data.json --output out.json --fields email

# Explicit format
python -m gdpr_obfuscator.cli --input data --output out --format json --fields email
```

### Phase 6: Testing

**Add tests**:
- `tests/test_json_adapter.py` - JSON array and JSONL formats
- `tests/test_parquet_adapter.py` - Parquet processing
- `tests/test_format_detection.py` - Auto-detection logic
- Integration tests with S3 (using moto or stubber)

**Test coverage target**: Maintain >90% coverage

---

## Dependency Impact

### Current Dependencies (MVP)
```
boto3>=1.34.0  # AWS SDK
```
**Total size**: ~10MB

### Additional Dependencies (Extensions)
```
pyarrow>=10.0.0  # For Parquet support
```
**Additional size**: ~30MB

### Lambda Deployment Consideration
- **Current package**: ~10MB (fits in Lambda direct upload limit of 50MB)
- **With Parquet support**: ~40MB (still within limit, but close)
- **Recommendation**: Use Lambda Layer for pyarrow if Parquet support is needed

---

## API Examples

### JSON Format

**Input file** (`data.json`):
```json
[
  {"id": 1, "name": "Alice", "email": "alice@example.com", "phone": "555-1234"},
  {"id": 2, "name": "Bob", "email": "bob@example.com", "phone": "555-5678"}
]
```

**CLI command**:
```bash
python -m gdpr_obfuscator.cli \
  --input data.json \
  --output data.obf.json \
  --fields email,phone \
  --format json
```

**Output file** (`data.obf.json`):
```json
[
  {"id": 1, "name": "Alice", "email": "a3f2e1d4c5b6a789", "phone": "b6a7891c2d3e4f50"},
  {"id": 2, "name": "Bob", "email": "c5d6e7f8a9b0c1d2", "phone": "d3e4f5a6b7c8d9e0"}
]
```

### JSONL Format (Line-Delimited JSON)

**Input file** (`data.jsonl`):
```
{"id": 1, "name": "Alice", "email": "alice@example.com"}
{"id": 2, "name": "Bob", "email": "bob@example.com"}
```

**Better for streaming large files** - processes one line at a time.

### Parquet Format

**CLI command**:
```bash
python -m gdpr_obfuscator.cli \
  --input data.parquet \
  --output data.obf.parquet \
  --fields email,ssn \
  --format parquet
```

**Note**: Parquet is binary format, cannot show example here.

---

## S3 Integration Examples

### Auto-detect format from S3 key
```python
from gdpr_obfuscator.s3_adapter import process_and_upload

# Format auto-detected from .json extension
process_and_upload(
    source_s3_uri='s3://input-bucket/raw/data.json',
    target_s3_uri='s3://output-bucket/obfuscated/data.json',
    sensitive_fields=['email', 'phone']
)
```

### Explicit format specification
```python
process_and_upload(
    source_s3_uri='s3://input-bucket/data',  # No extension
    target_s3_uri='s3://output-bucket/data.obf',
    sensitive_fields=['email'],
    file_format='json'  # Explicit format
)
```

---

## Lambda Handler Changes

**Current handler** supports CSV only:
```python
{
  "s3_uri": "s3://bucket/file.csv",
  "fields": ["email", "phone"],
  "primary_key": "id",
  "target_s3_uri": "s3://bucket/output.csv"
}
```

**Extended handler** adds format parameter:
```python
{
  "s3_uri": "s3://bucket/file.json",
  "fields": ["email", "phone"],
  "primary_key": "id",
  "target_s3_uri": "s3://bucket/output.json",
  "file_format": "json"  # NEW: optional, auto-detect if omitted
}
```

---

## Testing Strategy

### Unit Tests
- Test each adapter independently
- Mock S3 calls (use boto3 Stubber)
- Verify obfuscation correctness for each format

### Integration Tests
- End-to-end S3 download → process → upload
- Test with real sample files (small size)
- Verify output format matches input format

### Performance Tests
- Verify 1MB file processed in <60 seconds (requirement)
- Test memory usage (important for Lambda)
- Compare performance across formats

---

## Risks and Mitigations

### Risk 1: Parquet dependency size exceeds Lambda limits
**Mitigation**: 
- Deploy pyarrow as Lambda Layer
- Or use Lambda Container Image (up to 10GB)
- Document both deployment options

### Risk 2: Different formats have different primary key conventions
**Mitigation**: 
- Always require explicit `primary_key_field` parameter
- Fail fast with clear error if primary key missing
- Document common conventions (id, _id, pk)

### Risk 3: Large JSON files consume too much memory
**Mitigation**: 
- Implement JSONL (line-delimited) mode for streaming
- Document recommended format for large datasets
- Add file size warnings in documentation

---

## Documentation Updates Required

1. **README.md**: Add format support examples
2. **API.md** (new): Detailed API reference for all formats
3. **DEPLOYMENT.md**: Update Lambda deployment for Parquet layer
4. **requirements-runtime.txt**: Add conditional pyarrow dependency

---

## Backward Compatibility

**100% backward compatible** with MVP:
- All existing functions continue to work
- `obfuscate_csv_stream()` unchanged
- Default format is still CSV
- No breaking changes to API