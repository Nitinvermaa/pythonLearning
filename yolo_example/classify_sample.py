# classify_sample.py
from ultralytics import YOLO
from pathlib import Path

def classify_one(image_path: str, weights_path: str = "yolov8n-cls.pt", device: str = "cpu"):
    p_img = Path(image_path).resolve()
    assert p_img.exists(), f"Image not found: {p_img}"

    model = YOLO(weights_path)
    print(f"[info] model.task={model.task}")  # should be 'classify'
    results = model.predict(source=str(p_img), device=device, save=True, verbose=True)
    print(results[0].probs.top1, results[0].names[results[0].probs.top1], float(results[0].probs.top1conf))
    print(f"[info] annotated saved under: {results[0].save_dir}")

if __name__ == "__main__":
    classify_one("ultralytics/assets/bus.jpg", device="cpu")
    # or device="mps"
