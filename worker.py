import sys
import os
import asyncio
import traceback
import time
import re
import unicodedata

def main(epub_path, output_path, voice, engine, lang_code, vendor_path, book_id, output_format, notifications, abort, log):
    """
    Worker function for concurrent audiobook generation using asyncio.
    """
    if vendor_path not in sys.path:
        sys.path.insert(0, vendor_path)

    try:
        log(f"Starting conversion for book ID: {book_id}")
        
        # 1. Extract text
        notifications.put((0.05, "Extracting text..."))
        text = extract_content_robust(epub_path, log)
        if not text:
            return False, (book_id, output_format, "Could not extract text.")

        text = clean_text_for_tts(text)
        log(f"Cleaned text length: {len(text)} characters")
        
        # 2. Prepare chunks (5000 chars per chunk)
        chunk_size = 5000
        text_chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        total_chunks = len(text_chunks)
        log(f"Total chunks: {total_chunks}")

        # 3. Concurrent generation using asyncio
        async def run_concurrent_tts():
            # Limit concurrency to avoid getting blocked (e.g., 3 concurrent requests)
            semaphore = asyncio.Semaphore(3)
            
            if os.path.exists(output_path):
                os.remove(output_path)

            # We will store raw audio data in a list to keep them in order
            audio_segments = [None] * total_chunks
            completed = [0] # Use a list for mutable closure

            async def fetch_chunk(index, chunk_text):
                async with semaphore:
                    if abort.is_set(): return
                    
                    try:
                        data = b""
                        if engine == 'Edge TTS':
                            import edge_tts
                            communicate = edge_tts.Communicate(chunk_text, voice)
                            async for message in communicate.stream():
                                if message["type"] == "audio":
                                    data += message["data"]
                        else:
                            # gTTS - Not natively async, run in executor
                            from gtts import gTTS
                            def run_gtts():
                                import tempfile
                                tts = gTTS(text=chunk_text, lang=lang_code)
                                with tempfile.NamedTemporaryFile(suffix='.mp3', delete=True) as tf:
                                    tts.save(tf.name)
                                    with open(tf.name, "rb") as rf:
                                        return rf.read()
                            
                            data = await asyncio.get_event_loop().run_in_executor(None, run_gtts)
                            await asyncio.sleep(0.5) # Rate limit safety

                        audio_segments[index] = data
                        completed[0] += 1
                        notifications.put((0.1 + (completed[0] / total_chunks * 0.8), 
                                         f"Downloaded {completed[0]} of {total_chunks} segments..."))
                    except Exception as e:
                        log(f"Error in chunk {index}: {str(e)}")

            # Create tasks
            tasks = [fetch_chunk(i, chunk) for i, chunk in enumerate(text_chunks)]
            await asyncio.gather(*tasks)
            
            # Unify in order
            log("Assembling audio file...")
            with open(output_path, "wb") as f:
                for segment in audio_segments:
                    if segment:
                        f.write(segment)

        # Run the async loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_concurrent_tts())
        finally:
            loop.close()

        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            strip_audio_tags(output_path, vendor_path)
            log("SUCCESS: Generation finished.")
            return True, (book_id, output_format, output_path)
        else:
            return False, (book_id, output_format, "Audio generation failed or was aborted.")

    except Exception as e:
        log(f"CRITICAL ERROR: {traceback.format_exc()}")
        return False, (book_id, output_format, str(e))

def clean_text_for_tts(text):
    text = unicodedata.normalize('NFKC', text)
    replacements = {'\xad': '', '\u200b': '', '\ufeff': '', '“': '"', '”': '"', '‘': "'", '’': "'", '…': '...', '—': '-'}
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = "".join(c for c in text if unicodedata.category(c)[0] != 'C' or c in '\n\t')
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    return text.strip()

def strip_audio_tags(file_path, vendor_path):
    if vendor_path not in sys.path:
        sys.path.insert(0, vendor_path)
    try:
        from mutagen.mp3 import MP3
        audio = MP3(file_path)
        audio.delete()
        audio.save()
    except: pass

def extract_content_robust(epub_path, log):
    from calibre.ebooks.oeb.polish.container import get_container
    from bs4 import BeautifulSoup
    try:
        container = get_container(epub_path)
        all_text = []
        from calibre.ebooks.oeb.polish.cover import find_cover_page
        cover_page = None
        try: cover_page = find_cover_page(container)
        except: pass
        
        spine_names = [x[0] if isinstance(x, (list, tuple)) else x for x in container.spine_names]
        for name in spine_names:
            if cover_page and name == cover_page: continue
            mime = container.mime_map.get(name)
            if mime in {'text/html', 'application/xhtml+xml'}:
                try:
                    raw = container.raw_data(name)
                    soup = BeautifulSoup(raw, 'html.parser')
                    for tag in soup(["script", "style", "img", "image", "svg", "video", "audio", "iframe", "meta", "link"]):
                        tag.decompose()
                    title_tag = soup.find(['h1', 'h2', 'h3'])
                    title_text = title_tag.get_text().strip() if title_tag else ""
                    if title_tag: title_tag.decompose()
                    text = soup.get_text(separator=' ', strip=True)
                    if text or title_text:
                        if title_text: all_text.append(f"{title_text}. {text}. ")
                        else: all_text.append(f"{text}. ")
                except: continue
        return "".join(all_text)
    except: return None
