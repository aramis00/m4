"""Clinical notes tools for retrieving and searching text data.

This module provides specialized tools for clinical notes that prevent
context overflow by returning snippets instead of full text by default.

Tools:
- search_notes: Full-text search with result snippets
- get_note: Retrieve a single note by ID
- list_patient_notes: List available notes for a patient (metadata only)
"""

from dataclasses import dataclass
from enum import Enum

from m4.core.backends import get_backend
from m4.core.datasets import DatasetDefinition, Modality
from m4.core.tools.base import ToolInput, ToolOutput


class NoteType(str, Enum):
    """Types of clinical notes available."""

    DISCHARGE = "discharge"
    RADIOLOGY = "radiology"
    ALL = "all"


# Input models
@dataclass
class SearchNotesInput(ToolInput):
    """Input for search_notes tool."""

    query: str
    note_type: str = "all"  # discharge, radiology, or all
    limit: int = 5
    snippet_length: int = 300


@dataclass
class GetNoteInput(ToolInput):
    """Input for get_note tool."""

    note_id: str
    max_length: int | None = None  # Optional truncation


@dataclass
class ListPatientNotesInput(ToolInput):
    """Input for list_patient_notes tool."""

    subject_id: int
    note_type: str = "all"  # discharge, radiology, or all
    limit: int = 20


# Tool implementations
class SearchNotesTool:
    """Tool for full-text search across clinical notes.

    Returns snippets around matches to prevent context overflow.
    Use get_note() to retrieve full text of specific notes.
    """

    name = "search_notes"
    description = (
        "Search clinical notes by keyword. Returns snippets, not full text. "
        "Use get_note() to retrieve full content of a specific note."
    )
    input_model = SearchNotesInput
    output_model = ToolOutput

    required_modalities: frozenset[Modality] = frozenset({Modality.NOTES})
    supported_datasets: frozenset[str] | None = None

    def invoke(
        self, dataset: DatasetDefinition, params: SearchNotesInput
    ) -> ToolOutput:
        """Search notes and return snippets around matches."""
        backend = get_backend()
        backend_info = backend.get_backend_info(dataset)

        # Determine which tables to search
        tables_to_search = self._get_tables_for_type(params.note_type)

        if not tables_to_search:
            return ToolOutput(
                result=f"{backend_info}\n**Error:** Invalid note_type '{params.note_type}'. "
                f"Use 'discharge', 'radiology', or 'all'."
            )

        results = []
        search_term = params.query.replace("'", "''")  # Escape single quotes

        for table in tables_to_search:
            # Build search query with snippet extraction
            # Using LIKE for basic search - could be enhanced with full-text search
            sql = f"""
                SELECT
                    note_id,
                    subject_id,
                    CASE
                        WHEN POSITION(LOWER('{search_term}') IN LOWER(text)) > 0 THEN
                            SUBSTRING(
                                text,
                                GREATEST(1, POSITION(LOWER('{search_term}') IN LOWER(text)) - {params.snippet_length // 2}),
                                {params.snippet_length}
                            )
                        ELSE LEFT(text, {params.snippet_length})
                    END as snippet,
                    LENGTH(text) as note_length
                FROM {table}
                WHERE LOWER(text) LIKE '%{search_term.lower()}%'
                LIMIT {params.limit}
            """

            try:
                result = backend.execute_query(sql, dataset)
                if result.success and result.data:
                    results.append(f"\n**{table.upper()}:**\n{result.data}")
            except Exception as e:
                results.append(f"\n**{table.upper()}:** Error - {e}")

        if not results:
            return ToolOutput(
                result=f"{backend_info}\n**No matches found** for '{params.query}' "
                f"in {', '.join(tables_to_search)}."
            )

        output = (
            f"{backend_info}\n"
            f"**Search:** '{params.query}' (showing snippets of ~{params.snippet_length} chars)\n"
            f"{''.join(results)}\n\n"
            f"**Tip:** Use `get_note(note_id)` to retrieve full text of a specific note."
        )

        return ToolOutput(result=output)

    def _get_tables_for_type(self, note_type: str) -> list[str]:
        """Get table names for a note type."""
        note_type = note_type.lower()
        if note_type == "discharge":
            return ["discharge"]
        elif note_type == "radiology":
            return ["radiology"]
        elif note_type == "all":
            return ["discharge", "radiology"]
        return []

    def is_compatible(self, dataset: DatasetDefinition) -> bool:
        """Check compatibility."""
        if self.supported_datasets and dataset.name not in self.supported_datasets:
            return False
        if not self.required_modalities.issubset(dataset.modalities):
            return False
        return True


class GetNoteTool:
    """Tool for retrieving a single clinical note by ID.

    Returns the full note text. Use with caution as notes can be long.
    """

    name = "get_note"
    description = (
        "Retrieve full text of a specific clinical note by note_id. "
        "Notes can be very long - consider using search_notes() first "
        "to find relevant notes."
    )
    input_model = GetNoteInput
    output_model = ToolOutput

    required_modalities: frozenset[Modality] = frozenset({Modality.NOTES})
    supported_datasets: frozenset[str] | None = None

    def invoke(self, dataset: DatasetDefinition, params: GetNoteInput) -> ToolOutput:
        """Retrieve a single note by ID."""
        backend = get_backend()
        backend_info = backend.get_backend_info(dataset)

        # Note IDs contain the note type (e.g., "10000032_DS-1" for discharge)
        note_id = params.note_id.replace("'", "''")

        # Try both tables since we may not know which one contains the note
        for table in ["discharge", "radiology"]:
            sql = f"""
                SELECT
                    note_id,
                    subject_id,
                    text,
                    LENGTH(text) as note_length
                FROM {table}
                WHERE note_id = '{note_id}'
                LIMIT 1
            """

            try:
                result = backend.execute_query(sql, dataset)
                if result.success and result.data and "note_id" in result.data.lower():
                    # Found the note
                    # Optionally truncate if max_length specified
                    if params.max_length and len(result.data) > params.max_length:
                        truncated_result = result.data[: params.max_length]
                        return ToolOutput(
                            result=f"{backend_info}\n**Note (truncated to {params.max_length} chars):**\n{truncated_result}\n\n[...truncated...]"
                        )
                    return ToolOutput(result=f"{backend_info}\n{result.data}")
            except Exception:
                continue

        return ToolOutput(
            result=f"{backend_info}\n**Error:** Note '{params.note_id}' not found. "
            f"Use `list_patient_notes(subject_id)` or `search_notes(query)` "
            f"to find valid note IDs."
        )

    def is_compatible(self, dataset: DatasetDefinition) -> bool:
        """Check compatibility."""
        if self.supported_datasets and dataset.name not in self.supported_datasets:
            return False
        if not self.required_modalities.issubset(dataset.modalities):
            return False
        return True


class ListPatientNotesTool:
    """Tool for listing available notes for a patient.

    Returns metadata only (note IDs, types, lengths) - not full text.
    Use this to discover what notes exist before retrieving them.
    """

    name = "list_patient_notes"
    description = (
        "List available clinical notes for a patient by subject_id. "
        "Returns note metadata (IDs, types, lengths) without full text. "
        "Use get_note(note_id) to retrieve specific notes."
    )
    input_model = ListPatientNotesInput
    output_model = ToolOutput

    required_modalities: frozenset[Modality] = frozenset({Modality.NOTES})
    supported_datasets: frozenset[str] | None = None

    def invoke(
        self, dataset: DatasetDefinition, params: ListPatientNotesInput
    ) -> ToolOutput:
        """List notes for a patient without returning full text."""
        backend = get_backend()
        backend_info = backend.get_backend_info(dataset)

        tables_to_query = self._get_tables_for_type(params.note_type)

        if not tables_to_query:
            return ToolOutput(
                result=f"{backend_info}\n**Error:** Invalid note_type '{params.note_type}'. "
                f"Use 'discharge', 'radiology', or 'all'."
            )

        results = []

        for table in tables_to_query:
            # Query for metadata only - explicitly exclude full text
            sql = f"""
                SELECT
                    note_id,
                    subject_id,
                    '{table}' as note_type,
                    LENGTH(text) as note_length,
                    LEFT(text, 100) as preview
                FROM {table}
                WHERE subject_id = {params.subject_id}
                LIMIT {params.limit}
            """

            try:
                result = backend.execute_query(sql, dataset)
                if result.success and result.data:
                    results.append(f"\n**{table.upper()} NOTES:**\n{result.data}")
            except Exception as e:
                results.append(f"\n**{table.upper()}:** Error - {e}")

        if not results or all("no rows" in r.lower() for r in results):
            return ToolOutput(
                result=f"{backend_info}\n**No notes found** for subject_id {params.subject_id}.\n\n"
                f"**Tip:** Verify the subject_id exists in the related MIMIC-IV dataset."
            )

        output = (
            f"{backend_info}\n"
            f"**Notes for subject_id {params.subject_id}:**\n"
            f"{''.join(results)}\n\n"
            f"**Tip:** Use `get_note(note_id)` to retrieve full text of a specific note."
        )

        return ToolOutput(result=output)

    def _get_tables_for_type(self, note_type: str) -> list[str]:
        """Get table names for a note type."""
        note_type = note_type.lower()
        if note_type == "discharge":
            return ["discharge"]
        elif note_type == "radiology":
            return ["radiology"]
        elif note_type == "all":
            return ["discharge", "radiology"]
        return []

    def is_compatible(self, dataset: DatasetDefinition) -> bool:
        """Check compatibility."""
        if self.supported_datasets and dataset.name not in self.supported_datasets:
            return False
        if not self.required_modalities.issubset(dataset.modalities):
            return False
        return True
