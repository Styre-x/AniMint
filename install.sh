#!/bin/bash

cd ~
git clone https://github.com/Styre-x/AniMint.git
cd AniMint

python3 -m venv aniVenv
source aniVenv/bin/activate

pip install PyQt5 python-xlib PyGObject

sudo touch /usr/local/bin/animint
sudo chmod +x /usr/local/bin/animint
sudo bash -c 'cat <<EOF > /usr/local/bin/animint
#!/bin/bash
source ~/AniMint/aniVenv/bin/activate
python3 ~/AniMint/main.py
EOF'

echo Installed successfully!
