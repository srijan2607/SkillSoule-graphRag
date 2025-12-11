from enum import Enum

class IngestionMode(str, Enum):
    """
    Ingestion mode enum.
    
    INCREMENTAL: Adds new records, updates changes, ignores unchanged. 
                 Safe mode, does NOT delete missing records.
    FULL: Replaces entire dataset. Deletes records not present in the new file.
          Dangerous mode, requires explicit confirmation.
    """
    INCREMENTAL = "incremental"
    FULL = "full"
