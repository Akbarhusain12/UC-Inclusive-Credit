import sys
import cv2
import pytesseract
import os
import json
from pytesseract import Output
import pdfplumber

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

ROTATION_MAP = {
    0:   None,
    90:  cv2.ROTATE_90_CLOCKWISE,
    180: cv2.ROTATE_180,
    270: cv2.ROTATE_90_COUNTERCLOCKWISE,
}


def rotate_image(img, angle):
    code = ROTATION_MAP.get(angle)
    return cv2.rotate(img, code) if code is not None else img


def best_rotation_angle(gray):

    h, w = gray.shape
    scale = min(1.0, 600 / max(h, w))
    small = cv2.resize(gray, None, fx=scale, fy=scale,
                       interpolation=cv2.INTER_AREA)

    best_angle, best_score = 0, -1

    for angle in [0, 90, 180, 270]:
        candidate = rotate_image(small, angle)
        data = pytesseract.image_to_data(
            candidate, output_type=Output.DICT,
            config="--oem 3 --psm 3"
        )
        scores = [int(c) for c in data["conf"]
                  if str(c) != "-1" and int(c) > 0]
        word_count = len(scores)
        avg_conf   = sum(scores) / word_count if word_count else 0
        score      = avg_conf * word_count

        print(f"[ROT] {angle:3d}° -> avg_conf {avg_conf:.1f}  "
              f"words {word_count:3d}  score {score:.0f}",
              file=sys.stderr)

        if score > best_score:
            best_score, best_angle = score, angle

    print(f"[ROT] Chosen: {best_angle}°  (score {best_score:.0f})",
          file=sys.stderr)
    return best_angle


def fix_inversion(gray):
    mean_brightness = gray.mean()
    if mean_brightness < 127:
        print(f"[INV] Dark background detected (mean={mean_brightness:.1f}), inverting.",
              file=sys.stderr)
        gray = cv2.bitwise_not(gray)
    else:
        print(f"[INV] Light background (mean={mean_brightness:.1f}), no inversion needed.",
              file=sys.stderr)
    return gray


def preprocess(gray):
    h, w = gray.shape
    if max(h, w) < 1500:
        scale = 1500 / max(h, w)
        gray = cv2.resize(gray, None, fx=scale, fy=scale,
                          interpolation=cv2.INTER_CUBIC)
        print(f"[PRE] Upscaled {scale:.2f}x -> {gray.shape[1]}x{gray.shape[0]}",
              file=sys.stderr)

    gray = fix_inversion(gray)

    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    processed = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        21, 10
    )
    return processed


def extract_text_from_image(image_path):
    img = cv2.imread(image_path)
    if img is None:
        raise Exception(f"OpenCV could not read: {image_path}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    angle = best_rotation_angle(gray)

    img = rotate_image(img, angle)

    gray_rotated = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    processed = preprocess(gray_rotated)

    config = r"--oem 3 --psm 4"
    text = pytesseract.image_to_string(processed, config=config)

    data = pytesseract.image_to_data(processed, output_type=Output.DICT,
                                     config=config)
    scores = [int(c) for c in data["conf"] if str(c) != "-1" and int(c) > 0]
    avg_conf = round(sum(scores) / len(scores), 2) if scores else 0.0

    return text.strip(), avg_conf


def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                except Exception as e:
                    print(f"[PDF] Warning: could not read page {i+1}: {e}",
                          file=sys.stderr)
                    continue
    except Exception as e:
        print(f"[PDF] Error opening PDF: {e}", file=sys.stderr)
        return ""

    return text.strip()


def process_file(file_path):
    if not os.path.exists(file_path):
        print(f"ERROR: File not found at {file_path}", file=sys.stderr)
        sys.exit(1)

    try:
        if file_path.lower().endswith(".pdf"):
            text = extract_text_from_pdf(file_path)
            confidence = 100.0
        else:
            text, confidence = extract_text_from_image(file_path)

        if not text:
            print("WARNING: No text extracted", file=sys.stderr)
            print(json.dumps({"raw_text": "", "confidence": 0}))
            sys.exit(0)

        result = {"raw_text": text, "confidence": confidence}
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(0)

    except Exception as e:
        print(f"CRITICAL ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("ERROR: Usage: python vision_extractor.py <file_path>",
              file=sys.stderr)
        sys.exit(1)
    process_file(sys.argv[1])