#TODO
# break up into multiple scripts? This is getting weird to navigate

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
        self.VideoPath = '' # This will be a setting later without the cli argument

# Global user settings
userSettings = Settings()

class SharedVideo(QtMultimedia.QAbstractVideoSurface):
    frame_ready = QtCore.pyqtSignal(QtGui.QImage)

    def __init__(self, parent=None):
        super().__init__(parent)

    def supportedPixelFormats(self, handle_type):
        return [
            QtMultimedia.QVideoFrame.Format_RGB32,
            QtMultimedia.QVideoFrame.Format_ARGB32,
            QtMultimedia.QVideoFrame.Format_ARGB32_Premultiplied,
            QtMultimedia.QVideoFrame.Format_RGB24,
        ]

    def present(self, frame):
        image = frame.image()
        if not image.isNull():
            self.frame_ready.emit(image)
        return True

class VideoWallpaper(QtWidgets.QMainWindow):
    def __init__(self, video_surface, screen):
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
        self.video_widget = QtWidgets.QLabel(self)
        self.video_widget.setGeometry(self.rect())
        self.video_widget.setScaledContents(True)
        self.video_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        # self.video_widget = QtMultimediaWidgets.QVideoWidget(self)
        # self.video_widget.setGeometry(self.rect())
        # self.setCentralWidget(self.video_widget)

        video_surface.frame_ready.connect(self.update_frame)

        # Initialize the media player
        #self.media_player = QtMultimedia.QMediaPlayer(self, QtMultimedia.QMediaPlayer.VideoSurface)
        #self.media_player.setVideoOutput(self.video_widget)

        #self.media_player.setMedia(QtMultimedia.QMediaContent(QtCore.QUrl.fromLocalFile(video_path)))
        #self.media_player.setVolume(0)

        self.set_window_type_desktop() # This resizes and pushes the window to the back of everything

        #self.media_player.play()
        self.video_widget.mousePressEvent = self.on_click

        # Connect the media status change to handle looping
        #self.media_player.mediaStatusChanged.connect(self.handle_media_status)

    #@QtCore.pyqtSlot(QtGui.QImage)
    def update_frame(self, image):
        pixmap = QtGui.QPixmap.fromImage(image)
        self.video_widget.setPixmap(pixmap)

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

    def keyPressEvent(self, event):
        """
        Override the key press event to allow exiting the application with the Esc key.
        """
        if event.key() == QtCore.Qt.Key_Escape:
            QtWidgets.QApplication.quit()

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
        exit_action = menu.addAction("Exit")
        action = menu.exec_(self.mapToGlobal(pos))

        if action == exit_action:
            QtWidgets.QApplication.quit()

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

        self.icon_label = QtWidgets.QLabel(self)
        pixmap = QtGui.QPixmap(icon_path)
        if pixmap.isNull():
            raise FileNotFoundError(f"Icon file not found or invalid: {icon_path}")
        self.icon_label.setPixmap(pixmap)
        self.icon_label.setScaledContents(True)
        self.icon_label.setFixedSize(64, 64)

        self.icon_label.mousePressEvent = self.on_click

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
        Sets the window type to NET_WM_WINDOW_TYPE_UTILITY and window state to _NET_WM_STATE_BELOW.
        Without this the icons appear as an open app.
        """
        try:
            window_id = int(self.winId())
            d = display.Display()
            w = d.create_resource_object('window', window_id)

            NET_WM_WINDOW_TYPE = d.get_atom('_NET_WM_WINDOW_TYPE')
            NET_WM_WINDOW_TYPE_UTILITY = d.get_atom('_NET_WM_WINDOW_TYPE_UTILITY')

            w.change_property(NET_WM_WINDOW_TYPE, Xatom.ATOM, 32, [NET_WM_WINDOW_TYPE_UTILITY])

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
            self.show_context_menu(event.pos())

    def show_context_menu(self, pos):
        """
        Display a context menu with options.
        """
        #TODO
        # update options for files specifically

    def keyPressEvent(self, event):
        """
        Override the key press event to allow exiting the application with the Esc key.
        """
        if event.key() == QtCore.Qt.Key_Escape:
            QtWidgets.QApplication.quit()

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
        print("invalid icon! Please search for desktop icons and find a new location to search!")
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

    userSettings.VideoPath = sys.argv[1]

    # Check if the video file exists
    if not os.path.exists(userSettings.VideoPath):
        print(f"Error: Video file not found at {userSettings.VideoPath}")
        sys.exit(1)
    
    # Create wallpaper windows for each screen

    #TODO:
    # This is very bad for performance. Try using one video player to play both videos.
    # Some videos lag, others do not. Size doesn't seem to matter, it seems to be pretty random. 
    # Uncompressed videos work better from what I've seen.

    app = QtWidgets.QApplication(sys.argv)
    shared_surface = SharedVideo()

    media_player = QtMultimedia.QMediaPlayer(None, QtMultimedia.QMediaPlayer.VideoSurface)
    media_player.setVideoOutput(shared_surface)
    media_player.setMedia(QtMultimedia.QMediaContent(QtCore.QUrl.fromLocalFile(userSettings.VideoPath)))
    media_player.setVolume(0)
    media_player.play()

    media_player.mediaStatusChanged.connect(lambda status: media_player.setPosition(0) if status == QtMultimedia.QMediaPlayer.EndOfMedia else None)

    # get all screens
    screens = app.screens()
    wallpapers = []
    for id, screen in enumerate(screens):
        wallpaper = VideoWallpaper(shared_surface, screen)
        wallpaper.show()
        wallpapers.append(wallpaper)

    # desktop icons
    icons = []

    # Only reason I am using gtk is to get desktop icons. Even then it doesn't work for .desktop files so it's almost useless

    Gtk.init()

    marginx = 0
    marginy = 0

    desktopPath = os.path.expanduser("~") + "/Desktop/"

    if not os.path.exists(desktopPath):
        print("No desktop????")
    else:
        for filepath in traverse_directory(desktopPath):
            geo = screens[0].availableGeometry() # currently the only screen that works with desktop icons is 0
            icon_size = 76
            position = QtCore.QPoint(
                geo.x() + int(icon_size/2) + marginx,
                geo.y() + int(icon_size/2) + marginy
            )
            marginy += 100
            #print(ficon screen {idx + 1} position {position}.") # needed for debugging later
            icon = ClickableIcon(get_icon_path(filepath), position, filepath)
            icon.show()
            icons.append(icon)

    sys.exit(app.exec_()) # This allows for execution of other processes but exits the main thread

if __name__ == '__main__':
    main()
