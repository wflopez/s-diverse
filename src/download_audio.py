import sys
import csv
import argparse
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple
import logging


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_timestamp(timestamp_str: str) -> Tuple[float, float]:
    """
    Parse timestamp string in format 'HH:MM:SS - HH:MM:SS' to seconds.
    
    Args:
        timestamp_str: Timestamp string (e.g., '00:00:00 - 00:00:47')
    
    Returns:
        Tuple of (start_seconds, end_seconds)
    
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
        
        if start >= end:
            raise ValueError(f"Start time must be before end time: {timestamp_str}")
        
        return float(start), float(end)
    except Exception as e:
        raise ValueError(f"Failed to parse timestamp '{timestamp_str}': {e}")


def download_audio(url: str, output_path: str) -> bool:
    """
    Download audio from YouTube URL using yt-dlp.
    
    Args:
        url: YouTube URL
        output_path: Path where audio will be saved (without extension)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Downloading audio from: {url}")
        
        command = [
            'yt-dlp',
            '-f', 'bestaudio/best',
            '-x',  # Extract audio
            '--audio-format', 'wav',  # Output format
            '--audio-quality', '0',  # Best quality
            '--remote-components', 'ejs:github',  # Enable JS challenge solver
            '-o', output_path,
            url
        ]
        
        result = subprocess.run(command, capture_output=True, text=True, timeout=600)
        
        if result.returncode != 0:
            logger.error(f"yt-dlp error: {result.stderr}")
            return False
        
        logger.info(f"Successfully downloaded: {output_path}")
        return True
    except subprocess.TimeoutExpired:
        logger.error(f"Download timeout for {url}")
        return False
    except Exception as e:
        logger.error(f"Failed to download {url}: {e}")
        return False


def convert_to_wav_16k(input_file: str, output_file: str) -> bool:
    """
    Convert audio to WAV format at 16kHz with S16_LE codec using ffmpeg.
    
    Args:
        input_file: Input audio file path
        output_file: Output WAV file path
    
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Converting {input_file} to 16kHz WAV S16_LE")
        
        command = [
            'ffmpeg',
            '-i', input_file,
            '-acodec', 'pcm_s16le',  # S16_LE codec
            '-ar', '16000',  # 16kHz sample rate
            '-ac', '1',  # Mono
            '-y',  # Overwrite output
            output_file
        ]
        
        result = subprocess.run(command, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            logger.error(f"ffmpeg error: {result.stderr}")
            return False
        
        logger.info(f"Successfully converted: {output_file}")
        return True
    except subprocess.TimeoutExpired:
        logger.error(f"Conversion timeout for {input_file}")
        return False
    except Exception as e:
        logger.error(f"Failed to convert {input_file}: {e}")
        return False


def extract_segment(input_file: str, output_file: str, start: float, end: float) -> bool:
    """
    Extract a segment from audio file using ffmpeg.
    
    Args:
        input_file: Input audio file path
        output_file: Output audio file path
        start: Start time in seconds
        end: End time in seconds
    
    Returns:
        True if successful, False otherwise
    """
    try:
        duration = end - start
        logger.info(f"Extracting segment: {start:.2f}s - {end:.2f}s ({duration:.2f}s)")
        
        command = [
            'ffmpeg',
            '-i', input_file,
            '-ss', str(start),  # Start time
            '-to', str(end),    # End time
            '-acodec', 'pcm_s16le',  # S16_LE codec
            '-ar', '16000',  # 16kHz sample rate
            '-ac', '1',  # Mono
            '-y',  # Overwrite output
            output_file
        ]
        
        result = subprocess.run(command, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            logger.error(f"ffmpeg error: {result.stderr}")
            return False
        
        logger.info(f"Successfully extracted segment: {output_file}")
        return True
    except subprocess.TimeoutExpired:
        logger.error(f"Extraction timeout for {input_file}")
        return False
    except Exception as e:
        logger.error(f"Failed to extract segment from {input_file}: {e}")
        return False


def process_tsv_file(tsv_path: str, output_dir: str, temp_dir: str = None) -> None:
    """
    Process TSV file and download/segment audio.
    
    TSV must contain columns:
    - Timestamp: Format 'HH:MM:SS - HH:MM:SS'
    - Source: YouTube URL
    - Sample_ID: Output filename (without extension)
    - Disease: Disease type (optional, used for organizing output in subdirectories)
    
    Args:
        tsv_path: Path to input TSV file
        output_dir: Base directory where output WAV files will be saved
        temp_dir: Directory for temporary files (optional, uses system temp if None)
    """
    # Validate input file
    tsv_path = Path(tsv_path)
    if not tsv_path.exists():
        logger.error(f"TSV file not found: {tsv_path}")
        sys.exit(1)
    
    # Create base output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Base output directory: {output_path}")
    
    # Create temp directory if not provided
    if temp_dir is None:
        temp_dir = tempfile.mkdtemp(prefix='audio_download_')
    temp_path = Path(temp_dir)
    temp_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Temp directory: {temp_path}")
    
    # Read TSV file
    try:
        with open(tsv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')
            rows = list(reader)
    except Exception as e:
        logger.error(f"Failed to read TSV file: {e}")
        sys.exit(1)
    
    if not rows:
        logger.error("TSV file is empty")
        sys.exit(1)
    
    # Validate required columns
    required_columns = {'Timestamp', 'Source', 'Sample_ID'}
    if not required_columns.issubset(set(rows[0].keys())):
        logger.error(f"TSV must contain columns: {required_columns}")
        logger.error(f"Found columns: {set(rows[0].keys())}")
        sys.exit(1)
    
    has_disease_column = 'Disease' in rows[0].keys()
    logger.info(f"Processing {len(rows)} rows from TSV file")
    
    # Group rows by source URL
    sources: Dict[str, List[Dict]] = {}
    for row in rows:
        source = row['Source'].strip()
        if source not in sources:
            sources[source] = []
        sources[source].append(row)
    
    logger.info(f"Found {len(sources)} unique audio sources")
    
    # Process each unique source
    for source_idx, (source_url, source_rows) in enumerate(sources.items(), 1):
        logger.info(f"\n{'='*70}")
        logger.info(f"Processing source {source_idx}/{len(sources)}: {source_url}")
        logger.info(f"{'='*70}")
        
        # Download audio
        temp_audio = temp_path / f"source_{source_idx}.wav"
        
        if not download_audio(source_url, str(temp_audio.with_suffix(''))):
            logger.warning(f"Skipping source {source_url} due to download failure")
            continue
        
        # Find actual downloaded file (yt-dlp adds extension)
        downloaded_files = list(temp_path.glob(f"source_{source_idx}*"))
        if not downloaded_files:
            logger.error(f"No downloaded file found for source {source_url}")
            continue
        
        downloaded_file = downloaded_files[0]
        logger.info(f"Downloaded file: {downloaded_file}")
        
        # Convert to 16kHz WAV S16_LE if needed
        converted_audio = temp_path / f"source_{source_idx}_converted.wav"
        if not convert_to_wav_16k(str(downloaded_file), str(converted_audio)):
            logger.warning(f"Skipping source {source_url} due to conversion failure")
            continue
        
        # Process segments for this source
        for row in source_rows:
            try:
                sample_id = row['Sample_ID'].strip()
                timestamp_str = row['Timestamp'].strip()
                
                # Get disease if available
                disease = row.get('Disease', '').strip() if has_disease_column else 'Unknown'
                
                # Parse timestamp
                start, end = parse_timestamp(timestamp_str)
                
                # Create disease-specific output directory
                disease_output_path = output_path / disease
                disease_output_path.mkdir(parents=True, exist_ok=True)
                
                # Extract segment
                output_file = disease_output_path / f"{sample_id}.wav"
                if extract_segment(str(converted_audio), str(output_file), start, end):
                    logger.info(f"✓ Created: {output_file}")
                else:
                    logger.error(f"✗ Failed to extract segment for {sample_id}")
            
            except ValueError as e:
                logger.error(f"Skipping row: {e}")
            except Exception as e:
                logger.error(f"Error processing row {row}: {e}")
    
    logger.info(f"\n{'='*70}")
    logger.info("Processing complete!")
    logger.info(f"Output files saved to: {output_path}")
    logger.info(f"{'='*70}")


def main():
    
    parser = argparse.ArgumentParser(
        description='Download audio from YouTube and extract segments based on timestamps',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage (uses default output directory data/audio)
  python download_audio.py data/diversse.tsv
  
  # Custom output directory
  python download_audio.py data/diversse.tsv -o /custom/audio/path
  
  # With custom temp directory
  python download_audio.py data/diversse.tsv --temp-dir /tmp/audio_temp/
  
  # With debug logging
  python download_audio.py data/diversse.tsv --debug
  
TSV Format:
  The input TSV file must contain the following columns:
  - Sample_ID: Output filename (without extension)
  - Timestamp: Segment timing (format: HH:MM:SS - HH:MM:SS)
  - Source: YouTube URL
  - Disease: Disease type (optional, used to organize files in subdirectories)
  
Output Structure:
  Files are organized by disease in subdirectories:
  - data/audio/ALS/ALS_F01_01.wav
  - data/audio/PD/PD_M01_01.wav
  - etc.
        """
    )
    
    parser.add_argument(
        '--tsv_file',
        type=str,
        default='data/diversse.tsv',
        help='Path to input TSV file with columns: Sample_ID, Timestamp, Source, and Disease'
    )
    
    parser.add_argument(
        '-o', '--output-dir',
        type=str,
        default='data/audio',
        help='Directory to save output WAV files (default: data/audio). Files will be organized in disease subfolders.'
    )
    
    parser.add_argument(
        '--temp-dir',
        type=str,
        default=None,
        help='Optional directory for temporary files (default: system temp directory)'
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
    
    process_tsv_file(args.tsv_file, args.output_dir, args.temp_dir)


if __name__ == '__main__':
    main()
