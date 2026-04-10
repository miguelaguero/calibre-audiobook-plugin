from calibre.customize import InterfaceActionBase

class AudiobookGeneratorPlugin(InterfaceActionBase):
    name                = 'Audiobook Generator'
    description         = 'Generate audiobooks from ebooks using TTS'
    supported_platforms = ['windows', 'osx', 'linux']
    author              = 'Miguel Aguero'
    version             = (0, 1, 9)
    minimum_calibre_version = (5, 0, 0)
    icon = 'images/icon.png'

    actual_plugin = 'calibre_plugins.audiobook_generator.ui:InterfacePlugin'

    def is_customizable(self):
        return True

    def config_widget(self):
        from calibre_plugins.audiobook_generator.ui import get_plugin_instance
        from calibre_plugins.audiobook_generator.config import ConfigWidget
        return ConfigWidget(plugin_action=get_plugin_instance())

    def save_settings(self, config_widget):
        config_widget.save_settings()
