import sys
import csv
import argparse
import logging
from pathlib import Path
from typing import List, Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_timestamp(timestamp_str: str) -> float:
    """
    Parse timestamp string in format 'HH:MM:SS - HH:MM:SS' and return duration in seconds.
    
    Args:
        timestamp_str: Timestamp string (e.g., '00:00:00 - 00:00:47')
    
    Returns:
        Duration in seconds as float
    
    Raises:
        ValueError: If timestamp format is invalid
    """
    try:
        parts = timestamp_str.split(' - ')
        if len(parts) != 2:
            raise ValueError(f"Invalid timestamp format: {timestamp_str}")
        
        def time_to_seconds(time_str):
            h, m, s = map(int, time_str.strip().split(':'))
            return h * 3600 + m * 60 + s
        
        start = time_to_seconds(parts[0])
        end = time_to_seconds(parts[1])
        
        duration = end - start
        
        if duration <= 0:
            raise ValueError(f"End time must be after start time: {timestamp_str}")
        
        return float(duration)
    except Exception as e:
        raise ValueError(f"Failed to parse timestamp '{timestamp_str}': {e}")


def add_duration_column(tsv_path: str) -> None:
    """
    Add Duration column to TSV file based on Timestamp column.
    
    Args:
        tsv_path: Path to input/output TSV file
    """
    tsv_path = Path(tsv_path)
    
    # Validate input file
    if not tsv_path.exists():
        logger.error(f"TSV file not found: {tsv_path}")
        sys.exit(1)
    
    logger.info(f"Reading TSV file: {tsv_path}")
    
    # Read TSV file
    try:
        with open(tsv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')
            rows = list(reader)
            fieldnames = reader.fieldnames
    except Exception as e:
        logger.error(f"Failed to read TSV file: {e}")
        sys.exit(1)
    
    if not rows:
        logger.error("TSV file is empty")
        sys.exit(1)
    
    # Validate required columns
    if 'Timestamp' not in fieldnames:
        logger.error("TSV file must contain 'Timestamp' column")
        logger.error(f"Found columns: {fieldnames}")
        sys.exit(1)
    
    # Check if Duration column already exists
    if 'Duration' in fieldnames:
        logger.warning("Duration column already exists. It will be overwritten.")
        fieldnames_output = fieldnames
    else:
        # Add Duration column after Timestamp column
        timestamp_index = fieldnames.index('Timestamp')
        fieldnames_output = fieldnames[:timestamp_index + 1] + ['Duration'] + fieldnames[timestamp_index + 1:]
    
    logger.info(f"Processing {len(rows)} rows")
    
    # Process each row
    processed_rows = []
    error_count = 0
    
    for idx, row in enumerate(rows, 1):
        try:
            timestamp_str = row.get('Timestamp', '').strip()
            duration = parse_timestamp(timestamp_str)
            row['Duration'] = str(duration)
            processed_rows.append(row)
            logger.debug(f"Row {idx}: {timestamp_str} → Duration: {duration}s")
        except ValueError as e:
            logger.error(f"Row {idx}: {e}")
            error_count += 1
            # Keep row without duration in case of error
            if 'Duration' not in row:
                row['Duration'] = ''
            processed_rows.append(row)
    
    if error_count > 0:
        logger.warning(f"Encountered {error_count} errors while processing rows")
    
    # Write TSV file
    try:
        logger.info(f"Writing updated TSV file: {tsv_path}")
        with open(tsv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames_output, delimiter='\t')
            writer.writeheader()
            writer.writerows(processed_rows)
        logger.info("✓ TSV file updated successfully")
    except Exception as e:
        logger.error(f"Failed to write TSV file: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Add Duration column to TSV file based on Timestamp column',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add duration column to TSV file
  python calculate_duration.py data/diversse.tsv
  
  # With debug logging
  python calculate_duration.py data/diversse.tsv --debug

Usage:
  The Timestamp column should be in format: HH:MM:SS - HH:MM:SS
  The Duration column will contain the duration in seconds.
  The output is written to the same file as the input.
        """
    )
    
    parser.add_argument(
        '--tsv_file',
        type=str,
        help='Path to input/output TSV file with Timestamp column'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger().setLevel(logging.DEBUG)
    
    add_duration_column(args.tsv_file)


if __name__ == '__main__':
    main()
