## AniMint

An animated wallpaper manager for Linux Mint. Likely works on other Ubuntu-based distributions, please check and let me know!
Currently very bare-bones, more will be added soon.

You can either run install.sh which will clone the repo, set up a venv, and install packages or clone and install yourself.
If you run install.sh, it will create a new command `animint` that will open the wallpaper.

## automatic install

copy/paste or download `install.sh` and run it. Run `animint` and choose a wallpaper. All done!

## manual install

Install required libraries,
 I recommend a python venv:
```
pip install PyQt5 python-xlib PyGObject
```

clone the repo:
```
git clone https://github.com/Styre-x/AniMint.git
```

Run the main file:
python3 main.py

This will pop up a window to choose a wallpaper mp4 video.

## Issues

Current issues:
scaling can be weird. Choose a wallpaper and relaunch to fix most of the time.

Icon dragging broke clicking to open files, will fix soon. 

## features

To be added:
A better right-click menu with customization options

Komorebi is better for performance, but often crashes due to the outdated libraries in use.
Rather than try and update the libraries for Komorebi, I decided to re-write it with QtPy.
