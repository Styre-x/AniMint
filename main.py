#TODO
# break up into multiple scripts? This is getting weird to navigate

import sys
import os
import configparser
import time
from PyQt5 import QtWidgets, QtCore, QtGui, QtMultimedia, QtMultimediaWidgets
from Xlib import display
from Xlib import Xatom
import subprocess
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gio, Gtk

# wallpapers and icons so I don't have to pass a reference to everything everywhere
wallpapers = []
icons = []

# Global user settings
userSettings = configparser.ConfigParser()
userSettings['Settings'] = {
    'wallpaper': 'empty',
    'textcolor': 'black'
}

def saveSettings():
    with open("settings", "w") as file:
        userSettings.write(file)
        file.close()

if not os.path.exists("settings"):
    saveSettings()

userSettings = configparser.ConfigParser()
userSettings.read("settings")


class VideoWallpaper(QtWidgets.QMainWindow):
    def __init__(self, screen, manager):
        super().__init__()

        self.screen = screen

        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |            # Remove window borders
            QtCore.Qt.WindowStaysOnBottomHint          # Attempt to keep the window at the bottom
        )

        # Get the available geometry excluding panels and docks
        available_geo = self.screen.availableGeometry()
        self.setGeometry(available_geo)

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

        # Create a video widget to display the video
        self.video_widget = QtMultimediaWidgets.QVideoWidget(self)
        self.video_widget.setGeometry(self.rect())
        self.setCentralWidget(self.video_widget)

        # Initialize the media player
        self.media_player = QtMultimedia.QMediaPlayer(self, QtMultimedia.QMediaPlayer.VideoSurface)
        self.media_player.setVideoOutput(self.video_widget)

        self.set_window_type_desktop() # This resizes and pushes the window to the back of everything
        self.video_widget.mousePressEvent = self.on_click

        # Connect the media status change to handle looping
        self.media_player.mediaStatusChanged.connect(self.handle_media_status)

        self.WallpaperManager = manager

    def loadVideo(self):
        self.media_player.setMedia(QtMultimedia.QMediaContent(QtCore.QUrl.fromLocalFile(userSettings["Settings"]['wallpaper'])))
        self.media_player.setVolume(0)
        self.media_player.play()

    def handle_media_status(self, status):
        if status == QtMultimedia.QMediaPlayer.EndOfMedia:
            self.media_player.setPosition(0)
            self.media_player.play()

    def set_window_type_desktop(self):
        """
        Sets the window type to _NET_WM_WINDOW_TYPE_DESKTOP and window state to _NET_WM_STATE_BELOW.
        Without this the desktop appears as an open app, gross!
        """
        try:
            window_id = int(self.winId())
            d = display.Display()
            w = d.create_resource_object('window', window_id)

            NET_WM_WINDOW_TYPE = d.get_atom('_NET_WM_WINDOW_TYPE')
            NET_WM_WINDOW_TYPE_DESKTOP = d.get_atom('_NET_WM_WINDOW_TYPE_DESKTOP')

            NET_WM_STATE = d.get_atom('_NET_WM_STATE')
            NET_WM_STATE_BELOW = d.get_atom('_NET_WM_STATE_BELOW')

            w.change_property(NET_WM_WINDOW_TYPE, Xatom.ATOM, 32, [NET_WM_WINDOW_TYPE_DESKTOP])
            w.change_property(NET_WM_STATE, Xatom.ATOM, 32, [NET_WM_STATE_BELOW])

            d.sync()
        except Exception as e:
            print(f"Error setting window type: {e}")

    def on_click(self, event):
        """
        Handle the click event on the video.
        """
        if event.button() == QtCore.Qt.RightButton:
            self.show_context_menu(event.pos())

    def show_context_menu(self, pos):
        """
        Display a context menu with options.
        """
        menu = QtWidgets.QMenu(self)
        # create a menu to display when right clicked
        manager_action = menu.addAction("Wallpaper Manager")
        exit_action = menu.addAction("Exit")
        action = menu.exec_(self.mapToGlobal(pos))

        if action == exit_action:
            QtWidgets.QApplication.quit()
        if action == manager_action:
            self.WallpaperManager.show()

class ClickableIcon(QtWidgets.QWidget):
    def __init__(self, icon_path, position, filepath, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnBottomHint
        )

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4) 

        text = "icon"
        if filepath.endswith(".desktop"):
            text = parse_desktop_file(filepath, "Name")
        else:
            text = os.path.basename(filepath)

        if len(text) >= 45:
            text = text[:48] + "..."

        self.icon_label = QtWidgets.QLabel(self)
        pixmap = QtGui.QPixmap(icon_path)
        if pixmap.isNull():
            raise FileNotFoundError(f"Icon file not found or invalid: {icon_path}")
        self.icon_label.setPixmap(pixmap)
        self.icon_label.setScaledContents(True)
        self.icon_label.setFixedSize(50, 50)

        self.icon_label.mousePressEvent = self.on_click

        textStyle = """
            QLabel {
                color: %s; 
                font-size: 10px;
                font-weight: 5;
                background-color: rgba(0, 0, 0, 0);  /* Transparent background */
            }
        """ % (userSettings['Settings']["textcolor"])

        self.text_label = QtWidgets.QLabel(self)
        self.text_label.setText(text)
        self.text_label.setAlignment(QtCore.Qt.AlignCenter)
        self.text_label.setStyleSheet(textStyle)
        self.text_label.setWordWrap(True)

        self.text_label.setFixedHeight(24)
        self.text_label.setMinimumWidth(128)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        layout.addWidget(self.icon_label, alignment=QtCore.Qt.AlignCenter)
        layout.addWidget(self.text_label, alignment=QtCore.Qt.AlignCenter)
        self.setLayout(layout)
        self.remove_open_apps()
        self.move(position)
        self.adjustSize()

        # store the file path for the icon in the object
        self.filepath = filepath

    def remove_open_apps(self):
        """
        Sets the window type to NET_WM_WINDOW_TYPE_DOCK and window state to _NET_WM_STATE_BELOW.
        Without this the icons appear as an open app.
        """
        try:
            window_id = int(self.winId())
            d = display.Display()
            w = d.create_resource_object('window', window_id)

            NET_WM_WINDOW_TYPE = d.get_atom('_NET_WM_WINDOW_TYPE')
            NET_WM_WINDOW_TYPE_DOCK = d.get_atom('_NET_WM_WINDOW_TYPE_DOCK')

            w.change_property(NET_WM_WINDOW_TYPE, Xatom.ATOM, 32, [NET_WM_WINDOW_TYPE_DOCK])

            d.sync()
        except Exception as e:
            print(f"Error setting window type: {e}")

    def on_click(self, event):
        """
        Handle the click event on the icon.
        """
        if event.button() == QtCore.Qt.LeftButton:
            if self.filepath.endswith(".desktop"): # parse it and run it if it is a desktop file.
                subprocess.run(parse_desktop_file(self.filepath, False).split(" "))
                return
            subprocess.run(['xdg-open', self.filepath], check=True) # I think this opens everything correctly? 
        elif event.button() == QtCore.Qt.RightButton:
            self.show_context_menu()

    def show_context_menu(self):
        """
        Display a context menu with options.
        """
        #TODO
        # update options for files specifically
        print("something should happen here. May be a good idea to get working on that...")
    
    def update_text(self):
        textStyle = """
            QLabel {
                color: %s; 
                font-size: 10px;
                font-weight: 5;
                background-color: rgba(0, 0, 0, 0);  /* Transparent background */
            }
        """ % (userSettings['Settings']["textcolor"])
        self.text_label.setStyleSheet(textStyle)

class WallpaperManager(QtWidgets.QWidget):
    def __init__(self, wallpapers, parent=None):
        """
        Initializes the WallpaperManager widget.

        Parameters:
        - parent (QWidget, optional): Parent widget. Defaults to None.
        """
        super().__init__(parent)
        
        # Set up the UI
        self.init_ui()
        self.wallpapers = wallpapers
    
    def init_ui(self):
        """
        Sets up the user interface components.
        """
        self.setWindowTitle("Wallpaper Manager")
        self.setFixedSize(400, 150)
        self.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.WindowTitleHint)
        
        # Create layout
        layout = QtWidgets.QVBoxLayout()
        
        layout.addWidget(QtWidgets.QLabel("Desktop Icon Text Color:"))

        # Dropdown for text colors
        self.color_dropdown = QtWidgets.QComboBox()
        self.color_dropdown.addItems(["Black", "White", "Red", "Green", "Blue", "Yellow", "Cyan", "Magenta"])
        self.color_dropdown.currentTextChanged.connect(self.color_selected)
        layout.addWidget(self.color_dropdown)

        # Instruction label
        instruction_label = QtWidgets.QLabel("Select a new wallpaper:")
        layout.addWidget(instruction_label)
        
        # Horizontal layout for buttons
        button_layout = QtWidgets.QHBoxLayout()
        
        # Change Wallpaper Button
        self.change_button = QtWidgets.QPushButton("Change Wallpaper")
        self.change_button.clicked.connect(self.choose_wallpaper)
        button_layout.addWidget(self.change_button)
        
        # Cancel Button
        self.cancel_button = QtWidgets.QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.hide)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def show(self):
        """
        Overrides the show method to display the dialog.
        """
        super().show()
    
    def hide(self):
        """
        Overrides the hide method to close the dialog.
        """
        super().hide()
    
    def choose_wallpaper(self):
        """
        Opens a file dialog to select a new wallpaper and sets it.
        """
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.ReadOnly
        file_filter = "MP4 Videos (*.mp4)"
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Wallpaper", "", file_filter, options=options)
        
        if file_path:
            self.set_wallpaper(file_path)
            self.hide()
            for wallpaper in self.wallpapers:
                wallpaper.loadVideo()
    
    def set_wallpaper(self, wallpaper_path):
        """
        Sets the selected video
        Parameters:
        - wallpaper_path (str): Absolute path to the wallpaper image.
        """
        if not os.path.isfile(wallpaper_path):
            QtWidgets.QMessageBox.warning(self, "Error", "Selected file does not exist.")
            return
        
        userSettings['Settings']['wallpaper'] = wallpaper_path
        saveSettings()

    def color_selected(self, color):
        """
        Sets the selected text color
        """
        userSettings["Settings"]["textcolor"] = color
        saveSettings()
        for icon in icons:
            icon.update_text()

def get_icon_path(filepath):
    """
    Given a file path string, return the path to the associated icon.
    Parameters: File path
    Returns: string file path to icon
    """

    # this is so gross but .desktop icons (specifically steam) were weird and did not look good.
    # This fixes that. 
    if os.path.basename(filepath).endswith(".desktop"):
        iconname = parse_desktop_file(filepath, True) + ".png"
        homedir = os.path.expanduser("~")
        if os.path.exists("/usr/share/pixmaps/"+ iconname):
            return "/usr/share/pixmaps/" + iconname
        if os.path.exists(homedir + "/.local/share/icons/hicolor/64x64/apps/" + iconname):
            return homedir + "/.local/share/icons/hicolor/64x64/apps/" + iconname
        print("invalid icon! Please search for desktop icons and find a new location to search! Line 323 or around there")
        # fallback: just return a gear for the icon

    try:
        fileinfo = Gio.file_new_for_path(filepath).query_info('standard::content-type', 0, None)
        mimetype = fileinfo.get_content_type()
    except Exception as e:
        print(f"Error getting MIME type for {filepath}: {e}")
        mimetype = None
    
    icon_theme = Gtk.IconTheme.get_default()
    
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
    """
    Find the icon, name, or command from a .desktop file
    Parameters: File path, iconFlag (True for icon, False for command, "Name" for name)
    Returns: String, icon, command, or name
    """
    config = configparser.ConfigParser(interpolation=None)
    config.read(filepath)
    
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
    Parameters: directory
    Returns: None
    """
    for root, dirs, files in os.walk(directory):
        for file in files:
            yield os.path.join(root, file)

def main():

    app = QtWidgets.QApplication(sys.argv)

    # get all screens
    screens = app.screens()

    # Create wallpaper windows for each screen

    #TODO:
    # This is very bad for performance. Try using one video player to play both videos.
    # Some videos lag, others do not. Size doesn't seem to matter, it seems to be pretty random. 
    # Uncompressed videos work better from what I've seen.

    
    manager = WallpaperManager(wallpapers)

    if userSettings['Settings']['wallpaper'] == "empty":
        manager.show()

    for idx, screen in enumerate(screens):
        wallpaper = VideoWallpaper(screen, manager)
        wallpaper.show()
        wallpapers.append(wallpaper)
        if userSettings['Settings']['wallpaper'] != "empty":
            wallpaper.loadVideo()

    # Only reason I am using gtk is to get desktop icons. Even then it doesn't work for .desktop files so it's almost useless

    Gtk.init()

    marginx = 0
    marginy = 0

    desktopPath = os.path.expanduser("~") + "/Desktop/"

    if not os.path.exists(desktopPath):
        print("No desktop????")
    else:
        geo = screens[0].availableGeometry() # currently the only screen that works with desktop icons is 0
        # print(geo.width(), geo.height())
        maxy = geo.height() - 140
        for filepath in traverse_directory(desktopPath):
            icon_size = 64
            position = QtCore.QPoint(
                int(icon_size/2) + marginx,
                int(icon_size/2) + marginy
            )
            marginy += 86
            
            if marginy >= maxy:
                marginy = 0
                marginx += 135
            icon = ClickableIcon(get_icon_path(filepath), position, filepath)
            icon.show()
            icons.append(icon)

    sys.exit(app.exec_()) # This allows for execution of other processes but exits the main thread

if __name__ == '__main__':
    main()
