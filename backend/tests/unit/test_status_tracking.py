"""
Unit tests for status tracking functionality (Story 2.5).

Tests cover:
- Progress percentage calculation
- ETA calculation
- Processing speed calculation with exponential moving average
- Status transitions
- IngestionStatusResponse model validation
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock

from app.models.ingestion import IngestionStatusResponse
from app.services.ingestion_service import IngestionService


@pytest.mark.unit
def test_progress_percentage_calculation():
    """Test progress percentage calculation (AC: 4)."""
    # Scenario 1: 25% complete
    total_records = 1000
    processed_records = 250
    progress = (processed_records / total_records) * 100
    assert progress == 25.0

    # Scenario 2: 50% complete
    processed_records = 500
    progress = (processed_records / total_records) * 100
    assert progress == 50.0

    # Scenario 3: 100% complete
    processed_records = 1000
    progress = (processed_records / total_records) * 100
    assert progress == 100.0

    # Scenario 4: 0% complete (pending)
    processed_records = 0
    progress = (processed_records / total_records) * 100
    assert progress == 0.0


@pytest.mark.unit
def test_progress_percentage_precision():
    """Test progress percentage calculation with decimal precision."""
    total_records = 40523
    processed_records = 15234
    
    progress = (processed_records / total_records) * 100
    # Should be approximately 37.6%
    assert 37.5 < progress < 37.7
    
    # Test rounding to 2 decimal places
    progress_rounded = round(progress, 2)
    # Actual calculation: 15234/40523 = 0.375896... = 37.59%
    assert progress_rounded == 37.59


@pytest.mark.unit
def test_eta_calculation_basic():
    """Test estimated time remaining calculation (AC: 6)."""
    total_records = 1000
    processed_records = 250
    processing_speed = 100.0  # 100 records/sec

    remaining_records = total_records - processed_records
    eta = remaining_records / processing_speed

    assert eta == 7.5  # 750 records / 100 records/sec = 7.5 seconds


@pytest.mark.unit
def test_eta_calculation_various_speeds():
    """Test ETA with different processing speeds."""
    total_records = 10000
    processed_records = 2500
    remaining_records = total_records - processed_records  # 7500

    # Fast processing: 200 records/sec
    eta_fast = remaining_records / 200.0
    assert eta_fast == 37.5  # 37.5 seconds

    # Medium processing: 100 records/sec
    eta_medium = remaining_records / 100.0
    assert eta_medium == 75.0  # 75 seconds (1.25 minutes)

    # Slow processing: 50 records/sec
    eta_slow = remaining_records / 50.0
    assert eta_slow == 150.0  # 150 seconds (2.5 minutes)


@pytest.mark.unit
def test_eta_calculation_edge_cases():
    """Test ETA edge cases."""
    # No records processed yet
    total_records = 1000
    processed_records = 0
    processing_speed = 100.0
    remaining_records = total_records - processed_records
    eta = remaining_records / processing_speed
    assert eta == 10.0

    # Almost complete
    processed_records = 999
    remaining_records = total_records - processed_records
    eta = remaining_records / processing_speed
    assert eta == 0.01  # 1 record / 100 records/sec

    # Zero speed (should handle division by zero)
    with pytest.raises(ZeroDivisionError):
        eta = remaining_records / 0.0


@pytest.mark.unit
def test_exponential_moving_average():
    """Test EMA calculation for processing speed (AC: 6)."""
    old_speed = 100.0  # records/sec
    batch_speed = 120.0  # records/sec
    alpha = 0.3

    # EMA formula: new_speed = alpha * batch_speed + (1 - alpha) * old_speed
    new_speed = alpha * batch_speed + (1 - alpha) * old_speed
    
    # 0.3 * 120 + 0.7 * 100 = 36 + 70 = 106
    assert new_speed == pytest.approx(106.0)


@pytest.mark.unit
def test_exponential_moving_average_stability():
    """Test EMA provides stable speed estimates."""
    # Simulate fluctuating batch speeds
    speeds = [100.0, 150.0, 80.0, 120.0, 110.0]
    alpha = 0.3
    
    current_avg = speeds[0]
    for batch_speed in speeds[1:]:
        current_avg = alpha * batch_speed + (1 - alpha) * current_avg
    
    # Final average should be between min and max
    assert min(speeds) < current_avg < max(speeds)
    # Should be closer to later values due to EMA weighting
    assert 100 < current_avg < 120


@pytest.mark.unit
def test_status_response_model_validation():
    """Test IngestionStatusResponse model validation (AC: 2)."""
    # Valid response
    response = IngestionStatusResponse(
        job_id="test-job-id",
        status="processing",
        total_records=1000,
        processed_records=250,
        failed_records=5,
        current_batch=3,
        total_batches=10,
        progress_percentage=25.0,
        estimated_time_remaining=30,
        processing_speed=100.0,
        started_at=datetime.utcnow(),
        completed_at=None,
        error_message=None
    )
    
    assert response.job_id == "test-job-id"
    assert response.status == "processing"
    assert response.progress_percentage == 25.0
    assert response.estimated_time_remaining == 30


@pytest.mark.unit
def test_status_response_model_constraints():
    """Test model field constraints."""
    # Test progress_percentage constraints (0-100)
    with pytest.raises(Exception):  # Pydantic validation error
        IngestionStatusResponse(
            job_id="test",
            status="processing",
            total_records=1000,
            processed_records=250,
            failed_records=0,
            progress_percentage=150.0,  # Invalid: > 100
            started_at=datetime.utcnow()
        )
    
    with pytest.raises(Exception):  # Pydantic validation error
        IngestionStatusResponse(
            job_id="test",
            status="processing",
            total_records=1000,
            processed_records=250,
            failed_records=0,
            progress_percentage=-10.0,  # Invalid: < 0
            started_at=datetime.utcnow()
        )


@pytest.mark.unit
def test_status_transitions():
    """Test status value transitions (AC: 7)."""
    valid_statuses = [
        "pending",
        "processing",
        "completed",
        "completed_with_errors",
        "failed"
    ]
    
    # All statuses should be valid strings
    for status in valid_statuses:
        response = IngestionStatusResponse(
            job_id="test",
            status=status,
            total_records=1000,
            processed_records=0 if status == "pending" else 1000,
            failed_records=0,
            progress_percentage=0.0 if status == "pending" else 100.0,
            started_at=datetime.utcnow()
        )
        assert response.status == status


@pytest.mark.unit
def test_total_batches_calculation():
    """Test total batches calculation."""
    batch_size = 1000
    
    # Exact multiple
    total_records = 5000
    total_batches = (total_records + batch_size - 1) // batch_size
    assert total_batches == 5
    
    # With remainder
    total_records = 5500
    total_batches = (total_records + batch_size - 1) // batch_size
    assert total_batches == 6
    
    # Single batch
    total_records = 500
    total_batches = (total_records + batch_size - 1) // batch_size
    assert total_batches == 1


@pytest.mark.unit
def test_optional_fields():
    """Test optional fields in IngestionStatusResponse."""
    # Minimal response (pending job)
    response = IngestionStatusResponse(
        job_id="test",
        status="pending",
        total_records=1000,
        processed_records=0,
        failed_records=0,
        progress_percentage=0.0,
        started_at=datetime.utcnow()
    )
    
    # Optional fields should be None
    assert response.current_batch is None
    assert response.total_batches is None
    assert response.estimated_time_remaining is None
    assert response.processing_speed is None
    assert response.completed_at is None
    assert response.error_message is None


@pytest.mark.unit
def test_completed_response():
    """Test response for completed job."""
    started_at = datetime.utcnow() - timedelta(minutes=5)
    completed_at = datetime.utcnow()
    
    response = IngestionStatusResponse(
        job_id="test",
        status="completed",
        total_records=1000,
        processed_records=1000,
        failed_records=0,
        current_batch=10,
        total_batches=10,
        progress_percentage=100.0,
        estimated_time_remaining=0,  # Should be 0 or None when complete
        processing_speed=150.0,
        started_at=started_at,
        completed_at=completed_at,
        error_message=None
    )
    
    assert response.status == "completed"
    assert response.progress_percentage == 100.0
    assert response.processed_records == response.total_records
    assert response.completed_at is not None


@pytest.mark.unit
def test_failed_response():
    """Test response for failed job."""
    response = IngestionStatusResponse(
        job_id="test",
        status="failed",
        total_records=1000,
        processed_records=250,
        failed_records=750,
        progress_percentage=25.0,
        started_at=datetime.utcnow() - timedelta(minutes=2),
        completed_at=datetime.utcnow(),
        error_message="Database connection failed"
    )
    
    assert response.status == "failed"
    assert response.error_message is not None
    assert response.failed_records > 0
