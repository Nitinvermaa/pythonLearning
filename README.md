# pythonLearning ----


# (optional) reset Ultralytics settings and runs dir
rm -rf ~/Library/Application\ Support/Ultralytics
rm -rf runs        # if you have a local runs/ folder in your project



Create & activate a virtual environment (macOS)

cd /path/to/your/project

# create venv
python3 -m venv .venv
# activate it
source .venv/bin/activate

# upgrade pip
python -m pip install --upgrade pip wheel setuptools


Install the libraries (CPU or Apple Silicon)

pip install "ultralytics>=8.3.0" opencv-python


Apple Silicon (M-series) with Metal (optional acceleration)
Recent PyTorch builds ship MPS by default, but if you need to pin:

pip install "torch>=2.2.0" "torchvision>=0.17.0" --index-url https://download.pytorch.org/whl/cpu
pip install "ultralytics>=8.3.0" opencv-python


