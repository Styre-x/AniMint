An animated wallpaper manager for Linux Mint 22. Likely works on other Ubuntu-based distributions, please check and let me know!
Currently very bare-bones, more will be added soon.

It is very simple to use:

Install required libraries:
```
sudo apt-get install python3-gi

pip install PyQt5 python-xlib
```

Run the main file:
python3 main.py

This will pop up a window to choose a wallpaper mp4 video.

KomorebiPy is better on performance for CPU, but often crashes due to the outdated libraries in use.
Rather than try and update the libraries for Komorebi, I decided to re-write it with QtPy.

To be added:
A better right-click menu with customization options
