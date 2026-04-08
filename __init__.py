from calibre.customize import InterfaceActionBase

class AudiobookGeneratorPlugin(InterfaceActionBase):
    name                = 'Audiobook Generator'
    description         = 'Generate audiobooks from ebooks using TTS'
    supported_platforms = ['windows', 'osx', 'linux']
    author              = 'Miguel Aguero'
    version             = (0, 1, 3)
    minimum_calibre_version = (5, 0, 0)
    icon = 'images/icon.png'

    # This points to the actual class in ui.py
    # Format: 'calibre_plugins.import_name.module:ClassName'
    actual_plugin = 'calibre_plugins.audiobook_generator.ui:InterfacePlugin'

    def is_customizable(self):
        return True

    def config_widget(self):
        """
        Returns the QWidget that will be displayed in the 
        Preferences -> Plugins -> Customize dialog.
        """
        from calibre_plugins.audiobook_generator.config import ConfigWidget
        return ConfigWidget()

    def save_settings(self, config_widget):
        """
        Called when the user clicks 'OK' in the configuration dialog.
        """
        config_widget.save_settings()
