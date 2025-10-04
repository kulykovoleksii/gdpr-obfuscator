"""
Format adapter pattern for multi-format support.
CSV is fully implemented. JSON and Parquet are stubs for future implementation.
"""

from abc import ABC, abstractmethod
from typing import List, IO, Callable, Union, Dict, Type
import csv
import logging

logger = logging.getLogger(__name__)


class FormatAdapter(ABC):
    """
    Abstract base class for file format handlers.

    Each adapter is responsible for:
    - Reading records from input stream
    - Applying obfuscation function to sensitive fields
    - Writing obfuscated records to output stream
    """

    @abstractmethod
    def process_stream(
        self,
        input_stream: IO[bytes],
        output_stream: IO[bytes],
        sensitive_fields: List[str],
        primary_key_field: str,
        obfuscate_fn: Callable[[str, str], str],
    ) -> int:
        """
        Process input stream and write obfuscated output.

        Args:
            input_stream: Binary input stream
            output_stream: Binary output stream
            sensitive_fields: List of field names to obfuscate
            primary_key_field: Name of primary key field
            obfuscate_fn: Function that takes (pk_value, field_name) and returns token

        Returns:
            Number of records processed
        """
        pass


class CSVAdapter(FormatAdapter):
    """
    CSV format adapter (fully implemented).

    Processes CSV files with header row.
    Uses streaming approach for memory efficiency.
    """

    def process_stream(
        self,
        input_stream: IO[bytes],
        output_stream: IO[bytes],
        sensitive_fields: List[str],
        primary_key_field: str,
        obfuscate_fn: Callable[[str, str], str],
    ) -> int:
        """Process CSV format using streaming approach."""
        from io import TextIOWrapper

        # Wrap byte streams for text processing
        text_in = TextIOWrapper(input_stream, encoding="utf-8")
        text_out = TextIOWrapper(output_stream, encoding="utf-8", write_through=True)

        try:
            reader = csv.DictReader(text_in)
            if not reader.fieldnames:
                raise ValueError("CSV has no header row")

            writer = csv.DictWriter(text_out, fieldnames=reader.fieldnames)
            writer.writeheader()

            count = 0
            for row in reader:
                count += 1
                pk_value = row.get(primary_key_field, "")

                # Obfuscate each sensitive field
                for field in sensitive_fields:
                    if field in row:
                        row[field] = obfuscate_fn(pk_value, field)

                writer.writerow(row)

            text_out.flush()
            logger.info("CSV: processed %d rows", count)
            return count
        finally:
            # Detach wrappers to prevent them from closing the underlying streams
            try:
                text_in.detach()
            except Exception as e:  # noqa: B110
                logger.debug("Failed to detach input wrapper: %s", e)
            try:
                text_out.detach()
            except Exception as e:  # noqa: B110
                logger.debug("Failed to detach output wrapper: %s", e)


class JSONAdapter(FormatAdapter):
    """
    JSON format adapter (stub - not yet implemented).

    Planned support for:
    - JSON arrays: [{"id":1,"email":"a@b.com"}, ...]
    - JSONL (line-delimited): one object per line

    TODO: Implement in Phase 2
    """

    def process_stream(
        self,
        input_stream: IO[bytes],
        output_stream: IO[bytes],
        sensitive_fields: List[str],
        primary_key_field: str,
        obfuscate_fn: Callable[[str, str], str],
    ) -> int:
        """Stub implementation - raises NotImplementedError."""
        raise NotImplementedError(
            "JSON format support is not yet implemented. "
            "Currently only CSV format is supported. "
            "See EXTENSION_PLAN.md for implementation details."
        )


class ParquetAdapter(FormatAdapter):
    """
    Parquet format adapter (stub - not yet implemented).

    Planned approach:
    - Use pyarrow library for reading/writing
    - Process row-by-row or in batches
    - Maintain column types

    TODO: Implement in Phase 2
    Requires: pip install pyarrow
    """

    def process_stream(
        self,
        input_stream: IO[bytes],
        output_stream: IO[bytes],
        sensitive_fields: List[str],
        primary_key_field: str,
        obfuscate_fn: Callable[[str, str], str],
    ) -> int:
        """Stub implementation - raises NotImplementedError."""
        raise NotImplementedError(
            "Parquet format support is not yet implemented. "
            "Currently only CSV format is supported. "
            "Parquet support requires pyarrow dependency. "
            "See EXTENSION_PLAN.md for implementation details."
        )


def get_adapter(file_format: str) -> Union[CSVAdapter, JSONAdapter, ParquetAdapter]:
    """
    Factory function to get appropriate adapter for file format.

    Args:
        file_format: One of 'csv', 'json', 'jsonl', 'parquet'

    Returns:
        FormatAdapter instance (CSVAdapter, JSONAdapter, or ParquetAdapter)

    Raises:
        ValueError: If format is not recognized
        NotImplementedError: If format is recognized but not yet implemented

    Example:
        adapter = get_adapter('csv')  # Returns CSVAdapter (works)
        adapter = get_adapter('json')  # Returns JSONAdapter
                                        #  (raises NotImplementedError)
    """
    format_lower = file_format.lower()

    format_map: Dict[str, Type[Union[CSVAdapter, JSONAdapter, ParquetAdapter]]] = {
        "csv": CSVAdapter,
        "json": JSONAdapter,
        "jsonl": JSONAdapter,
        "parquet": ParquetAdapter,
    }

    if format_lower not in format_map:
        supported = list(format_map.keys())
        raise ValueError(
            f"Unsupported format: '{file_format}'. " f"Supported formats: {supported}"
        )

    adapter_class = format_map[format_lower]
    return adapter_class()
    """
    Factory function to get appropriate adapter for file format.

    Args:
        file_format: One of 'csv', 'json', 'jsonl', 'parquet'

    Returns:
        FormatAdapter instance (CSVAdapter, JSONAdapter, or ParquetAdapter)

    Raises:
        ValueError: If format is not recognized
        NotImplementedError: If format is recognized but not yet implemented

    Example:
        adapter = get_adapter('csv')  # Returns CSVAdapter (works)
        adapter = get_adapter('json')  # Returns JSONAdapter
                                        #  (raises NotImplementedError)
    """
    format_lower = file_format.lower()

    format_map = {
        "csv": CSVAdapter,
        "json": JSONAdapter,
        "jsonl": JSONAdapter,
        "parquet": ParquetAdapter,
    }

    if format_lower not in format_map:
        supported = list(format_map.keys())
        raise ValueError(
            f"Unsupported format: '{file_format}'. " f"Supported formats: {supported}"
        )

    adapter_class = format_map[format_lower]
    return adapter_class()


def detect_format_from_filename(filename: str) -> str:
    """
    Detect file format from filename extension.

    Args:
        filename: Filename or path

    Returns:
        Format string ('csv', 'json', 'jsonl', 'parquet')

    Raises:
        ValueError: If format cannot be detected

    Example:
        detect_format_from_filename('data.csv')     # 'csv'
        detect_format_from_filename('data.json')    # 'json'
        detect_format_from_filename('data.jsonl')   # 'jsonl'
        detect_format_from_filename('data.parquet') # 'parquet'
    """
    filename_lower = filename.lower()

    if filename_lower.endswith(".csv"):
        return "csv"
    elif filename_lower.endswith(".jsonl") or filename_lower.endswith(".ndjson"):
        return "jsonl"
    elif filename_lower.endswith(".json"):
        return "json"
    elif filename_lower.endswith(".parquet") or filename_lower.endswith(".pq"):
        return "parquet"
    else:
        raise ValueError(
            f"Cannot detect format from filename: {filename}. "
            "Supported extensions: .csv, .json, .jsonl, .parquet"
        )


def list_supported_formats() -> dict:
    """
    Return dict of supported formats and their implementation status.

    Returns:
        Dict with format names as keys and status as values

    Example:
        {
            'csv': 'implemented',
            'json': 'planned',
            'jsonl': 'planned',
            'parquet': 'planned'
        }
    """
    return {
        "csv": "implemented",
        "json": "planned",
        "jsonl": "planned",
        "parquet": "planned",
    }
