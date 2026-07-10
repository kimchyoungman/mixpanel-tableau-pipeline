"""
Tableau Hyper file writer using Hyper API.
"""
import logging
from datetime import datetime
from pathlib import Path

from tableauhyperapi import (
    Connection,
    CreateMode,
    HyperProcess,
    Inserter,
    Nullability,
    SqlType,
    TableDefinition,
    TableName,
    Telemetry,
)

from config.settings import DEFAULT_SCHEMA_NAME, DEFAULT_TABLE_NAME
from src.data_transformer import ColumnDef

logger = logging.getLogger(__name__)


class HyperWriter:
    """Write data to Tableau Hyper file format."""

    # Python type to Hyper SqlType mapping
    TYPE_MAP = {
        str: SqlType.text(),
        int: SqlType.big_int(),
        float: SqlType.double(),
        bool: SqlType.bool(),
        datetime: SqlType.timestamp(),
    }

    def __init__(self, output_path: str):
        """
        Initialize HyperWriter.

        Args:
            output_path: Path to the output .hyper file.
        """
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        self._hyper_process: HyperProcess | None = None
        self._connection: Connection | None = None

    def __enter__(self):
        """Context manager entry."""
        self._hyper_process = HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU)
        self._connection = Connection(
            self._hyper_process.endpoint,
            str(self.output_path),
            CreateMode.CREATE_AND_REPLACE
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def create_table(
        self,
        columns: list[ColumnDef],
        schema_name: str = DEFAULT_SCHEMA_NAME,
        table_name: str = DEFAULT_TABLE_NAME
    ) -> TableDefinition:
        """
        Create a table in the Hyper file.

        Args:
            columns: List of ColumnDef objects defining the schema.
            schema_name: Name of the schema (default: 'Extract').
            table_name: Name of the table (default: 'events').

        Returns:
            TableDefinition object.
        """
        if not self._connection:
            raise RuntimeError("HyperWriter not initialized. Use context manager.")

        # Create schema if it doesn't exist
        self._connection.catalog.create_schema_if_not_exists(schema_name)

        # Build column definitions
        hyper_columns = []
        for col in columns:
            sql_type = self.TYPE_MAP.get(col.python_type, SqlType.text())
            nullability = Nullability.NULLABLE if col.nullable else Nullability.NOT_NULLABLE
            hyper_columns.append(TableDefinition.Column(col.name, sql_type, nullability))

        # Create table definition
        table_def = TableDefinition(
            TableName(schema_name, table_name),
            hyper_columns
        )

        # Create the table
        self._connection.catalog.create_table(table_def)
        logger.info(f"Created table '{schema_name}.{table_name}' with {len(columns)} columns")

        return table_def

    def write_rows(self, table_def: TableDefinition, rows: list[tuple]) -> int:
        """
        Write rows to a table.

        Args:
            table_def: TableDefinition for the target table.
            rows: List of tuples to insert.

        Returns:
            Number of rows written.
        """
        if not self._connection:
            raise RuntimeError("HyperWriter not initialized. Use context manager.")

        if not rows:
            logger.warning("No rows to write")
            return 0

        with Inserter(self._connection, table_def) as inserter:
            inserter.add_rows(rows)
            inserter.execute()

        logger.info(f"Wrote {len(rows)} rows to {table_def.table_name}")
        return len(rows)

    def write_rows_chunked(
        self,
        table_def: TableDefinition,
        rows: list[tuple],
        chunk_size: int = 10000
    ) -> int:
        """
        Write rows in chunks for large datasets.

        Args:
            table_def: TableDefinition for the target table.
            rows: List of tuples to insert.
            chunk_size: Number of rows per chunk.

        Returns:
            Total number of rows written.
        """
        if not self._connection:
            raise RuntimeError("HyperWriter not initialized. Use context manager.")

        total_written = 0

        for i in range(0, len(rows), chunk_size):
            chunk = rows[i:i + chunk_size]
            with Inserter(self._connection, table_def) as inserter:
                inserter.add_rows(chunk)
                inserter.execute()
            total_written += len(chunk)
            logger.info(f"Written {total_written}/{len(rows)} rows")

        return total_written

    def close(self):
        """Close connection and process."""
        if self._connection:
            self._connection.close()
            self._connection = None
        if self._hyper_process:
            self._hyper_process.close()
            self._hyper_process = None
