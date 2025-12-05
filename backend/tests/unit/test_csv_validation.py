"""Unit tests for CSV validation service."""

import pytest
from app.services.csv_validation_service import CSVValidationService
from app.exceptions import CSVValidationError


# Skills CSV Tests

@pytest.mark.unit
def test_validate_skills_csv_success():
    """Test skills CSV validation with all required columns."""
    service = CSVValidationService()

    csv_content = b"ID,NAME,DESCRIPTION,CATEGORY,SUBCATEGORY\n1,Python,Programming language,Tech,Backend\n2,Java,OOP language,Tech,Backend"

    result = service.validate_skills_csv(csv_content)

    assert result["total_count"] == 2
    assert "ID" in result["columns"]
    assert "NAME" in result["columns"]
    assert "DESCRIPTION" in result["columns"]
    assert "CATEGORY" in result["columns"]
    assert "SUBCATEGORY" in result["columns"]


@pytest.mark.unit
def test_validate_skills_csv_only_required_columns():
    """Test skills CSV validation with only required columns (ID, NAME, DESCRIPTION, CATEGORY, SUBCATEGORY)."""
    service = CSVValidationService()

    csv_content = b"ID,NAME,DESCRIPTION,CATEGORY,SUBCATEGORY\n1,Python,Programming language,Tech,Backend\n2,JavaScript,Web language,Tech,Frontend"

    result = service.validate_skills_csv(csv_content)

    assert result["total_count"] == 2
    assert "ID" in result["columns"]
    assert "NAME" in result["columns"]
    assert "DESCRIPTION" in result["columns"]
    assert "CATEGORY" in result["columns"]
    assert "SUBCATEGORY" in result["columns"]


@pytest.mark.unit
def test_validate_skills_csv_missing_id_column():
    """Test skills CSV validation fails when ID column is missing."""
    service = CSVValidationService()

    csv_content = b"NAME,DESCRIPTION,CATEGORY,SUBCATEGORY\nPython,Programming language,Tech,Backend"

    with pytest.raises(CSVValidationError) as exc_info:
        service.validate_skills_csv(csv_content)

    error_detail = exc_info.value.detail
    assert error_detail["error"] == "csv_validation_failed"
    assert "Missing required columns" in error_detail["message"]
    assert "ID" in str(error_detail["validation_errors"])


@pytest.mark.unit
def test_validate_skills_csv_missing_name_column():
    """Test skills CSV validation fails when NAME column is missing."""
    service = CSVValidationService()

    csv_content = b"ID,DESCRIPTION,CATEGORY,SUBCATEGORY\n1,Programming language,Tech,Backend"

    with pytest.raises(CSVValidationError) as exc_info:
        service.validate_skills_csv(csv_content)

    error_detail = exc_info.value.detail
    assert "NAME" in str(error_detail["validation_errors"])


@pytest.mark.unit
def test_validate_skills_csv_case_insensitive():
    """Test column matching is case-insensitive for skills CSV."""
    service = CSVValidationService()

    # Columns in different case
    csv_content = b"id,name,description,category,subcategory\n1,Python,Language,Tech,Backend"

    result = service.validate_skills_csv(csv_content)

    assert result["total_count"] == 1


@pytest.mark.unit
def test_validate_skills_csv_mixed_case():
    """Test column matching with mixed case."""
    service = CSVValidationService()

    csv_content = b"Id,Name,Description,Category,SubCategory\n1,Python,Language,Tech,Backend"

    result = service.validate_skills_csv(csv_content)

    assert result["total_count"] == 1


@pytest.mark.unit
def test_validate_skills_csv_empty_data():
    """Test validation fails for header-only skills CSV."""
    service = CSVValidationService()

    csv_content = b"ID,NAME,DESCRIPTION,CATEGORY,SUBCATEGORY"  # Header only, no data rows

    with pytest.raises(CSVValidationError) as exc_info:
        service.validate_skills_csv(csv_content)

    error_detail = exc_info.value.detail
    assert "no data rows" in error_detail["message"].lower()


# Jobs CSV Tests

@pytest.mark.unit
def test_validate_jobs_csv_success():
    """Test jobs CSV validation with all required columns."""
    service = CSVValidationService()

    csv_content = b"Job ID,Job Title,Company Name,Location,standardized_skills\n1,Software Engineer,TechCo,Remote,Python|Java\n2,UI Designer,DesignCo,New York,Figma|Sketch"

    result = service.validate_jobs_csv(csv_content)

    assert result["total_count"] == 2
    assert "Job ID" in result["columns"]
    assert "Job Title" in result["columns"]
    assert "Company Name" in result["columns"]
    assert "Location" in result["columns"]
    assert "standardized_skills" in result["columns"]


@pytest.mark.unit
def test_validate_jobs_csv_only_required_columns():
    """Test jobs CSV validation with only required columns."""
    service = CSVValidationService()

    csv_content = b"Job ID,Job Title,Company Name,Location,standardized_skills\n1,Software Engineer,TechCo,Remote,Python|Java"

    result = service.validate_jobs_csv(csv_content)

    assert result["total_count"] == 1
    assert len(result["columns"]) == 5


@pytest.mark.unit
def test_validate_jobs_csv_missing_job_id():
    """Test jobs CSV validation fails when Job ID is missing."""
    service = CSVValidationService()

    csv_content = b"Job Title,Company Name,Location,standardized_skills\nSoftware Engineer,TechCo,Remote,Python"

    with pytest.raises(CSVValidationError) as exc_info:
        service.validate_jobs_csv(csv_content)

    error_detail = exc_info.value.detail
    assert "Job ID" in str(error_detail["validation_errors"])


@pytest.mark.unit
def test_validate_jobs_csv_missing_standardized_skills():
    """Test jobs CSV validation fails when standardized_skills is missing."""
    service = CSVValidationService()

    csv_content = b"Job ID,Job Title,Company Name,Location\n1,Software Engineer,TechCo,Remote"

    with pytest.raises(CSVValidationError) as exc_info:
        service.validate_jobs_csv(csv_content)

    error_detail = exc_info.value.detail
    assert "standardized_skills" in str(error_detail["validation_errors"])


@pytest.mark.unit
def test_validate_jobs_csv_case_insensitive():
    """Test column matching is case-insensitive for jobs CSV."""
    service = CSVValidationService()

    csv_content = b"job id,job title,company name,LOCATION,STANDARDIZED_SKILLS\n1,Software Engineer,TechCo,Remote,Python"

    result = service.validate_jobs_csv(csv_content)

    assert result["total_count"] == 1


# General CSV Validation Tests

@pytest.mark.unit
def test_validate_csv_corrupted_file():
    """Test validation fails gracefully for corrupted CSV."""
    service = CSVValidationService()

    # Malformed CSV with mismatched quotes
    csv_content = b'ID,NAME,DESCRIPTION,CATEGORY,SUBCATEGORY\n1,"Unclosed quote\n2,Another row'

    with pytest.raises(CSVValidationError) as exc_info:
        service.validate_skills_csv(csv_content)

    error_detail = exc_info.value.detail
    assert "Failed to parse" in error_detail["message"]


@pytest.mark.unit
def test_validate_csv_empty_file():
    """Test validation fails for completely empty CSV file."""
    service = CSVValidationService()

    csv_content = b""

    with pytest.raises(CSVValidationError) as exc_info:
        service.validate_skills_csv(csv_content)

    error_detail = exc_info.value.detail
    assert "Failed to parse" in error_detail["message"]


@pytest.mark.unit
def test_validation_error_includes_found_columns():
    """Test that validation error includes list of found columns."""
    service = CSVValidationService()

    csv_content = b"ID,DESCRIPTION,CATEGORY\n1,Some description,Tech"

    with pytest.raises(CSVValidationError) as exc_info:
        service.validate_skills_csv(csv_content)

    error_detail = exc_info.value.detail
    validation_errors = str(error_detail["validation_errors"])
    assert "Found columns" in validation_errors
    assert "ID" in validation_errors
    assert "DESCRIPTION" in validation_errors
    assert "CATEGORY" in validation_errors


@pytest.mark.unit
def test_validation_error_includes_required_columns():
    """Test that validation error includes list of required columns."""
    service = CSVValidationService()

    csv_content = b"DESCRIPTION,CATEGORY\nSome description,Tech"

    with pytest.raises(CSVValidationError) as exc_info:
        service.validate_skills_csv(csv_content)

    error_detail = exc_info.value.detail
    validation_errors = str(error_detail["validation_errors"])
    assert "Required columns" in validation_errors
    assert "ID" in validation_errors
    assert "NAME" in validation_errors
    assert "DESCRIPTION" in validation_errors
    assert "CATEGORY" in validation_errors
    assert "SUBCATEGORY" in validation_errors


@pytest.mark.unit
def test_validation_error_includes_missing_columns():
    """Test that validation error specifically lists missing columns."""
    service = CSVValidationService()

    csv_content = b"ID,DESCRIPTION\n1,Some description"  # Missing NAME, CATEGORY, SUBCATEGORY

    with pytest.raises(CSVValidationError) as exc_info:
        service.validate_skills_csv(csv_content)

    error_detail = exc_info.value.detail
    validation_errors = str(error_detail["validation_errors"])
    assert "Missing columns" in validation_errors
    assert "NAME" in validation_errors


# ============================================================================
# Tests for validate_and_preview methods - Story 2.3
# ============================================================================

@pytest.mark.unit
def test_validate_and_preview_skills_success():
    """Test validate_and_preview_skills with valid CSV."""
    service = CSVValidationService()

    csv_content = b"ID,NAME,DESCRIPTION,CATEGORY,SUBCATEGORY\n1,Python,Programming language,Tech,Backend\n2,JavaScript,Web language,Tech,Frontend\n3,SQL,Database query,Tech,Data"

    result = service.validate_and_preview_skills(csv_content, preview_rows=2)

    assert result["is_valid"] is True
    assert result["columns"] == ["ID", "NAME", "DESCRIPTION", "CATEGORY", "SUBCATEGORY"]
    assert len(result["preview_rows"]) == 2
    assert result["total_rows"] == 3
    assert result["has_more"] is True
    assert result["validation_errors"] == []
    assert result["preview_rows"][0]["NAME"] == "Python"
    assert result["preview_rows"][1]["NAME"] == "JavaScript"


@pytest.mark.unit
def test_validate_and_preview_jobs_success():
    """Test validate_and_preview_jobs with valid CSV."""
    service = CSVValidationService()

    csv_content = b"Job ID,Job Title,Company Name,Location,standardized_skills\n1,Software Engineer,TechCo,San Francisco,Python|JavaScript\n2,UI Designer,DesignCo,New York,Figma|Sketch"

    result = service.validate_and_preview_jobs(csv_content, preview_rows=5)

    assert result["is_valid"] is True
    assert result["columns"] == ["Job ID", "Job Title", "Company Name", "Location", "standardized_skills"]
    assert len(result["preview_rows"]) == 2
    assert result["total_rows"] == 2
    assert result["has_more"] is False
    assert result["validation_errors"] == []


@pytest.mark.unit
def test_validate_and_preview_skills_default_preview_rows():
    """Test validate_and_preview_skills with default preview_rows (10)."""
    service = CSVValidationService()

    # Create CSV with 15 rows
    rows = ["ID,NAME,DESCRIPTION,CATEGORY,SUBCATEGORY"] + [
        f"{i},Skill{i},Description {i},Category{i},Subcategory{i}"
        for i in range(1, 16)
    ]
    csv_content = "\n".join(rows).encode('utf-8')

    result = service.validate_and_preview_skills(csv_content)

    assert result["is_valid"] is True
    assert len(result["preview_rows"]) == 10
    assert result["total_rows"] == 15
    assert result["has_more"] is True


@pytest.mark.unit
def test_validate_and_preview_skills_custom_preview_rows():
    """Test validate_and_preview_skills with custom preview_rows."""
    service = CSVValidationService()

    csv_content = b"ID,NAME,DESCRIPTION,CATEGORY,SUBCATEGORY\n1,Python,Language,Tech,Backend\n2,Java,Language,Tech,Backend\n3,Go,Language,Tech,Backend\n4,Rust,Language,Tech,Backend\n5,Swift,Language,Tech,Mobile"

    result = service.validate_and_preview_skills(csv_content, preview_rows=3)

    assert len(result["preview_rows"]) == 3
    assert result["total_rows"] == 5
    assert result["has_more"] is True


@pytest.mark.unit
def test_validate_and_preview_skills_missing_columns():
    """Test validate_and_preview_skills fails with missing columns."""
    service = CSVValidationService()

    csv_content = b"ID,NAME,DESCRIPTION\n1,Python,Language"  # Missing CATEGORY, SUBCATEGORY

    with pytest.raises(CSVValidationError) as exc_info:
        service.validate_and_preview_skills(csv_content, preview_rows=10)

    error_detail = exc_info.value.detail
    assert "Missing required columns" in error_detail["message"]


@pytest.mark.unit
def test_validate_and_preview_jobs_missing_columns():
    """Test validate_and_preview_jobs fails with missing columns."""
    service = CSVValidationService()

    csv_content = b"Job ID,Job Title\n1,Engineer"  # Missing Company Name, Location, standardized_skills

    with pytest.raises(CSVValidationError) as exc_info:
        service.validate_and_preview_jobs(csv_content, preview_rows=10)

    error_detail = exc_info.value.detail
    assert "Missing required columns" in error_detail["message"]


@pytest.mark.unit
def test_validate_and_preview_skills_empty_data():
    """Test validate_and_preview_skills fails with no data rows."""
    service = CSVValidationService()

    csv_content = b"ID,NAME,DESCRIPTION,CATEGORY,SUBCATEGORY"  # Header only

    with pytest.raises(CSVValidationError) as exc_info:
        service.validate_and_preview_skills(csv_content, preview_rows=10)

    error_detail = exc_info.value.detail
    assert "no data rows" in error_detail["message"].lower()


@pytest.mark.unit
def test_validate_and_preview_skills_case_insensitive():
    """Test validate_and_preview_skills with case-insensitive columns."""
    service = CSVValidationService()

    csv_content = b"id,name,description,category,subcategory\n1,Python,Language,Tech,Backend"

    result = service.validate_and_preview_skills(csv_content, preview_rows=5)

    assert result["is_valid"] is True
    assert result["total_rows"] == 1


@pytest.mark.unit
def test_validate_and_preview_skills_sanitizes_formulas():
    """Test that validate_and_preview_skills sanitizes CSV injection."""
    service = CSVValidationService()

    csv_content = b"ID,NAME,DESCRIPTION,CATEGORY,SUBCATEGORY\n1,Python,=1+1,Tech,Backend\n2,Java,+cmd|calc,Tech,Backend"

    result = service.validate_and_preview_skills(csv_content, preview_rows=5)

    # Formulas should be sanitized
    assert result["preview_rows"][0]["DESCRIPTION"] == "'=1+1"
    assert result["preview_rows"][1]["DESCRIPTION"] == "'+cmd|calc"


@pytest.mark.unit
def test_validate_and_preview_jobs_sanitizes_formulas():
    """Test that validate_and_preview_jobs sanitizes CSV injection."""
    service = CSVValidationService()

    csv_content = b"Job ID,Job Title,Company Name,Location,standardized_skills\n1,=SUM(A:A),TechCo,SF,Python\n2,@COMMAND,DesignCo,NY,Figma"

    result = service.validate_and_preview_jobs(csv_content, preview_rows=5)

    # Formulas should be sanitized
    assert result["preview_rows"][0]["Job Title"] == "'=SUM(A:A)"
    assert result["preview_rows"][1]["Job Title"] == "'@COMMAND"


@pytest.mark.unit
def test_validate_and_preview_skills_preview_structure():
    """Test that validate_and_preview_skills returns correct structure."""
    service = CSVValidationService()

    csv_content = b"ID,NAME,DESCRIPTION,CATEGORY,SUBCATEGORY\n1,Python,Language,Tech,Backend\n2,Java,Language,Tech,Backend"

    result = service.validate_and_preview_skills(csv_content, preview_rows=5)

    # Verify structure matches CSVPreviewResponse requirements
    assert "is_valid" in result
    assert "columns" in result
    assert "preview_rows" in result
    assert "total_rows" in result
    assert "has_more" in result
    assert "validation_errors" in result
    assert isinstance(result["is_valid"], bool)
    assert isinstance(result["columns"], list)
    assert isinstance(result["preview_rows"], list)
    assert isinstance(result["total_rows"], int)
    assert isinstance(result["has_more"], bool)
    assert isinstance(result["validation_errors"], list)


@pytest.mark.unit
def test_validate_and_preview_jobs_preview_structure():
    """Test that validate_and_preview_jobs returns correct structure."""
    service = CSVValidationService()

    csv_content = b"Job ID,Job Title,Company Name,Location,standardized_skills\n1,Engineer,TechCo,SF,Python"

    result = service.validate_and_preview_jobs(csv_content, preview_rows=5)

    # Verify structure matches CSVPreviewResponse requirements
    assert "is_valid" in result
    assert "columns" in result
    assert "preview_rows" in result
    assert "total_rows" in result
    assert "has_more" in result
    assert "validation_errors" in result


@pytest.mark.unit
def test_validate_and_preview_skills_has_more_flag_accuracy():
    """Test has_more flag accuracy in validate_and_preview_skills."""
    service = CSVValidationService()

    # More rows than preview
    csv_more = b"ID,NAME,DESCRIPTION,CATEGORY,SUBCATEGORY\n" + b"\n".join([
        f"{i},Skill{i},Desc{i},Cat{i},Sub{i}".encode('utf-8')
        for i in range(1, 12)
    ])
    result_more = service.validate_and_preview_skills(csv_more, preview_rows=10)
    assert result_more["has_more"] is True

    # Exactly equal
    csv_equal = b"ID,NAME,DESCRIPTION,CATEGORY,SUBCATEGORY\n1,A,B,C,D\n2,E,F,G,H\n3,I,J,K,L"
    result_equal = service.validate_and_preview_skills(csv_equal, preview_rows=3)
    assert result_equal["has_more"] is False

    # Less than preview
    csv_less = b"ID,NAME,DESCRIPTION,CATEGORY,SUBCATEGORY\n1,A,B,C,D"
    result_less = service.validate_and_preview_skills(csv_less, preview_rows=5)
    assert result_less["has_more"] is False


@pytest.mark.unit
def test_validate_and_preview_jobs_extra_columns():
    """Test validate_and_preview_jobs accepts extra columns beyond required."""
    service = CSVValidationService()

    csv_content = b"Job ID,Job Title,Company Name,Location,standardized_skills,EXTRA1,EXTRA2\n1,Engineer,TechCo,SF,Python,Value1,Value2"

    result = service.validate_and_preview_jobs(csv_content, preview_rows=5)

    assert result["is_valid"] is True
    assert "EXTRA1" in result["columns"]
    assert "EXTRA2" in result["columns"]


@pytest.mark.unit
def test_validate_and_preview_skills_preserves_column_order():
    """Test that validate_and_preview_skills preserves original column order."""
    service = CSVValidationService()

    csv_content = b"NAME,ID,SUBCATEGORY,DESCRIPTION,CATEGORY\nPython,1,Backend,Language,Tech"

    result = service.validate_and_preview_skills(csv_content, preview_rows=5)

    # Column order should match CSV
    assert result["columns"] == ["NAME", "ID", "SUBCATEGORY", "DESCRIPTION", "CATEGORY"]
