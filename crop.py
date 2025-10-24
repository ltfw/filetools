#!/usr/bin/env python3
"""Crop faces from images in the `photos/` directory and write them to `cropped/`.

Usage: python crop.py

Creates `cropped/` next to `photos/` and saves files named <original>_face<index>.jpg
"""
import os
import sys
import argparse
from pathlib import Path
import cv2


def ensure_cascade(name):
    cascade_name = cv2.data.haarcascades + name
    if not os.path.exists(cascade_name):
        raise FileNotFoundError(f"Haar cascade not found at {cascade_name}. Ensure opencv-python is installed.")
    return cascade_name


def detect_faces(gray_img, cascade, scaleFactor, minNeighbors, minSize):
    return cascade.detectMultiScale(gray_img, scaleFactor=scaleFactor, minNeighbors=minNeighbors, minSize=minSize)


def crop_and_verify(img_path, face_cascade, eye_cascade, out_dir, args):
    img = cv2.imread(str(img_path))
    if img is None:
        print(f"Warning: failed to read {img_path}")
        return 0

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Use stricter detection parameters to reduce false positives
    faces = detect_faces(gray, face_cascade, 
                        scaleFactor=1.05,  # More sensitive scale factor
                        minNeighbors=8,    # Require more neighbors for validation
                        minSize=(50, 50))  # Larger minimum size

    base = img_path.stem
    ext = '.jpg'
    
    # Debug: print number of faces detected
    print(f"  Detected {len(faces)} potential faces")
    
    # Filter faces and calculate quality scores
    valid_faces = []
    for i, (x, y, w, h) in enumerate(faces, start=1):
        # Reject by minimum area ratio if requested
        if args.min_area is not None:
            area_ratio = (w * h) / float(img.shape[0] * img.shape[1])
            if area_ratio < args.min_area:
                continue

        # Check aspect ratio - faces should be roughly square or slightly taller (relaxed)
        aspect_ratio = w / h
        if aspect_ratio < 0.4 or aspect_ratio > 2.0:  # More permissive aspect ratio
            print(f"    Rejected face {i}: bad aspect ratio {aspect_ratio:.2f}")
            continue

        # Check if face is in reasonable position (not at very edges) - relaxed
        img_h, img_w = img.shape[:2]
        if x < img_w * 0.02 or y < img_h * 0.02 or x + w > img_w * 0.98 or y + h > img_h * 0.98:
            print(f"    Rejected face {i}: too close to edge")
            continue

        # Eye detection for quality scoring
        eye_score = 0
        if eye_cascade is not None:
            face_gray = gray[y:y + h, x:x + w]
            eyes = eye_cascade.detectMultiScale(face_gray, scaleFactor=1.1, minNeighbors=3)
            eye_score = len(eyes)
            
            # Make eye detection optional - don't reject if no eyes found
            if eye_score < 1:
                print(f"    Face {i}: no eyes detected (keeping anyway)")
                eye_score = 0

        # Calculate quality score
        area_score = w * h
        # Bonus for faces with 2 eyes, penalty for very small faces
        quality_score = area_score + (eye_score * 2000) - (1000 if w < 80 or h < 80 else 0)
        
        valid_faces.append({
            'coords': (x, y, w, h),
            'quality': quality_score,
            'eye_count': eye_score
        })

    if not valid_faces:
        return 0

    # Select the face with the highest quality score
    best_face = max(valid_faces, key=lambda f: f['quality'])
    x, y, w, h = best_face['coords']

    # Expand box slightly for better framing
    pad = int(0.2 * max(w, h))
    x1 = max(0, x - pad)
    y1 = max(0, y - pad)
    x2 = min(img.shape[1], x + w + pad)
    y2 = min(img.shape[0], y + h + pad)
    face_img = img[y1:y2, x1:x2]
    out_path = out_dir / f"{base}_face{ext}"
    cv2.imwrite(str(out_path), face_img)

    # Optionally write annotated image
    if args.annotate:
        ann_dir = out_dir / 'annotated'
        ann_dir.mkdir(exist_ok=True)
        ann = img.copy()
        cv2.rectangle(ann, (x1, y1), (x2, y2), (0, 255, 0), 2)
        ann_path = ann_dir / f"{base}_ann{ext}"
        cv2.imwrite(str(ann_path), ann)

    return 1


def parse_args():
    p = argparse.ArgumentParser(description='Crop faces from images in photos/ and save to cropped/')
    p.add_argument('--verify-eyes', action='store_true', help='Require eyes inside detected face (reduces false positives)')
    p.add_argument('--min-eyes', type=int, default=1, help='Minimum number of eyes required when --verify-eyes is set')
    p.add_argument('--min-area', type=float, default=0.0, help='Minimum face area ratio relative to image (0.0-1.0). Skip detections smaller than this')
    p.add_argument('--scale-factor', type=float, default=1.1, help='scaleFactor for detectMultiScale')
    p.add_argument('--min-neighbors', type=int, default=5, help='minNeighbors for detectMultiScale')
    p.add_argument('--min-size', type=int, default=30, help='minimum size (px) for face detection window')
    p.add_argument('--annotate', action='store_true', help='Save annotated copies with rectangles into cropped/annotated/')
    return p.parse_args()


def main():
    args = parse_args()

    repo_root = Path(__file__).resolve().parent
    photos_dir = repo_root / 'photos'
    out_dir = repo_root / 'cropped'

    if not photos_dir.exists():
        print(f"Photos directory not found: {photos_dir}")
        sys.exit(1)

    out_dir.mkdir(exist_ok=True)

    face_cascade_path = ensure_cascade('haarcascade_frontalface_default.xml')
    face_cascade = cv2.CascadeClassifier(face_cascade_path)

    # Always try to load eye cascade for better accuracy
    eye_cascade = None
    try:
        eye_cascade_path = ensure_cascade('haarcascade_eye.xml')
        eye_cascade = cv2.CascadeClassifier(eye_cascade_path)
        print('Eye detection enabled for better accuracy')
    except FileNotFoundError:
        print('Eye cascade not found; using face detection only.')
        eye_cascade = None

    supported_ext = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
    total_images = 0
    total_faces = 0

    for p in sorted(photos_dir.iterdir()):
        if p.is_file() and p.suffix.lower() in supported_ext:
            total_images += 1
            faces_found = crop_and_verify(p, face_cascade, eye_cascade, out_dir, args)
            print(f"{p.name}: {faces_found} face(s)")
            total_faces += faces_found

    print('-' * 40)
    print(f"Processed images: {total_images}")
    print(f"Total faces saved: {total_faces}")


if __name__ == '__main__':
    main()
