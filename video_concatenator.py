#!/usr/bin/env python3
"""
Video Concatenator Script
Concatenates all videos in a folder sequentially by time (creation/modification time)
Supports multiple video formats and uses FFmpeg for processing
"""

import os
import sys
import glob
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
import argparse

# Supported video formats
SUPPORTED_FORMATS = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v']

def check_ffmpeg():
    """Check if FFmpeg is installed and available"""
    try:
        subprocess.run(['ffmpeg', '-version'], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL, 
                      check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def get_video_files(folder_path):
    """Get all video files from the specified folder"""
    video_files = []
    
    for ext in SUPPORTED_FORMATS:
        pattern = os.path.join(folder_path, f"*{ext}")
        video_files.extend(glob.glob(pattern))
        # Also check for uppercase extensions
        pattern = os.path.join(folder_path, f"*{ext.upper()}")
        video_files.extend(glob.glob(pattern))
    
    return video_files

def sort_files_by_time(files, sort_by='modified'):
    """Sort files by creation or modification time"""
    def get_time(file_path):
        stat = os.stat(file_path)
        if sort_by == 'created':
            # On macOS, use st_birthtime for creation time
            return getattr(stat, 'st_birthtime', stat.st_mtime)
        else:
            return stat.st_mtime
    
    return sorted(files, key=get_time)

def create_file_list(video_files, temp_dir):
    """Create a text file with the list of videos for FFmpeg concat filter"""
    list_file = os.path.join(temp_dir, 'file_list.txt')
    
    with open(list_file, 'w') as f:
        for video_file in video_files:
            # Escape single quotes and backslashes for FFmpeg
            escaped_path = video_file.replace("'", "'\\''")
            f.write(f"file '{escaped_path}'\n")
    
    return list_file

def get_video_info(video_file):
    """Get basic video information using ffprobe"""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', video_file
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError:
        return None

def concatenate_videos(video_files, output_file, temp_dir):
    """Concatenate videos using FFmpeg"""
    if not video_files:
        print("No video files found to concatenate.")
        return False
    
    if len(video_files) == 1:
        print(f"Only one video file found. Copying to output: {output_file}")
        subprocess.run(['cp', video_files[0], output_file], check=True)
        return True
    
    # Create file list for FFmpeg
    file_list = create_file_list(video_files, temp_dir)
    
    print(f"Concatenating {len(video_files)} videos...")
    print("Video files in order:")
    for i, video in enumerate(video_files, 1):
        file_time = datetime.fromtimestamp(os.path.getmtime(video))
        print(f"  {i}. {os.path.basename(video)} ({file_time.strftime('%Y-%m-%d %H:%M:%S')})")
    
    # FFmpeg command to concatenate videos
    cmd = [
        'ffmpeg', '-f', 'concat', '-safe', '0', '-i', file_list,
        '-c', 'copy', output_file, '-y'  # -y to overwrite output file
    ]
    
    try:
        print(f"\nRunning FFmpeg concatenation...")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ Successfully created: {output_file}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during concatenation: {e}")
        print(f"FFmpeg error output: {e.stderr}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Concatenate videos sequentially by time')
    parser.add_argument('folder', help='Folder containing video files')
    parser.add_argument('-o', '--output', default='concatenated_video.mp4', 
                       help='Output video file name (default: concatenated_video.mp4)')
    parser.add_argument('--sort-by', choices=['modified', 'created'], default='modified',
                       help='Sort by creation or modification time (default: modified)')
    parser.add_argument('--formats', nargs='+', default=SUPPORTED_FORMATS,
                       help=f'Video formats to include (default: {" ".join(SUPPORTED_FORMATS)})')
    
    args = parser.parse_args()
    
    # Check if folder exists
    if not os.path.isdir(args.folder):
        print(f"❌ Error: Folder '{args.folder}' does not exist.")
        sys.exit(1)
    
    # Check if FFmpeg is available
    if not check_ffmpeg():
        print("❌ Error: FFmpeg is not installed or not available in PATH.")
        print("Please install FFmpeg: https://ffmpeg.org/download.html")
        print("On macOS with Homebrew: brew install ffmpeg")
        sys.exit(1)
    
    # Get video files
    print(f"Searching for video files in: {args.folder}")
    video_files = get_video_files(args.folder)
    
    if not video_files:
        print(f"❌ No video files found in '{args.folder}'")
        print(f"Supported formats: {', '.join(SUPPORTED_FORMATS)}")
        sys.exit(1)
    
    # Sort files by time
    sorted_videos = sort_files_by_time(video_files, args.sort_by)
    
    # Create temporary directory for file list
    with tempfile.TemporaryDirectory() as temp_dir:
        # Concatenate videos
        success = concatenate_videos(sorted_videos, args.output, temp_dir)
    
    if success:
        file_size = os.path.getsize(args.output) / (1024 * 1024)  # Size in MB
        print(f"📹 Output file: {args.output} ({file_size:.1f} MB)")
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
