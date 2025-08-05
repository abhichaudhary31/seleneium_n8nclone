#!/bin/bash

# Video Concatenator Runner Script
# Makes it easy to run the video concatenator with common options

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/video_concatenator.py"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    print_error "video_concatenator.py not found in script directory"
    exit 1
fi

# Check if FFmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    print_error "FFmpeg is not installed or not in PATH"
    print_info "Install FFmpeg with: brew install ffmpeg (macOS) or sudo apt install ffmpeg (Ubuntu)"
    exit 1
fi

# Show usage if no arguments
if [ $# -eq 0 ]; then
    echo "Video Concatenator Runner"
    echo "Usage: $0 <video_folder> [output_name] [sort_by]"
    echo ""
    echo "Examples:"
    echo "  $0 ./my_videos"
    echo "  $0 ./recordings meeting.mp4"
    echo "  $0 ./clips final_video.mp4 created"
    echo ""
    echo "Parameters:"
    echo "  video_folder  - Folder containing video files"
    echo "  output_name   - Output file name (optional, default: concatenated_video.mp4)"
    echo "  sort_by       - Sort by 'modified' or 'created' time (optional, default: modified)"
    exit 1
fi

VIDEO_FOLDER="$1"
OUTPUT_NAME="${2:-concatenated_video.mp4}"
SORT_BY="${3:-modified}"

# Check if folder exists
if [ ! -d "$VIDEO_FOLDER" ]; then
    print_error "Folder '$VIDEO_FOLDER' does not exist"
    exit 1
fi

print_info "Starting video concatenation..."
print_info "Input folder: $VIDEO_FOLDER"
print_info "Output file: $OUTPUT_NAME"
print_info "Sort by: $SORT_BY time"

# Run the Python script
python3 "$PYTHON_SCRIPT" "$VIDEO_FOLDER" -o "$OUTPUT_NAME" --sort-by "$SORT_BY"

# Check if successful
if [ $? -eq 0 ]; then
    print_info "Video concatenation completed successfully!"
    if [ -f "$OUTPUT_NAME" ]; then
        FILE_SIZE=$(du -h "$OUTPUT_NAME" | cut -f1)
        print_info "Output file size: $FILE_SIZE"
    fi
else
    print_error "Video concatenation failed"
    exit 1
fi
