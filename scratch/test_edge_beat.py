import asyncio
import edge_tts
import io
from pydub import AudioSegment

async def main():
    voice = "en-US-ChristopherNeural"
    beats = [
        {"text": "The Ozark Mountains...", "pause_after": 1.5},
        {"text": "They hold secrets.", "pause_after": 1.0},
        {"text": "Very old secrets.", "pause_after": 2.0}
    ]
    
    master_audio = AudioSegment.empty()
    master_words = []
    
    for beat in beats:
        text = beat["text"]
        communicate = edge_tts.Communicate(text, voice, rate="-10%", pitch="-15Hz")
        
        audio_data = b""
        word_boundaries = []
        
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
            elif chunk["type"] == "WordBoundary":
                word_boundaries.append({
                    "text": chunk["text"],
                    "offset": chunk["offset"],
                    "duration": chunk["duration"]
                })
        
        if not audio_data:
            continue
            
        # load audio snippet
        audio_segment = AudioSegment.from_file(io.BytesIO(audio_data), format="mp3")
        current_duration = len(master_audio) / 1000.0
        
        for wb in word_boundaries:
            start = (wb["offset"] / 10000000.0) + current_duration
            end = start + (wb["duration"] / 10000000.0)
            master_words.append({
                "text": wb["text"],
                "start": start,
                "end": end
            })
            
        master_audio += audio_segment
        
        # add silence
        pause_ms = int(beat.get("pause_after", 0.5) * 1000)
        master_audio += AudioSegment.silent(duration=pause_ms)
        
    master_audio.export("scratch/edge_test.mp3", format="mp3")
    print(master_words)

asyncio.run(main())
