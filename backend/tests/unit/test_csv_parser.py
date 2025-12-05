"""Unit tests for CSV parser utility."""

import pytest
from app.utils.csv_parser import parse_csv, parse_csv_preview, CSVParseError


@pytest.mark.unit
def test_parse_valid_csv():
    """Test parsing valid CSV file."""
    csv_content = b"ID,NAME,DESCRIPTION\n1,Python,Programming language\n2,JavaScript,Web language"

    result = parse_csv(csv_content)

    assert result["total_count"] == 2
    assert result["columns"] == ["ID", "NAME", "DESCRIPTION"]
    assert len(result["rows"]) == 2
    assert result["rows"][0]["ID"] == 1
    assert result["rows"][0]["NAME"] == "Python"
    assert result["rows"][1]["ID"] == 2
    assert result["rows"][1]["NAME"] == "JavaScript"


@pytest.mark.unit
def test_parse_csv_utf8_encoding():
    """Test parsing CSV with UTF-8 encoding."""
    csv_content = "ID,NAME\n1,François\n2,Björk".encode('utf-8')

    result = parse_csv(csv_content)

    assert result["total_count"] == 2
    assert result["rows"][0]["NAME"] == "François"
    assert result["rows"][1]["NAME"] == "Björk"


@pytest.mark.unit
def test_parse_csv_latin1_fallback():
    """Test parsing CSV falls back to latin-1 encoding."""
    # Create content with latin-1 specific characters
    csv_content = "ID,NAME\n1,café".encode('latin-1')

    result = parse_csv(csv_content)

    assert result["total_count"] == 1
    assert "NAME" in result["columns"]


@pytest.mark.unit
def test_parse_empty_csv_raises_error():
    """Test parsing empty CSV raises CSVParseError."""
    csv_content = b""

    with pytest.raises(CSVParseError) as exc_info:
        parse_csv(csv_content)

    assert "empty" in str(exc_info.value).lower()


@pytest.mark.unit
def test_parse_corrupted_csv_raises_error():
    """Test parsing corrupted CSV raises CSVParseError."""
    # Malformed CSV with mismatched quotes that pandas can't parse
    csv_content = b'ID,NAME\n1,"Unclosed quote\n2,Another row'

    with pytest.raises(CSVParseError) as exc_info:
        parse_csv(csv_content)

    assert "Failed to parse CSV" in str(exc_info.value)


@pytest.mark.unit
def test_parse_csv_header_only():
    """Test parsing CSV with only headers (no data rows)."""
    csv_content = b"ID,NAME,DESCRIPTION"

    result = parse_csv(csv_content)

    assert result["total_count"] == 0
    assert result["columns"] == ["ID", "NAME", "DESCRIPTION"]
    assert len(result["rows"]) == 0


@pytest.mark.unit
def test_parse_csv_with_special_characters():
    """Test parsing CSV with special characters in data."""
    csv_content = b"ID,NAME,DESCRIPTION\n1,Python,\"A language with commas, quotes, and newlines\"\n2,Go,Simple"

    result = parse_csv(csv_content)

    assert result["total_count"] == 2
    assert "commas" in result["rows"][0]["DESCRIPTION"]


@pytest.mark.unit
def test_parse_csv_preserves_column_names():
    """Test that column names are preserved exactly as in CSV."""
    csv_content = b"Job ID,Job Title,Company Name\n1,Engineer,TechCo"

    result = parse_csv(csv_content)

    assert "Job ID" in result["columns"]
    assert "Job Title" in result["columns"]
    assert "Company Name" in result["columns"]


@pytest.mark.unit
def test_parse_csv_sanitizes_formula_injection():
    """Test that CSV formula injection attempts are sanitized."""
    # CSV with potential formula injection attempts
    csv_content = b"ID,NAME,DESCRIPTION\n1,Python,=1+1\n2,Java,+cmd|calc\n3,Go,-2+5"

    result = parse_csv(csv_content)

    # Formulas should be prefixed with single quote
    assert result["rows"][0]["DESCRIPTION"] == "'=1+1"
    assert result["rows"][1]["DESCRIPTION"] == "'+cmd|calc"
    assert result["rows"][2]["DESCRIPTION"] == "'-2+5"


@pytest.mark.unit
def test_parse_csv_sanitizes_various_injection_chars():
    """Test sanitization of various formula injection characters."""
    csv_content = b"ID,VALUE\n1,=SUM(A1:A10)\n2,+1+1\n3,-1+1\n4,@SUM(B:B)\n5,|ping\n6,%systemroot%"

    result = parse_csv(csv_content)

    # All dangerous formulas should be sanitized
    assert result["rows"][0]["VALUE"] == "'=SUM(A1:A10)"
    assert result["rows"][1]["VALUE"] == "'+1+1"
    assert result["rows"][2]["VALUE"] == "'-1+1"
    assert result["rows"][3]["VALUE"] == "'@SUM(B:B)"
    assert result["rows"][4]["VALUE"] == "'|ping"
    assert result["rows"][5]["VALUE"] == "'%systemroot%"


@pytest.mark.unit
def test_parse_csv_does_not_sanitize_safe_content():
    """Test that normal content is not modified during sanitization."""
    csv_content = b"ID,NAME,DESCRIPTION\n1,Python,A great language\n2,Java,Object-oriented programming"

    result = parse_csv(csv_content)

    # Normal content should remain unchanged
    assert result["rows"][0]["DESCRIPTION"] == "A great language"
    assert result["rows"][1]["DESCRIPTION"] == "Object-oriented programming"


@pytest.mark.unit
def test_parse_csv_sanitizes_with_whitespace():
    """Test that formulas with leading whitespace are sanitized."""
    csv_content = b"ID,VALUE\n1,  =1+1\n2,\t+formula"

    result = parse_csv(csv_content)

    # Formulas with leading whitespace should be sanitized
    assert result["rows"][0]["VALUE"] == "'  =1+1"
    assert result["rows"][1]["VALUE"] == "'\t+formula"


@pytest.mark.unit
def test_parse_csv_sanitizes_non_string_values_unchanged():
    """Test that numeric values are not modified by sanitization."""
    csv_content = b"ID,VALUE\n1,123\n2,456.78"

    result = parse_csv(csv_content)

    # Numeric values should remain as numbers (pandas auto-converts)
    assert isinstance(result["rows"][0]["VALUE"], (int, float))
    assert isinstance(result["rows"][1]["VALUE"], (int, float))


# ============================================================================
# Tests for parse_csv_preview() - Story 2.3
# ============================================================================

@pytest.mark.unit
def test_parse_csv_preview_basic():
    """Test basic preview generation with valid CSV."""
    csv_content = b"ID,NAME,DESCRIPTION,CATEGORY,SUBCATEGORY\n1,Python,Programming language,Tech,Backend\n2,JavaScript,Web language,Tech,Frontend\n3,SQL,Database query,Tech,Data"

    result = parse_csv_preview(csv_content, preview_rows=2)

    assert result["columns"] == ["ID", "NAME", "DESCRIPTION", "CATEGORY", "SUBCATEGORY"]
    assert len(result["preview_rows"]) == 2
    assert result["total_rows"] == 3
    assert result["has_more"] is True
    assert result["preview_rows"][0]["NAME"] == "Python"
    assert result["preview_rows"][1]["NAME"] == "JavaScript"


@pytest.mark.unit
def test_parse_csv_preview_exact_count():
    """Test preview when preview_rows equals total_rows."""
    csv_content = b"ID,NAME\n1,Python\n2,Java\n3,Go"

    result = parse_csv_preview(csv_content, preview_rows=3)

    assert len(result["preview_rows"]) == 3
    assert result["total_rows"] == 3
    assert result["has_more"] is False


@pytest.mark.unit
def test_parse_csv_preview_less_than_requested():
    """Test preview when CSV has fewer rows than requested."""
    csv_content = b"ID,NAME\n1,Python\n2,Java"

    result = parse_csv_preview(csv_content, preview_rows=10)

    assert len(result["preview_rows"]) == 2
    assert result["total_rows"] == 2
    assert result["has_more"] is False


@pytest.mark.unit
def test_parse_csv_preview_has_more_flag():
    """Test has_more flag accuracy for various scenarios."""
    # More rows than preview
    csv_more = b"ID,NAME\n1,A\n2,B\n3,C\n4,D\n5,E\n6,F\n7,G\n8,H\n9,I\n10,J\n11,K"
    result_more = parse_csv_preview(csv_more, preview_rows=10)
    assert result_more["has_more"] is True
    assert result_more["total_rows"] == 11
    assert len(result_more["preview_rows"]) == 10

    # Exactly equal
    csv_equal = b"ID,NAME\n1,A\n2,B\n3,C"
    result_equal = parse_csv_preview(csv_equal, preview_rows=3)
    assert result_equal["has_more"] is False
    assert result_equal["total_rows"] == 3

    # Less than preview
    csv_less = b"ID,NAME\n1,A"
    result_less = parse_csv_preview(csv_less, preview_rows=5)
    assert result_less["has_more"] is False
    assert result_less["total_rows"] == 1


@pytest.mark.unit
def test_parse_csv_preview_default_rows():
    """Test default preview_rows parameter (should be 10)."""
    # Create CSV with 15 rows
    rows = ["ID,NAME"] + [f"{i},Item{i}" for i in range(1, 16)]
    csv_content = "\n".join(rows).encode('utf-8')

    result = parse_csv_preview(csv_content)  # No preview_rows specified

    assert len(result["preview_rows"]) == 10
    assert result["total_rows"] == 15
    assert result["has_more"] is True


@pytest.mark.unit
def test_parse_csv_preview_sanitizes_formulas():
    """Test that preview data is sanitized for CSV injection."""
    csv_content = b"ID,NAME,DESCRIPTION\n1,Python,=1+1\n2,Java,+cmd|calc\n3,Go,-2+5\n4,Ruby,@SUM(A:A)\n5,PHP,|ping\n6,C++,%systemroot%"

    result = parse_csv_preview(csv_content, preview_rows=10)

    # All formulas should be prefixed with single quote
    assert result["preview_rows"][0]["DESCRIPTION"] == "'=1+1"
    assert result["preview_rows"][1]["DESCRIPTION"] == "'+cmd|calc"
    assert result["preview_rows"][2]["DESCRIPTION"] == "'-2+5"
    assert result["preview_rows"][3]["DESCRIPTION"] == "'@SUM(A:A)"
    assert result["preview_rows"][4]["DESCRIPTION"] == "'|ping"
    assert result["preview_rows"][5]["DESCRIPTION"] == "'%systemroot%"


@pytest.mark.unit
def test_parse_csv_preview_safe_content_unchanged():
    """Test that normal content in preview is not modified."""
    csv_content = b"ID,NAME,DESCRIPTION\n1,Python,A great language\n2,Java,Object-oriented"

    result = parse_csv_preview(csv_content, preview_rows=5)

    # Normal content should remain unchanged
    assert result["preview_rows"][0]["DESCRIPTION"] == "A great language"
    assert result["preview_rows"][1]["DESCRIPTION"] == "Object-oriented"


@pytest.mark.unit
def test_parse_csv_preview_utf8_encoding():
    """Test preview with UTF-8 encoding."""
    csv_content = "ID,NAME,DESCRIPTION\n1,François,French developer\n2,Björk,Icelandic singer\n3,José,Spanish engineer".encode('utf-8')

    result = parse_csv_preview(csv_content, preview_rows=3)

    assert result["total_rows"] == 3
    assert result["preview_rows"][0]["NAME"] == "François"
    assert result["preview_rows"][1]["NAME"] == "Björk"
    assert result["preview_rows"][2]["NAME"] == "José"


@pytest.mark.unit
def test_parse_csv_preview_latin1_fallback():
    """Test preview falls back to latin-1 encoding."""
    csv_content = "ID,NAME\n1,café\n2,naïve".encode('latin-1')

    result = parse_csv_preview(csv_content, preview_rows=5)

    assert result["total_rows"] == 2
    assert "NAME" in result["columns"]
    assert len(result["preview_rows"]) == 2


@pytest.mark.unit
def test_parse_csv_preview_empty_raises_error():
    """Test preview with empty CSV raises CSVParseError."""
    csv_content = b""

    with pytest.raises(CSVParseError) as exc_info:
        parse_csv_preview(csv_content, preview_rows=10)

    assert "empty" in str(exc_info.value).lower()


@pytest.mark.unit
def test_parse_csv_preview_corrupted_raises_error():
    """Test preview with corrupted CSV raises CSVParseError."""
    csv_content = b'ID,NAME\n1,"Unclosed quote\n2,Another row'

    with pytest.raises(CSVParseError) as exc_info:
        parse_csv_preview(csv_content, preview_rows=5)

    assert "Failed to parse CSV" in str(exc_info.value)


@pytest.mark.unit
def test_parse_csv_preview_header_only():
    """Test preview with only headers (no data rows)."""
    csv_content = b"ID,NAME,DESCRIPTION,CATEGORY,SUBCATEGORY"

    result = parse_csv_preview(csv_content, preview_rows=10)

    assert result["total_rows"] == 0
    assert result["columns"] == ["ID", "NAME", "DESCRIPTION", "CATEGORY", "SUBCATEGORY"]
    assert len(result["preview_rows"]) == 0
    assert result["has_more"] is False


@pytest.mark.unit
def test_parse_csv_preview_preserves_column_names():
    """Test that preview preserves exact column names."""
    csv_content = b"Job ID,Job Title,Company Name,Location,Salary\n1,Engineer,TechCo,SF,100000"

    result = parse_csv_preview(csv_content, preview_rows=5)

    assert "Job ID" in result["columns"]
    assert "Job Title" in result["columns"]
    assert "Company Name" in result["columns"]
    assert "Location" in result["columns"]
    assert "Salary" in result["columns"]


@pytest.mark.unit
def test_parse_csv_preview_special_characters():
    """Test preview with special characters in data."""
    csv_content = b'ID,NAME,DESCRIPTION\n1,Python,"Language with commas, quotes, and newlines"\n2,Java,Simple description'

    result = parse_csv_preview(csv_content, preview_rows=5)

    assert result["total_rows"] == 2
    assert "commas" in result["preview_rows"][0]["DESCRIPTION"]


@pytest.mark.unit
def test_parse_csv_preview_large_file():
    """Test preview efficiently handles large CSV (only reads preview rows)."""
    # Create a large CSV with 1000 rows
    rows = ["ID,NAME,DESCRIPTION"] + [f"{i},Item{i},Description for item {i}" for i in range(1, 1001)]
    csv_content = "\n".join(rows).encode('utf-8')

    result = parse_csv_preview(csv_content, preview_rows=10)

    # Should return only 10 preview rows
    assert len(result["preview_rows"]) == 10
    assert result["total_rows"] == 1000
    assert result["has_more"] is True
    # Verify we got the first 10 rows
    assert result["preview_rows"][0]["NAME"] == "Item1"
    assert result["preview_rows"][9]["NAME"] == "Item10"


@pytest.mark.unit
def test_parse_csv_preview_numeric_values():
    """Test preview preserves numeric values correctly."""
    csv_content = b"ID,NAME,PRICE,QUANTITY\n1,Widget,29.99,100\n2,Gadget,49.50,50"

    result = parse_csv_preview(csv_content, preview_rows=5)

    # Numeric values should be preserved (pandas auto-converts)
    assert isinstance(result["preview_rows"][0]["ID"], (int, float))
    assert isinstance(result["preview_rows"][0]["PRICE"], (int, float))
    assert isinstance(result["preview_rows"][0]["QUANTITY"], (int, float))
