from openai import OpenAI
import re
import random
import os
import requests
from gtts import gTTS
import assemblyai as aai
import datetime
import subprocess
import moviepy as mpe
from moviepy import VideoFileClip
from moviepy.video.fx import Crop
from moviepy.video.fx import Resize
# Configuration
CONFIG = {
    "openrouter": {
        "api_key":"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",
        "base_url": "https://openrouter.ai/api/v1"
    },
    "pexels": {
        "api_key": "b4w7n5s901KPekznrDDQ7XxdkLVPsa4KhCZ8z46okQdmeqyVr5DdZh1f"
    },
    "assemblyai": {
        "api_key": "cef9801d8990492b9c93ca12c5e29b75"
    },
    "output": {
        "resolution": (1080, 1920),
        "fps": 30,
        "subtitle_style": "Fontname=Roboto-Bold,Fontsize=18,PrimaryColour=&HFFFFFF,horizontal_align='center', vertical_align='center',margin=(20, 200)"
    }
}

# Initialize clients
client = OpenAI(
    api_key=CONFIG["openrouter"]["api_key"],
    base_url=CONFIG["openrouter"]["base_url"]
)
aai.settings.api_key = CONFIG["assemblyai"]["api_key"]

def generate_reddit_style_story():
    """Generate a Reddit-style story using AI"""
    try:
        name = random.choice(["Alex", "Jamie", "Taylor", "Jordan", "Casey"])
        age = random.randint(18, 45)
        gender = random.choice(["male", "female", "non-binary"])
        
        prompt = f"""Create a 60-second Reddit-style story in first-person perspective with:
        - Name: {name}
        - Age: {age}
        - Gender: {gender}
        - Clear narrative arc (hook, conflict, resolution)
        - Punchline/moral ending
        - 150-200 words"""
        
        response = client.chat.completions.create(
            model="deepseek/deepseek-r1:free",
            messages=[
                {"role": "system", "content": "You are a viral Reddit storyteller."},
                {"role": "user", "content": prompt},
            ]
        )
        
        text = response.choices[0].message.content
        clean_text = re.sub(r'[^\x20-\x7E]+', '', text).strip()
        
        if len(clean_text) < 100:
            raise ValueError("Generated story is too short")
            
        return {
            "title": f"AITA with {name}?",
            "content": clean_text,
            "author": f"{name} ({age}{gender[0].upper()})"
        }
    
    except Exception as e:
        print(f"Story generation failed: {e}")
        return None

def text_to_speech(text, output_file="narration.mp3"):
    """Convert text to speech using gTTS"""
    try:
        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(output_file)
        return output_file
    except Exception as e:
        print(f"Text-to-speech failed: {e}")
        return None

def fetch_stock_video(duration=60):
    """Get high-quality stock video from Pexels API"""
    try:
        themes = ["subway surfer", "city timelapse", "driving highway", "aerial view", "time lapse city"]
        query = random.choice(themes)
        
        url = f"https://api.pexels.com/videos/search?query={query}&per_page=5&min_duration={duration-10}&orientation=landscape"
        headers = {"Authorization": CONFIG["pexels"]["api_key"]}
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        if not data.get("videos"):
            raise ValueError("No videos found")
        
        # Sort videos by quality (highest first)
        for video in sorted(data["videos"], key=lambda v: v["width"], reverse=True):
            video_files = video["video_files"]
            
            # Prefer HD/4K MP4 files in this order
            quality_preference = [
                {"width": 3840, "height": 2160, "file_type": "video/mp4"},  # 4K
                {"width": 1920, "height": 1080, "file_type": "video/mp4"},  # Full HD
                {"width": 1280, "height": 720, "file_type": "video/mp4"},   # HD
                {"width": 1920, "height": 1080},  # Fallback to any Full HD
                {"width": 1280, "height": 720}    # Fallback to any HD
            ]
            
            for quality in quality_preference:
                video_url = None
                for vf in video_files:
                    match = True
                    for k, v in quality.items():
                        if vf.get(k) != v:
                            match = False
                            break
                    if match:
                        video_url = vf["link"]
                        break
                
                if video_url:
                    # Download the video
                    cropped_path = "stock_video.mp4"
                    with open(cropped_path, "wb") as f:
                        video_data = requests.get(video_url, stream=True, timeout=20)
                        video_data.raise_for_status()
                        
                        total_size = int(video_data.headers.get('content-length', 0))
                        downloaded = 0
                        
                        for chunk in video_data.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                    
                    # Verify the downloaded file
                    if os.path.getsize(cropped_path) > 1024:  # At least 1KB
                        return cropped_path
                    else:
                        os.remove(cropped_path)
                        continue

        raise ValueError("No suitable high-quality video found")
    
    except Exception as e:
        print(f"Stock video error: {e}")
        return None
    
def create_subtitles(text, srt_path="subtitles.srt"):
    """Generate SRT subtitles file with better formatting"""
    try:
        if not text or not isinstance(text, str):
            raise ValueError("Invalid text input for subtitles")
            
        words = text.split()
        if len(words) < 1:
            raise ValueError("Text is too short for subtitles")
            
        chunk_size = 6  # Words per subtitle
        chunks = [' '.join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]
        
        with open(srt_path, "w", encoding='utf-8') as f:
            for i, chunk in enumerate(chunks):
                start_time = i * 4  # 2 seconds per chunk
                end_time = start_time + 2
                f.write(f"{i+1}\n")
                f.write(f"00:{start_time//60:02}:{start_time%60:02},000 --> 00:{end_time//60:02}:{end_time%60:02},000\n")
                f.write(f"{chunk}\n\n")
        
        return srt_path
        
    except Exception as e:
        print(f"Failed to create subtitles: {e}")
        # Create empty subtitles as fallback
        with open(srt_path, "w", encoding='utf-8') as f:
            f.write("1\n00:00:00,000 --> 00:00:02,000\nSubtitles unavailable\n\n")
        return srt_path

def _format_timestamp(ms):
    """Convert milliseconds to SRT timestamp format"""
    td = datetime.timedelta(milliseconds=ms)
    hours = td.seconds // 3600
    minutes = (td.seconds % 3600) // 60
    seconds = td.seconds % 60
    milliseconds = td.microseconds // 1000
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"

def render_final_video(cropped_clip, audio_path, srt_path, output_path="final_output.mp4"):
    """Combine all elements using FFmpeg"""
    try:
        # Get audio duration
        audio_clip = mpe.AudioFileClip(audio_path)
        audio_duration = audio_clip.duration
        audio_clip.close()
        
        # Loop video to match audio duration
        looped_video = "looped_temp.mp4"
        cmd_loop = [
            'ffmpeg',
            '-stream_loop', '-1',
            '-i', cropped_clip,
            '-t', str(audio_duration),
            '-c', 'copy',
            '-y', looped_video
        ]
        subprocess.run(cmd_loop, check=True)
        
        # Burn subtitles
        cmd_render = [
            'ffmpeg',
            '-i', looped_video,
            '-i', audio_path,
            '-vf', f"subtitles={srt_path}:force_style='{CONFIG['output']['subtitle_style']}'",
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-shortest',
            '-y', output_path
        ]
        subprocess.run(cmd_render, check=True)
        
        # Cleanup temporary files
        os.remove(looped_video)
        return output_path
    
    except Exception as e:
        print(f"Rendering failed: {e}")
        return None

def main():
    # Generate story
    story = generate_reddit_style_story()
    if not story:
        return
    print(f"Generated story: {story['title']}")
    
    # Convert to speech
    audio_path = text_to_speech(story["content"])
    if not audio_path:
        return
    
    # Generate subtitles
    srt_path = create_subtitles(story["content"])
    if not srt_path:
        return
    
    # Get stock video
    cropped_path = fetch_stock_video()
    cropped_path = VideoFileClip(cropped_path)
    crop_x = (cropped_path.w / 2 ) - 1080 / 2
    crop_y = (cropped_path.h / 2 ) - 1920 / 2

    cropped_path = cropped_path.cropped(x1=crop_x, y1=crop_y, width=1080,height=1920)
    cropped_clip = 'cropped_vid.mp4'
    cropped_path.write_videofile(cropped_clip)

    # Render final video
    output_path = render_final_video(cropped_clip, audio_path, srt_path)
    if output_path:
        print(f"Success! Video created at: {output_path}")

     

if __name__ == "__main__":
    main()