from qt.core import QWidget, QHBoxLayout, QLabel, QComboBox, QVBoxLayout
from calibre.utils.config import JSONConfig

# Initialize the config object. 
prefs = JSONConfig('plugins/audiobook_generator')

# Set default values
prefs.defaults['language'] = 'English'
prefs.defaults['tts_engine'] = 'Edge TTS'
prefs.defaults['voice_gender'] = 'Male'

class ConfigWidget(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        self.l = QVBoxLayout()
        self.setLayout(self.l)

        # 1. TTS Engine Selection (Top)
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

        # 2. Voice Gender Selection
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

        # 3. Language Selection
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
        
        # Add stretch to push everything to the top
        self.l.addStretch(1)

    def save_settings(self):
        prefs['language'] = self.language_combo.currentText()
        prefs['tts_engine'] = self.engine_combo.currentText()
        prefs['voice_gender'] = self.gender_combo.currentText()
