import sys
import os
import time

# Add vendor directory to sys.path
plugin_path = os.path.dirname(__file__)
vendor_path = os.path.join(plugin_path, 'vendor')
if vendor_path not in sys.path:
    sys.path.insert(0, vendor_path)

from calibre.gui2.actions import InterfaceAction
from calibre.gui2 import error_dialog, question_dialog, info_dialog, Dispatcher
from calibre_plugins.audiobook_generator.config import prefs

class InterfacePlugin(InterfaceAction):
    name = 'Audiobook Generator'
    
    action_spec = ('Audiobook Generator', None, 
                   'Generate audiobooks from ebooks using TTS', None)

    def genesis(self):
        icon = get_icons('images/icon.png')
        if icon:
            self.qaction.setIcon(icon)
        self.qaction.triggered.connect(self.show_dialog)

    def show_dialog(self):
        ids = self.gui.library_view.get_selected_ids()
        if not ids:
            return error_dialog(self.gui, 'No book selected', 
                                'Please select a book first.', show=True)
        
        if len(ids) > 1:
            return error_dialog(self.gui, 'Multiple books selected', 
                                'Please select only one book at a time.', show=True)

        db = self.gui.current_db
        book_id = ids[0]
        mi = db.get_metadata(book_id, index_is_id=True)
        title = mi.title
        
        language = prefs['language']
        engine = prefs['tts_engine']
        gender = prefs['voice_gender']
        output_format = prefs['output_format']

        # Accurate Time Estimation
        epub_path = db.new_api.format_abspath(book_id, 'EPUB')
        est_message = ""
        
        if epub_path and os.path.exists(epub_path):
            self.gui.status_bar.show_message("Analyzing book content for estimation...", 2000)
            try:
                from calibre.ebooks.oeb.polish.container import get_container
                from calibre.ebooks.oeb.polish.cover import find_cover_page
                from bs4 import BeautifulSoup
                
                container = get_container(epub_path)
                cover_page = None
                try:
                    cover_page = find_cover_page(container)
                except:
                    pass
                
                # Correctly handle spine_names (generator of tuples)
                spine_names = [x[0] if isinstance(x, (list, tuple)) else x for x in container.spine_names]
                
                full_text_buf = []
                for name in spine_names:
                    if cover_page and name == cover_page:
                        continue
                        
                    mime = container.mime_map.get(name)
                    if mime in {'text/html', 'application/xhtml+xml'}:
                        raw = container.raw_data(name)
                        soup = BeautifulSoup(raw, 'html.parser')
                        for tag in soup(["script", "style", "img", "image", "svg", "video", "audio", "iframe"]):
                            tag.decompose()
                        
                        text = soup.get_text(separator=' ', strip=True)
                        if text:
                            # Match worker logic for introductory "Cover" text
                            if text.lower().strip() == "cover" and len(text) < 10:
                                continue

                            title_tag = soup.find(['h1', 'h2', 'h3'])
                            title_text = title_tag.get_text().strip() if title_tag else ""
                            
                            if title_text:
                                full_text_buf.append(f"{title_text}\n\n{text}\n\n")
                            else:
                                full_text_buf.append(f"{text}\n\n")
                
                total_text = "".join(full_text_buf)
                chunk_size = 5000
                chunks = [total_text[i:i+chunk_size] for i in range(0, len(total_text), chunk_size)]
                num_chunks = len(chunks)
                
                total_seconds = num_chunks * 7
                est_minutes = int(total_seconds / 60)
                
                if total_seconds < 60:
                    est_message = f"Estimated time: ~{total_seconds} seconds ({num_chunks} chunks)."
                else:
                    est_message = f"Estimated time: ~{est_minutes} minutes ({num_chunks} chunks)."
            except Exception as e:
                print(f"Estimation error: {str(e)}")
                est_message = "Estimation currently unavailable."

        msg = (f'\nDo you want to generate an {output_format} version of "{title}"?\n\n'
               f'Engine: {engine} ({language}, {gender})\n'
               f'{est_message}\n\n'
               'The process runs in the background. You can monitor progress in the "Jobs" spinner.'
               '\n' + '\n' * 6)

        if question_dialog(self.gui, 'Generate Audiobook', msg):
            self.start_background_job(book_id, title, language, engine, gender, output_format)

    def start_background_job(self, book_id, title, language, engine, gender, output_format):
        from calibre.gui2.threaded_jobs import ThreadedJob
        from calibre_plugins.audiobook_generator.worker import main as worker_main
        
        db = self.gui.current_db.new_api
        epub_path = db.format_abspath(book_id, 'EPUB')
        
        if not epub_path:
            return error_dialog(self.gui, 'No EPUB found', 
                                'This book does not have an EPUB format available.', show=True)

        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tf:
            temp_mp3 = tf.name

        if engine == 'Edge TTS':
            voice = ('en-US-GuyNeural' if gender == 'Male' else 'en-US-AriaNeural') if 'English' in language else ('es-MX-JorgeNeural' if gender == 'Male' else 'es-MX-DaliaNeural')
        else:
            voice = None

        lang_code = 'en' if 'English' in language else 'es'

        args = [epub_path, temp_mp3, voice, engine, lang_code, vendor_path, book_id, output_format]
        
        job = ThreadedJob(
            'audiobook_gen',
            f'Generating audiobook for "{title}"',
            worker_main,
            args,
            {}, 
            Dispatcher(self.on_job_finished)
        )

        self.gui.job_manager.run_threaded_job(job)
        self.gui.status_bar.show_message(f'Audiobook Generator: Background job started for "{title}"', 3000)

    def on_job_finished(self, job):
        if job.failed:
            msg = f'Audiobook Generator: Job failed! Check job details.'
            self.gui.status_bar.show_message(msg, 10000)
            return

        try:
            success, result_data = job.result
            book_id, output_format, result_val = result_data
        except:
            return

        if not success:
            self.gui.status_bar.show_message(f"Audiobook Generator: FAILED - {result_val}", 10000)
            return

        temp_mp3 = result_val
        
        try:
            db = self.gui.current_db.new_api
            with open(temp_mp3, 'rb') as f:
                db.add_format(book_id, output_format, f, replace=True)
            
            if os.path.exists(temp_mp3):
                os.remove(temp_mp3)
                
            self.gui.status_bar.show_message('Audiobook Generator: SUCCESS - Finished and added to library.', 10000)
            
        except Exception as e:
            self.gui.status_bar.show_message(f"Audiobook Generator: Library Error - {str(e)}", 10000)

    def apply_settings(self):
        pass
