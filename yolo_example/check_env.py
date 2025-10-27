# check_env.py
import torch, cv2, ultralytics, platform, sys
print("Python:", sys.version)
print("OS:", platform.platform())
print("Torch:", torch.__version__)
print("Torch CUDA available:", torch.cuda.is_available())
print("Torch MPS available:", torch.backends.mps.is_available() if hasattr(torch.backends, "mps") else False)
print("Ultralytics:", ultralytics.__version__)
print("OpenCV:", cv2.__version__)


#python check_env.py

#Make Ultralytics use a local runs directory (nice & tidy)

#yolo settings runs_dir=./runs
#yolo settings  # prints the current settings

#Run a detection sanity test (CLI)

#yolo predict model=yolov8n.pt source=ultralytics/assets/bus.jpg save=True imgsz=640 conf=0.25 device=cpu
# For Apple Silicon acceleration:
# yolo predict model=yolov8n.pt source=ultralytics/assets/bus.jpg save=True imgsz=640 conf=0.25 device=mps

#Run a classification sanity test (CLI)

#yolo classify predict model=yolov8n-cls.pt source=ultralytics/assets/bus.jpg save=True device=cpu
# or device=mps
