# detect_sample.py
from pathlib import Path
import json, cv2
from ultralytics import YOLO

def detect_one(image_path: str,
               weights_path: str = "yolov8n.pt",
               device: str = "cpu",
               imgsz: int = 640,
               conf: float = 0.25):
    p_img = Path(image_path).resolve()
    assert p_img.exists(), f"Image not found: {p_img}"

    model = YOLO(weights_path)
    print(f"[info] model.task={model.task}, classes={model.names}")

    # Read image to confirm decode works
    img = cv2.imread(str(p_img))
    assert img is not None, f"cv2 could not read image: {p_img}"
    H, W = img.shape[:2]

    results = model.predict(
        source=str(p_img),
        imgsz=imgsz,
        conf=conf,
        iou=0.45,
        device=device,     # "cpu" | "mps" | "0"
        save=True,         # saves annotated image to runs/<task>/predict
        show=False,
        verbose=True
    )

    det = []
    r0 = results[0]
    # For detect/segment models, r0.boxes contains boxes; for segment, also r0.masks
    if getattr(r0, "boxes", None) is not None:
        for b in r0.boxes:
            x1, y1, x2, y2 = map(int, b.xyxy[0])
            conf_b = float(b.conf[0])
            cls_id = int(b.cls[0])
            det.append({
                "label": model.names.get(cls_id, str(cls_id)),
                "confidence": conf_b,
                "bbox": [x1, y1, x2, y2],
                "image_width": W,
                "image_height": H
            })
    print(json.dumps(det, indent=2))
    print(f"[info] annotated saved under: {results[0].save_dir}")

if __name__ == "__main__":
    # built-in sample image
    detect_one("ultralytics/assets/bus.jpg", weights_path="yolov8n.pt", device="cpu")
    # If you want Apple Silicon Metal:
    # detect_one("ultralytics/assets/bus.jpg", weights_path="yolov8n.pt", device="mps")


