import sys
import os
import configparser
from PyQt5 import QtWidgets, QtCore, QtGui, QtMultimedia, QtMultimediaWidgets
from Xlib import display
from Xlib import Xatom
import subprocess
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gio, Gtk

class Settings():
    def __init__(self):
        self.DesktopTextColor = "black"
        self.VideoPath = '/home/nick/Downloads/NAKEDTEST.mp4'

userSettings = Settings()

class VideoWallpaper(QtWidgets.QMainWindow):
    def __init__(self, video_path, screen):
        super().__init__()

        self.screen = screen

        # Verify that the video file exists
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # Remove window decorations and set window flags
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |            # Remove window borders
            QtCore.Qt.WindowStaysOnBottomHint |        # Attempt to keep the window at the bottom
            QtCore.Qt.Tool                             # Make it a tool window to influence stacking
        )

        # Get the available geometry (excluding panels and docks)
        available_geo = self.screen.availableGeometry()
        self.setGeometry(available_geo)
        print(f"Wallpaper window geometry set to: {available_geo}")

        # Make the window transparent to mouse events
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

        # Create a video widget to display the video
        self.video_widget = QtMultimediaWidgets.QVideoWidget(self)
        self.video_widget.setGeometry(self.rect())
        self.setCentralWidget(self.video_widget)

        # Initialize the media player
        self.media_player = QtMultimedia.QMediaPlayer(self, QtMultimedia.QMediaPlayer.VideoSurface)
        self.media_player.setVideoOutput(self.video_widget)

        # Set the media content to the provided video path
        self.media_player.setMedia(QtMultimedia.QMediaContent(QtCore.QUrl.fromLocalFile(video_path)))

        # Optional: Mute the video if you don't want sound
        self.media_player.setVolume(0)

        # Start playing the video

        self.set_window_type_desktop()

        self.media_player.play()
        self.media_player.setPosition(0)
        print("Video playback started.")

        # Connect the media status change to handle looping
        self.media_player.mediaStatusChanged.connect(self.handle_media_status)

        # Scheduled setting of the window breaks stuff with resizing and adds black bars to the desktop
        #QtCore.QTimer.singleShot(1000, self.set_window_type_desktop)

    def handle_media_status(self, status):
        if status == QtMultimedia.QMediaPlayer.EndOfMedia:
            self.media_player.setPosition(0)
            self.media_player.play()

    def closeEvent(self, event):
        # Ensure the media player is stopped when the window is closed
        self.media_player.stop()
        event.accept()

    def set_window_type_desktop(self):
        """
        Sets the window type to _NET_WM_WINDOW_TYPE_DESKTOP and window state to _NET_WM_STATE_BELOW.
        This ensures the window behaves as a desktop background and stays below other windows.
        """
        try:
            # Get the window ID
            window_id = int(self.winId())

            # Open the display
            d = display.Display()

            # Get the window object
            w = d.create_resource_object('window', window_id)

            # Define the atoms for window type and state
            NET_WM_WINDOW_TYPE = d.get_atom('_NET_WM_WINDOW_TYPE')
            NET_WM_WINDOW_TYPE_DESKTOP = d.get_atom('_NET_WM_WINDOW_TYPE_DESKTOP')

            NET_WM_STATE = d.get_atom('_NET_WM_STATE')
            NET_WM_STATE_BELOW = d.get_atom('_NET_WM_STATE_BELOW')

            # Set the window type to DESKTOP
            w.change_property(NET_WM_WINDOW_TYPE, Xatom.ATOM, 32, [NET_WM_WINDOW_TYPE_DESKTOP])

            # Add the BELOW state to ensure the window stays behind other windows
            w.change_property(NET_WM_STATE, Xatom.ATOM, 32, [NET_WM_STATE_BELOW])

            # Flush the display to apply changes
            d.sync()

            print(f"Successfully set window type to DESKTOP and state to BELOW for window ID {window_id}.")
        except Exception as e:
            print(f"Error setting window type: {e}")

    def keyPressEvent(self, event):
        """
        Override the key press event to allow exiting the application with the Esc key.
        """
        if event.key() == QtCore.Qt.Key_Escape:
            QtWidgets.QApplication.quit()

from PyQt5 import QtWidgets, QtCore, QtGui

class ClickableIcon(QtWidgets.QWidget):
    def __init__(self, icon_path, position, filepath, parent=None):
        super().__init__(parent)

        # Set window flags to make the widget frameless and always on top
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnBottomHint |
            QtCore.Qt.Tool
        )

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)      # Remove margins
        layout.setSpacing(4) 

        text = "icon"
        if filepath.endswith(".desktop"):
            text = parse_desktop_file(filepath, "Name")
        else:
            text = os.path.basename(filepath)

        # Create a label to display the icon
        self.icon_label = QtWidgets.QLabel(self)
        pixmap = QtGui.QPixmap(icon_path)
        if pixmap.isNull():
            raise FileNotFoundError(f"Icon file not found or invalid: {icon_path}")
        self.icon_label.setPixmap(pixmap)
        self.icon_label.setScaledContents(True)
        self.icon_label.setFixedSize(64, 64)        # Adjust icon size as needed
        self.icon_label.setToolTip(text)            # Optional: Tooltip on hover

        # Connect the click event to the handler
        self.icon_label.mousePressEvent = self.on_click

        # Create a label to display the text

        textStyle = """
            QLabel {
                color: %s; 
                font-size: 10px;
                font-weight: 5;
                background-color: rgba(0, 0, 0, 0);  /* Transparent background */
            }
        """ % (userSettings.DesktopTextColor)

        self.text_label = QtWidgets.QLabel(self)
        self.text_label.setText(text)
        self.text_label.setAlignment(QtCore.Qt.AlignCenter)
        self.text_label.setStyleSheet(textStyle)  # Customize text appearance
        self.text_label.setWordWrap(True)            # Allow text to wrap to multiple lines if needed

        # Set a fixed height for the text label to ensure consistent spacing
        self.text_label.setFixedHeight(24)           # Adjust height as needed

        # Optionally, set a minimum width to allow text to extend beyond the icon's width
        self.text_label.setMinimumWidth(128) 
        # # Set attribute to have a transparent background
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        # # Create a label to display the icon
        # self.label = QtWidgets.QLabel(self)
        # pixmap = QtGui.QPixmap(icon_path)
        # if pixmap.isNull():
        #     raise FileNotFoundError(f"Icon file not found or invalid: {icon_path}")
        # self.label.setPixmap(pixmap)
        # self.label.setScaledContents(True)
        # self.label.setFixedSize(64, 64)  # Adjust icon size as needed
        # self.icon_label.setToolTip(text) 

        # self.text_label = QtWidgets.QLabel(self)
        # self.text_label.setText(text)
        # self.text_label.setAlignment(QtCore.Qt.AlignCenter)
        # self.text_label.setStyleSheet("""
        #     QLabel {
        #         color: white; 
        #         font-size: 12px;
        #         background-color: rgba(0, 0, 0, 0);  /* Transparent background */
        #     }
        # """)  # Customize text appearance
        # self.text_label.setWordWrap(True)            # Allow text to wrap to multiple lines if needed

        # # Remove fixed width to allow text to extend beyond the icon's edges
        # # Instead, set a maximum width or let it expand as needed
        # self.text_label.setMaximumWidth(128)

        layout.addWidget(self.icon_label, alignment=QtCore.Qt.AlignCenter)
        layout.addWidget(self.text_label, alignment=QtCore.Qt.AlignCenter)
        self.setLayout(layout)

        # Set the position of the icon
        self.move(position)

        # Set the size of the widget to match the icon
        #self.setFixedSize(self.label.size())
        self.adjustSize()

        # Connect the click event
        self.icon_label.mousePressEvent = self.on_click

        self.filepath = filepath

    def on_click(self, event):
        """
        Handle the click event on the icon.
        """
        if event.button() == QtCore.Qt.LeftButton:
            print("Icon left-clicked!")
            # Add your desired functionality here
            # Example: Open a terminal
            if self.filepath.endswith(".desktop"):
                subprocess.run(parse_desktop_file(self.filepath, False).split(" "))
                return
            subprocess.run(['xdg-open', self.filepath], check=True)
        elif event.button() == QtCore.Qt.RightButton:
            self.show_context_menu(event.pos())

    def show_context_menu(self, pos):
        """
        Display a context menu with options.
        """
        menu = QtWidgets.QMenu(self)

        exit_action = menu.addAction("Exit")
        action = menu.exec_(self.mapToGlobal(pos))

        if action == exit_action:
            QtWidgets.QApplication.quit()

    def keyPressEvent(self, event):
        """
        Override the key press event to allow exiting the application with the Esc key.
        """
        if event.key() == QtCore.Qt.Key_Escape:
            QtWidgets.QApplication.quit()

def get_icon_path(filepath):
    """
    Given a MIME type, return the path to the associated icon.
    """

    if os.path.basename(filepath).endswith(".desktop"):
        print("changing to a desktop entry")
        iconname = parse_desktop_file(filepath, True) + ".png"
        homedir = os.path.expanduser("~")
        if os.path.exists("/usr/share/pixmaps/"+ iconname):
            return "/usr/share/pixmaps/" + iconname
        if os.path.exists(homedir + "/.local/share/icons/hicolor/64x64/apps/" + iconname):
            return homedir + "/.local/share/icons/hicolor/64x64/apps/" + iconname
        print("invalid icon! Please search for desktop icons and find a new location to search!")
        return "/usr/share/pixmaps/timeshift.png"

    try:
        fileinfo = Gio.file_new_for_path(filepath).query_info('standard::content-type', 0, None)
        mimetype = fileinfo.get_content_type()
    except Exception as e:
        print(f"Error getting MIME type for {filepath}: {e}")
        mimetype = None

    if mimetype == None:
        return "" # fallback error handling fopr icons, needs to be updated.
    
    icon_theme = Gtk.IconTheme.get_default()
    
    # Get the icon name from the MIME type
    info = Gio.content_type_get_icon(mimetype)
    icon_names = info.get_names()
    
    for icon_name in icon_names:
        # Try to load the icon in PNG format
        icon_info = icon_theme.lookup_icon(icon_name, 48, 0)
        if icon_info:
            return icon_info.get_filename()
    
    # Fallback icon if no specific icon is found
    fallback_icon = icon_theme.lookup_icon("text-x-generic", 48, 0)
    return fallback_icon.get_filename() if fallback_icon else None

def parse_desktop_file(filepath, iconFlag):
    config = configparser.ConfigParser(interpolation=None)
    config.read(filepath)
    
    # Access the properties of the .desktop file
    name = config['Desktop Entry']['Name']
    exec_command = str(config['Desktop Entry']['Exec'])
    
    if iconFlag == True:
        return config['Desktop Entry']["Icon"]
    if iconFlag == "Name":
        return name
    return exec_command

def traverse_directory(directory):
    """
    Traverse the given directory and yield file paths.
    """
    for root, dirs, files in os.walk(directory):
        for file in files:
            yield os.path.join(root, file)

def main():

    # Check if the video file exists
    if not os.path.exists(userSettings.VideoPath):
        print(f"Error: Video file not found at {userSettings.VideoPath}")
        sys.exit(1)

    app = QtWidgets.QApplication(sys.argv)

    # Retrieve all screens
    screens = app.screens()
    print(f"Detected {len(screens)} screen(s).")

    # Create wallpaper windows for each screen
    wallpapers = []
    for idx, screen in enumerate(screens):
        print(f"Creating wallpaper window for screen {idx + 1}: {screen.availableGeometry()}")
        wallpaper = VideoWallpaper(userSettings.VideoPath, screen)
        wallpaper.show()
        wallpapers.append(wallpaper)

    # desktop icons
    icons = []

    Gtk.init()

    # Loop through the desktop
    marginx = 10
    marginy = 0
    for filepath in traverse_directory("/home/nick/Desktop/"):
        geo = screens[0].availableGeometry() # currently the only screen that works with desktop icons is 0
        icon_size = 64  # Must match the size set in ClickableIcon
        position = QtCore.QPoint(
            geo.x() + int(icon_size/2) + marginx,
            geo.y() + int(icon_size/2) + marginy
        )
        marginy += 84
        print(f"Creating clickable icon for screen {idx + 1} at position {position}.")
        icon = ClickableIcon(get_icon_path(filepath), position, filepath)
        icon.show()
        icons.append(icon)

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
