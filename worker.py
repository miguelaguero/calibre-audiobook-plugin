import sys
import os
import asyncio
import traceback
import time

def main(epub_path, output_path, voice, engine, lang_code, vendor_path, book_id, output_format, notifications, abort, log):
    """
    Worker function.
    """
    if vendor_path not in sys.path:
        sys.path.insert(0, vendor_path)

    try:
        log(f"Starting conversion for book ID: {book_id}")
        
        # 1. Extract text
        notifications.put((0.05, "Extracting clean text..."))
        text = extract_content_robust(epub_path, log)
        if not text:
            log("ERROR: No text could be extracted.")
            return False, (book_id, output_format, "Could not extract text from EPUB.")

        log(f"Total characters extracted: {len(text)}")
        
        # 2. Generate Audio
        chunk_size = 5000
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        total_chunks = len(chunks)
        
        if total_chunks == 0:
            return False, (book_id, output_format, "Extracted text is empty.")

        log(f"Calculated {total_chunks} chunks.")

        if engine == 'Edge TTS':
            log("Generating audio with Edge TTS...")
            if os.path.exists(output_path):
                os.remove(output_path)
                
            import edge_tts
            
            async def process_all_chunks():
                for i, chunk in enumerate(chunks):
                    if abort.is_set():
                        log("ABORTED by user.")
                        return False
                    
                    msg = f"Generating audio chunk {i+1} of {total_chunks}..."
                    log(msg)
                    notifications.put((0.1 + ((i + 1) / total_chunks * 0.8), msg))

                    communicate = edge_tts.Communicate(chunk, voice)
                    with open(output_path, "ab") as f:
                        async for message in communicate.stream():
                            if message["type"] == "audio":
                                f.write(message["data"])
                return True

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                success = loop.run_until_complete(process_all_chunks())
                if not success:
                    return False, (book_id, output_format, "Aborted")
            finally:
                loop.close()
                
        else:
            log("Generating audio with gTTS...")
            if os.path.exists(output_path):
                os.remove(output_path)
                
            from gtts import gTTS
            for i, chunk in enumerate(chunks):
                if abort.is_set():
                    return False, (book_id, output_format, "Aborted")
                
                msg = f"Generating gTTS chunk {i+1} of {total_chunks}..."
                log(msg)
                notifications.put((0.1 + ((i + 1) / total_chunks * 0.8), msg))
                
                tts = gTTS(text=chunk, lang=lang_code)
                
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tf:
                    chunk_mp3 = tf.name
                
                tts.save(chunk_mp3)
                
                with open(output_path, "ab") as main_f:
                    with open(chunk_mp3, "rb") as chunk_f:
                        main_f.write(chunk_f.read())
                
                os.remove(chunk_mp3)
                if i < total_chunks - 1:
                    time.sleep(0.1)

        log(f"SUCCESS: Conversion finished. Total chunks: {total_chunks}")
        return True, (book_id, output_format, output_path)

    except Exception as e:
        err = traceback.format_exc()
        log(f"Error: {err}")
        return False, (book_id, output_format, str(e))

def extract_content_robust(epub_path, log):
    """Robustly extracts clean text from the EPUB container, SKIPPING THE COVER."""
    from calibre.ebooks.oeb.polish.container import get_container
    from calibre.ebooks.oeb.polish.cover import find_cover_page
    from bs4 import BeautifulSoup
    
    try:
        container = get_container(epub_path)
        all_text = []
        
        # Identify the cover page safely
        cover_page = None
        try:
            cover_page = find_cover_page(container)
        except:
            pass
        
        # spine_names is a generator of (name, linear) tuples
        spine_names = [x[0] if isinstance(x, (list, tuple)) else x for x in container.spine_names]
        
        for name in spine_names:
            # SKIP THE COVER PAGE
            if cover_page and name == cover_page:
                continue
                
            mime = container.mime_map.get(name)
            if mime in {'text/html', 'application/xhtml+xml'}:
                try:
                    raw = container.raw_data(name)
                    soup = BeautifulSoup(raw, 'html.parser')
                    
                    for tag in soup(["script", "style", "img", "image", "svg", "video", "audio", "iframe"]):
                        tag.decompose()
                    
                    text = soup.get_text(separator=' ', strip=True)
                    
                    if text:
                        # Skip introductory "Cover" text
                        if text.lower().strip() == "cover" and len(text) < 10:
                            continue

                        title_tag = soup.find(['h1', 'h2', 'h3'])
                        title_text = title_tag.get_text().strip() if title_tag else ""
                        
                        if title_text:
                            all_text.append(f"{title_text}\n\n{text}\n\n")
                        else:
                            all_text.append(f"{text}\n\n")
                except:
                    continue
                        
        return "".join(all_text)
    except Exception as e:
        log(f"Extraction error: {str(e)}")
        return None
