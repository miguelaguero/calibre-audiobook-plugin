from qt.core import QDialog, QVBoxLayout, QLabel, QPushButton

class MainDialog(QDialog):
    def __init__(self, gui, icon):
        QDialog.__init__(self, gui)
        self.gui = gui
        
        # Set up the window
        self.setWindowTitle('Audiobook Generator')
        if icon:
            self.setWindowIcon(icon)
        
        # Set up the layout
        self.l = QVBoxLayout()
        self.setLayout(self.l)
        
        # Add a placeholder label
        self.label = QLabel('Welcome to the Audiobook Generator!')
        self.l.addWidget(self.label)
        
        # Add a close button
        self.close_button = QPushButton('Close', self)
        self.close_button.clicked.connect(self.accept)
        self.l.addWidget(self.close_button)
        
        # Set a reasonable default size
        self.resize(300, 200)
