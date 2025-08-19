import json
import os

def analyze_transcript_lengths(file_path: str):
    """Analyzes the distribution of video transcript lengths from a JSON file."""
    if not os.path.exists(file_path):
        print(f"Error: The file '{file_path}' was not found.")
        return

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            videos = data.get('videos', []) # The list is nested under the 'videos' key
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from the file '{file_path}'.")
        return

    if not videos or not isinstance(videos, list):
        print("The file is empty or does not contain a valid list of videos.")
        return

    # Define categories for video length based on word count
    categories = {
        "Short (< 500 words)": 0,
        "Medium (500-1500 words)": 0,
        "Long (> 1500 words)": 0,
    }
    videos_with_transcripts = 0

    for video in videos:
        # The transcript is a dictionary, and the text is in the 'full_text' key
        transcript_obj = video.get('transcript')
        if transcript_obj and isinstance(transcript_obj, dict):
            transcript_text = transcript_obj.get('full_text', '')
            if transcript_text and isinstance(transcript_text, str):
                videos_with_transcripts += 1
                word_count = len(transcript_text.split())
                
                if word_count < 500:
                    categories["Short (< 500 words)"] += 1
                elif 500 <= word_count <= 1500:
                    categories["Medium (500-1500 words)"] += 1
                else:
                    categories["Long (> 1500 words)"] += 1
            
    total_videos = len(videos)
    print("Video Length Distribution (by Transcript Word Count)")
    print("="*55)
    for category, count in categories.items():
        percentage = (count / videos_with_transcripts) * 100 if videos_with_transcripts > 0 else 0
        print(f"{category}: {count} videos ({percentage:.1f}%)")
    print("-"*55)
    print(f"Total videos in file: {total_videos}")
    print(f"Videos with transcripts analyzed: {videos_with_transcripts}")

if __name__ == "__main__":
    # The script will analyze the v2 JSON file by default
    json_file = 'berg_exploration_with_transcripts_v2.json'
    analyze_transcript_lengths(json_file)
