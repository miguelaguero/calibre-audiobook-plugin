from qt.core import QWidget, QHBoxLayout, QLabel, QComboBox, QVBoxLayout, QPushButton, QCheckBox
from calibre.utils.config import JSONConfig

# Initialize the config object. 
prefs = JSONConfig('plugins/audiobook_generator')

# Set default values
prefs.defaults['language'] = 'English'
prefs.defaults['tts_engine'] = 'Edge TTS'
prefs.defaults['voice_gender'] = 'Male'
prefs.defaults['output_format'] = 'MP3'
prefs.defaults['detect_language'] = False

class ConfigWidget(QWidget):
    def __init__(self, plugin_action=None):
        QWidget.__init__(self)
        self.plugin_action = plugin_action
        self.l = QVBoxLayout()
        self.setLayout(self.l)

        # 1. Output Format Selection
        self.h0 = QHBoxLayout()
        self.l.addLayout(self.h0)
        self.format_label = QLabel('Output Format:')
        self.h0.addWidget(self.format_label)
        self.format_combo = QComboBox(self)
        self.format_combo.addItems(['MP3', 'M4B'])
        index = self.format_combo.findText(prefs['output_format'])
        if index >= 0:
            self.format_combo.setCurrentIndex(index)
        self.h0.addWidget(self.format_combo)

        # 2. TTS Engine Selection
        self.h1 = QHBoxLayout()
        self.l.addLayout(self.h1)
        self.engine_label = QLabel('TTS Engine:')
        self.h1.addWidget(self.engine_label)
        self.engine_combo = QComboBox(self)
        self.engine_combo.addItems(['Edge TTS', 'gTTS'])
        index = self.engine_combo.findText(prefs['tts_engine'])
        if index >= 0:
            self.engine_combo.setCurrentIndex(index)
        self.h1.addWidget(self.engine_combo)

        # 3. Voice Gender Selection
        self.h2 = QHBoxLayout()
        self.l.addLayout(self.h2)
        self.gender_label = QLabel('Voice Gender (Edge TTS only):')
        self.h2.addWidget(self.gender_label)
        self.gender_combo = QComboBox(self)
        self.gender_combo.addItems(['Male', 'Female'])
        index = self.gender_combo.findText(prefs['voice_gender'])
        if index >= 0:
            self.gender_combo.setCurrentIndex(index)
        self.h2.addWidget(self.gender_combo)

        # 4. Target Language Selection
        self.h3 = QHBoxLayout()
        self.l.addLayout(self.h3)
        self.label = QLabel('Target Language:')
        self.h3.addWidget(self.label)
        self.language_combo = QComboBox(self)
        self.language_combo.addItems(['English', 'Spanish (Latam)'])
        index = self.language_combo.findText(prefs['language'])
        if index >= 0:
            self.language_combo.setCurrentIndex(index)
        self.h3.addWidget(self.language_combo)

        # 4b. Detect Language from Book
        self.h4 = QHBoxLayout()
        self.l.addLayout(self.h4)
        self.detect_language_checkbox = QCheckBox('Detect language from book metadata', self)
        self.detect_language_checkbox.setChecked(prefs['detect_language'])
        self.detect_language_checkbox.setToolTip('If checked, the plugin will try to use the language defined in the book metadata.')
        self.h4.addWidget(self.detect_language_checkbox)
        
        self.l.addSpacing(20)
        
        # 5. Sync Button
        self.sync_button = QPushButton('Sync All Audiobook Icons', self)
        self.sync_button.setToolTip('Scan entire library for audiobooks and add cassette icons to covers')
        self.sync_button.clicked.connect(self.run_sync)
        self.l.addWidget(self.sync_button)
        
        self.l.addStretch(1)

    def run_sync(self):
        if self.plugin_action:
            self.plugin_action.sync_all_icons()

    def save_settings(self):
        prefs['language'] = self.language_combo.currentText()
        prefs['tts_engine'] = self.engine_combo.currentText()
        prefs['voice_gender'] = self.gender_combo.currentText()
        prefs['output_format'] = self.format_combo.currentText()
        prefs['detect_language'] = self.detect_language_checkbox.isChecked()
