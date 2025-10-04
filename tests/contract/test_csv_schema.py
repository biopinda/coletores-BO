"""Contract test for CSV export schema"""

import pytest
from pydantic import ValidationError
from src.models.contracts import CSVReportRow


class TestCSVReportRow:
    """Test CSVReportRow schema"""

    def test_valid_row(self):
        """Valid CSV row with all required fields"""
        row = CSVReportRow(
            canonicalName="Forzza, R.C.",
            variations="Forzza, R.C.;R.C. Forzza;Rafaela C. Forzza",
            occurrenceCounts="1523;847;234"
        )
        assert row.canonicalName == "Forzza, R.C."
        assert ";" in row.variations
        assert ";" in row.occurrenceCounts

    def test_count_alignment(self):
        """Count alignment: variations and counts must have same number of entries"""
        row = CSVReportRow(
            canonicalName="Silva, J.",
            variations="Silva, J.;J. Silva",
            occurrenceCounts="100;50"
        )
        
        variations_count = len(row.variations.split(';'))
        counts_count = len(row.occurrenceCounts.split(';'))
        assert variations_count == counts_count

    def test_semicolon_separated(self):
        """Variations and counts must be semicolon-separated"""
        row = CSVReportRow(
            canonicalName="Test",
            variations="Var1;Var2;Var3",
            occurrenceCounts="10;20;30"
        )
        assert row.variations.count(';') == 2
        assert row.occurrenceCounts.count(';') == 2

    def test_no_confidence_fields(self):
        """CSV row should NOT have confidence fields (per FR-025)"""
        row = CSVReportRow(
            canonicalName="Test",
            variations="Test",
            occurrenceCounts="1"
        )
        # Verify model doesn't have confidence fields
        assert not hasattr(row, 'confidence')
        assert not hasattr(row, 'classification_confidence')
        assert not hasattr(row, 'grouping_confidence')
