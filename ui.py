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
from calibre.gui2.threaded_jobs import ThreadedJob
from calibre_plugins.audiobook_generator.config import prefs

from qt.core import QImage, QPainter, QBuffer, QIODevice, Qt, QMenu

# Global reference to the plugin instance for the config dialog
_plugin_instance = None

def get_plugin_instance():
    return _plugin_instance

class InterfacePlugin(InterfaceAction):
    name = 'Audiobook Generator'
    
    action_spec = ('Audiobook Generator', None, 
                   'Generate audiobooks from ebooks using TTS', None)

    def genesis(self):
        global _plugin_instance
        _plugin_instance = self
        
        if hasattr(self, 'interface_action_base_plugin'):
            self.interface_action_base_plugin.actual_plugin_object = self
        
        icon = get_icons('images/icon.png')
        if icon:
            self.qaction.setIcon(icon)
        self.qaction.triggered.connect(self.show_dialog)
        
        # 1. Configure Action in toolbar menu
        self.config_action = self.create_action(
            spec=('Configure Plugin', 'config.png', 'Change plugin settings', None),
            attr='configure_plugin'
        )
        self.config_action.triggered.connect(self.do_config)
        
        self.menu = QMenu(self.gui)
        self.menu.addAction(self.config_action)
        self.qaction.setMenu(self.menu)

    def do_config(self):
        if hasattr(self, 'interface_action_base_plugin'):
            self.interface_action_base_plugin.do_user_config(self.gui)
        else:
            self.gui.iactions['Preferences'].do_config('plugins', self.name)

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
        if prefs['detect_language'] and mi.languages:
            l = mi.languages[0].lower()
            if l.startswith('en') or l == 'eng':
                language = 'English'
            elif l.startswith('es') or l == 'spa':
                language = 'Spanish (Latam)'

        engine = prefs['tts_engine']
        gender = prefs['voice_gender']
        output_format = prefs['output_format']

        epub_path = db.new_api.format_abspath(book_id, 'EPUB')
        est_message = ""
        
        if epub_path and os.path.exists(epub_path):
            try:
                from calibre.ebooks.oeb.polish.container import get_container
                from bs4 import BeautifulSoup
                container = get_container(epub_path)
                spine_names = [x[0] if isinstance(x, (list, tuple)) else x for x in container.spine_names]
                total_text_len = 0
                for name in spine_names:
                    mime = container.mime_map.get(name)
                    if mime in {'text/html', 'application/xhtml+xml'}:
                        raw = container.raw_data(name)
                        soup = BeautifulSoup(raw, 'html.parser')
                        for tag in soup(["script", "style", "img", "image", "svg", "video", "audio", "iframe"]):
                            tag.decompose()
                        text = soup.get_text(separator=' ', strip=True)
                        if text:
                            title_tag = soup.find(['h1', 'h2', 'h3'])
                            title_text = title_tag.get_text().strip() if title_tag else ""
                            total_text_len += len(f"{title_text}\n\n{text}\n\n")
                
                chunk_size = 5000
                num_chunks = (total_text_len // chunk_size) + (1 if total_text_len % chunk_size > 0 else 0)
                total_seconds = num_chunks * 7
                est_minutes = int(total_seconds / 60)
                est_message = f"Estimated time: ~{total_seconds if total_seconds < 60 else est_minutes} {'seconds' if total_seconds < 60 else 'minutes'} ({num_chunks} chunks)."
            except:
                est_message = "Estimation unavailable."

        msg = (f'\nDo you want to generate an {output_format} version of "{title}"?\n\n'
               f'Engine: {engine} ({language}, {gender})\n'
               f'{est_message}\n\n'
               'The process runs in the background. You can monitor progress in the "Jobs" spinner.'
               '\n' + '\n' * 6)

        if question_dialog(self.gui, 'Generate Audiobook', msg):
            self.start_background_job(book_id, title, language, engine, gender, output_format)

    def start_background_job(self, book_id, title, language, engine, gender, output_format):
        from calibre_plugins.audiobook_generator.worker import main as worker_main
        db = self.gui.current_db.new_api
        epub_path = db.format_abspath(book_id, 'EPUB')
        if not epub_path:
            return error_dialog(self.gui, 'No EPUB found', 'This book does not have an EPUB format.', show=True)

        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tf:
            temp_mp3 = tf.name

        voice = ('en-US-GuyNeural' if gender == 'Male' else 'en-US-AriaNeural') if 'English' in language else ('es-MX-JorgeNeural' if gender == 'Male' else 'es-MX-DaliaNeural') if engine == 'Edge TTS' else None
        lang_code = 'en' if 'English' in language else 'es'

        callback = Dispatcher(self.on_job_finished)
        job = ThreadedJob('audiobook_gen', f'Generating audiobook for "{title}"', worker_main, 
                          [epub_path, temp_mp3, voice, engine, lang_code, vendor_path, book_id, output_format], {}, 
                          callback)
        self.gui.job_manager.run_threaded_job(job)
        self.gui.status_bar.show_message(f'Audiobook Generator: Background job started for "{title}"', 3000)

    def on_job_finished(self, job):
        if job.failed:
            self.gui.status_bar.show_message('Audiobook Generator: Job failed!', 10000)
            return

        try:
            success, result_data = job.result
            book_id, output_format, result_val = result_data
        except: return

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
            
            self.apply_emblem_to_book(book_id)
            self.gui.status_bar.show_message('Audiobook Generator: SUCCESS - Finished and added to library.', 10000)
        except Exception as e:
            self.gui.status_bar.show_message(f"Audiobook Generator: Library Error - {str(e)}", 10000)

    def apply_emblem_to_book(self, book_id):
        db = self.gui.current_db.new_api
        cover_data = db.cover(book_id)
        if not cover_data: return

        try:
            rdata = self.load_resources(['images/cassette.png'])
            emblem_bytes = rdata.get('images/cassette.png')
            if not emblem_bytes: return
            emblem = QImage.fromData(emblem_bytes)
        except: return

        image = QImage.fromData(cover_data)
        if image.isNull(): return

        painter = QPainter(image)
        em_size = int(image.width() * 0.20)
        scaled_emblem = emblem.scaled(em_size, em_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        padding = int(image.width() * 0.02)
        x = image.width() - scaled_emblem.width() - padding
        y = padding
        painter.drawImage(x, y, scaled_emblem)
        painter.end()

        ba = QBuffer()
        ba.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(ba, "JPG")
        db.set_cover({book_id: ba.data().data()})
        
        self.gui.library_view.model().refresh_ids([book_id])
        if hasattr(self.gui, 'cover_view'):
            self.gui.cover_view.refresh_ids([book_id])

    def remove_emblem_from_book(self, book_id):
        """Attempts to restore original cover from ebook file if audio is missing."""
        db = self.gui.current_db.new_api
        formats = db.formats(book_id)
        if 'MP3' in formats or 'M4B' in formats:
            return

        from calibre.ebooks.metadata.meta import get_metadata
        for fmt in formats:
            path = db.format_abspath(book_id, fmt)
            if path and os.path.exists(path):
                try:
                    with open(path, 'rb') as f:
                        mi = get_metadata(f, stream_type=fmt.lower())
                    cover_data = None
                    if mi.cover_data and mi.cover_data[1]:
                        cover_data = mi.cover_data[1]
                    elif mi.cover and os.path.exists(mi.cover):
                        with open(mi.cover, 'rb') as cf:
                            cover_data = cf.read()
                    if cover_data:
                        db.set_cover({book_id: cover_data})
                        self.gui.library_view.model().refresh_ids([book_id])
                        return
                except: continue

    def sync_all_icons(self):
        """Runs library sync in a background thread to prevent UI freeze."""
        # Using a ThreadedJob for the sync as well
        def sync_worker(db, book_ids, notifications, abort, log):
            add_count = 0
            rem_count = 0
            total = len(book_ids)
            for i, bid in enumerate(book_ids):
                if abort.is_set(): break
                formats = db.formats(bid)
                if 'MP3' in formats or 'M4B' in formats:
                    # We can't do QImage composition in a non-GUI thread reliably.
                    # But we can return the IDs to the GUI thread.
                    add_count += 1
                else:
                    rem_count += 1
                if i % 10 == 0:
                    notifications.put((i/total, f"Scanning book {i} of {total}..."))
            return add_count, rem_count, book_ids

        db = self.gui.current_db.new_api
        ids = list(db.all_book_ids())
        
        # We'll do the actual drawing back in the GUI thread via the callback
        job = ThreadedJob('audiobook_sync', 'Syncing Audiobook Icons', sync_worker, 
                          [db, ids], {}, Dispatcher(self.on_sync_finished))
        self.gui.job_manager.run_threaded_job(job)
        self.gui.status_bar.show_message('Audiobook Generator: Started library-wide sync...', 3000)

    def on_sync_finished(self, job):
        if job.failed:
            self.gui.status_bar.show_message('Audiobook Generator: Sync failed!', 5000)
            return
        
        add_count, rem_count, ids = job.result
        db = self.gui.current_db.new_api
        
        # Drawing must happen in GUI thread
        for bid in ids:
            formats = db.formats(bid)
            if 'MP3' in formats or 'M4B' in formats:
                self.apply_emblem_to_book(bid)
            else:
                self.remove_emblem_from_book(bid)
                
        self.gui.status_bar.show_message(f'Audiobook Generator: Sync complete ({add_count} icons, {rem_count} cleared).', 10000)

    def apply_settings(self):
        pass
