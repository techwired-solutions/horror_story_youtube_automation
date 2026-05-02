import asyncio
import edge_tts

async def main():
    voice = "en-US-ChristopherNeural"
    communicate = edge_tts.Communicate("The Ozark Mountains...", voice)
    
    async for chunk in communicate.stream():
        if chunk["type"] != "audio":
            print(chunk)

asyncio.run(main())
