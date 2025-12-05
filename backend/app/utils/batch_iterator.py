"""
Batch iteration utilities for CSV processing.

Provides generators and utilities for processing large datasets in batches
to manage memory usage and enable progress tracking.
"""

from typing import List, Generator, Tuple, TypeVar, Dict, Any

T = TypeVar('T')


def batch_iterator(
    items: List[T],
    batch_size: int
) -> Generator[Tuple[int, List[T]], None, None]:
    """
    Split list into batches and yield with batch number.

    Args:
        items: List of items to batch
        batch_size: Number of items per batch

    Yields:
        Tuple[batch_number, batch_items]
        - batch_number: 1-indexed batch number
        - batch_items: List of items in this batch

    Example:
        items = [1, 2, 3, 4, 5]
        for batch_num, batch in batch_iterator(items, batch_size=2):
            print(f"Batch {batch_num}: {batch}")
        # Output:
        # Batch 1: [1, 2]
        # Batch 2: [3, 4]
        # Batch 3: [5]
    """
    total_items = len(items)
    total_batches = (total_items + batch_size - 1) // batch_size  # Ceiling division

    for batch_num in range(1, total_batches + 1):
        start_idx = (batch_num - 1) * batch_size
        end_idx = min(start_idx + batch_size, total_items)
        batch_items = items[start_idx:end_idx]

        yield batch_num, batch_items


def calculate_batch_stats(total_items: int, batch_size: int) -> Dict[str, Any]:
    """
    Calculate batch processing statistics.

    Args:
        total_items: Total number of items
        batch_size: Items per batch

    Returns:
        dict: {
            "total_batches": int,
            "full_batches": int,
            "last_batch_size": int
        }

    Example:
        >>> calculate_batch_stats(1055, 100)
        {
            "total_batches": 11,
            "full_batches": 10,
            "last_batch_size": 55
        }
    """
    total_batches = (total_items + batch_size - 1) // batch_size
    full_batches = total_items // batch_size
    last_batch_size = total_items % batch_size or batch_size

    return {
        "total_batches": total_batches,
        "full_batches": full_batches,
        "last_batch_size": last_batch_size
    }
