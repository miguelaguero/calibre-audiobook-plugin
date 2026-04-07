import sys
import os
import asyncio

# Add vendor directory to sys.path
plugin_path = os.path.dirname(__file__)
vendor_path = os.path.join(plugin_path, 'vendor')
if vendor_path not in sys.path:
    sys.path.insert(0, vendor_path)

from calibre.gui2.actions import InterfaceAction
from calibre.gui2 import error_dialog, question_dialog, info_dialog
from calibre_plugins.audiobook_generator.config import prefs

class InterfacePlugin(InterfaceAction):
    name = 'Audiobook Generator'
    
    # Set icon to None here to set it programmatically in genesis()
    action_spec = ('Audiobook Generator', None, 
                   'Generate audiobooks from ebooks using TTS', None)

    def genesis(self):
        # Programmatically load and set the icon
        # get_icons() is a builtin that looks into the plugin ZIP
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
                                'Please select only one book at a time for audiobook generation.', show=True)

        db = self.gui.current_db
        book_id = ids[0]
        mi = db.get_metadata(book_id, index_is_id=True)
        title = mi.title
        
        language = prefs['language']
        engine = prefs['tts_engine']
        gender = prefs['voice_gender']

        if question_dialog(self.gui, 'Generate Audiobook', 
                           f'Do you want to generate an MP3 file version of "{title}" using {engine} ({language}, {gender})?'):
            self.generate_audiobook(book_id, title, language, engine, gender)

    def generate_audiobook(self, book_id, title, language, engine, gender):
        from calibre.gui2.dialogs.progress import ProgressDialog
        
        db = self.gui.current_db.new_api
        epub_path = db.format_abspath(book_id, 'EPUB')
        
        if not epub_path:
            return error_dialog(self.gui, 'No EPUB found', 
                                'This book does not have an EPUB format available.', show=True)

        # Show progress dialog
        pd = ProgressDialog('Generating Audiobook...', 
                            f'Processing "{title}"', 
                            min=0, max=100, parent=self.gui, cancelable=False)
        pd.show()
        
        # Update status bar
        self.gui.status_bar.show_message(f'Audiobook Generator: Extracting text from "{title}"...', 3000)
        
        try:
            # 1. Extract text from EPUB
            pd.value = 10
            text = self.extract_text(epub_path)
            if not text:
                pd.hide()
                self.gui.status_bar.show_message('Audiobook Generator: Extraction failed.', 5000)
                return error_dialog(self.gui, 'Extraction Failed', 'Could not extract text from the EPUB.', show=True)
            
            # Limit to 5000 chars for now to avoid issues
            text_to_process = text[:5000]
            
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tf:
                temp_mp3 = tf.name

            pd.value = 30
            self.gui.status_bar.show_message(f'Audiobook Generator: Generating audio with {engine} ({gender})...', 5000)

            if engine == 'Edge TTS':
                # Map gender and language to specific voices
                if 'English' in language:
                    voice = 'en-US-GuyNeural' if gender == 'Male' else 'en-US-AriaNeural'
                else:
                    voice = 'es-MX-JorgeNeural' if gender == 'Male' else 'es-MX-DaliaNeural'
                
                asyncio.run(self.run_edge_tts(text_to_process, voice, temp_mp3))
            else:
                # Use gTTS
                lang_code = 'en' if 'English' in language else 'es'
                from gtts import gTTS
                tts = gTTS(text=text_to_process, lang=lang_code)
                tts.save(temp_mp3)
            
            pd.value = 80
            self.gui.status_bar.show_message('Audiobook Generator: Saving MP3 to library...', 3000)

            # 4. Add the MP3 to the Calibre book
            with open(temp_mp3, 'rb') as f:
                db.add_format(book_id, 'MP3', f, replace=True)
            
            if os.path.exists(temp_mp3):
                os.remove(temp_mp3)
                
            pd.value = 100
            pd.hide()
            self.gui.status_bar.show_message(f'Audiobook Generator: Finished "{title}"', 5000)
            info_dialog(self.gui, 'Success', f'Audiobook (MP3) generated using {engine} ({gender}) and added to "{title}"', show=True)
            
        except Exception as e:
            pd.hide()
            self.gui.status_bar.show_message('Audiobook Generator: Error occurred.', 5000)
            import traceback
            print(traceback.format_exc())
            return error_dialog(self.gui, 'Error', f'An error occurred: {str(e)}', show=True)

    async def run_edge_tts(self, text, voice, output_path):
        import edge_tts
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)

    def extract_text(self, epub_path):
        from calibre.ebooks.oeb.polish.container import get_container
        from bs4 import BeautifulSoup
        
        container = get_container(epub_path)
        all_text = []
        for name in container.name_path_map:
            mime = container.mime_map.get(name)
            if mime in {'text/html', 'application/xhtml+xml'}:
                raw = container.raw_data(name)
                soup = BeautifulSoup(raw, 'html.parser')
                for script in soup(["script", "style"]):
                    script.decompose()
                all_text.append(soup.get_text())
        return "\n".join(all_text)

    def apply_settings(self):
        pass
