#!/usr/bin/env python3
"""Crop faces and resize images to below 1MB, with filename format Firstname+Lastname_ID.jpg.

Usage:
  python crop_resize.py <input_path> [options]
"""

import os
import sys
import re
import argparse
from pathlib import Path
import cv2


def ensure_cascade(name):
    """Ensure cascade XML is available and return its absolute path."""
    cascade_name = cv2.data.haarcascades + name
    if not os.path.exists(cascade_name):
        raise FileNotFoundError(f"Haar cascade not found at {cascade_name}. Ensure opencv-python is installed.")
    return cascade_name


def clean_name(name_part):
    """Clean credentials, suffixes, departments, and extra whitespaces from name."""
    # Remove common file suffixes like _face, _ann
    name_part = re.sub(r'(_face\d*|_ann\d*)$', '', name_part, flags=re.IGNORECASE)
    
    # Remove department/role suffix (anything after a hyphen)
    if '-' in name_part:
        name_part = name_part.split('-')[0]
        
    # Remove degree credentials/titles (anything after a comma)
    if ',' in name_part:
        name_part = name_part.split(',')[0]
        
    # Replace underscores, hyphens, and multiple spaces with a single space
    name_part = re.sub(r'[_\s-]+', ' ', name_part).strip()
    return name_part


def parse_filename(filepath_or_name):
    """Parse name and ID/NIK from filename or filepath stem.
    
    Examples:
      - "0812170098 Susantoko" -> ("Susantoko", "0812170098")
      - "1005240708 Muhammad Anwar" -> ("Muhammad Anwar", "1005240708")
      - "0804180215_Noky Anresa Ferdiyanta" -> ("Noky Anresa Ferdiyanta", "0804180215")
    """
    stem = Path(filepath_or_name).stem
    
    # 1. Match digits at the start: e.g. "0812170098 Susantoko", "0804180215_Noky Anresa Ferdiyanta"
    start_match = re.match(r'^(\d+)[_\s-]+(.*)$', stem)
    if start_match:
        nik = start_match.group(1)
        raw_name = start_match.group(2)
        return clean_name(raw_name), nik
        
    # 2. Match digits at the end: e.g. "Susantoko_0812170098"
    end_match = re.search(r'^(.*?)[_\s-]+(\d+)$', stem)
    if end_match:
        raw_name = end_match.group(1)
        nik = end_match.group(2)
        return clean_name(raw_name), nik
        
    # 3. Match any sequence of digits in case of missing separators
    all_digit_seqs = re.findall(r'\b\d{3,}\b', stem)
    if all_digit_seqs:
        nik = all_digit_seqs[0]
        raw_name = stem.replace(nik, '').strip()
        return clean_name(raw_name), nik

    # No ID found, just clean the stem
    return clean_name(stem), None


def format_employee_name(full_name):
    """Format full name into the required format:
      - 1 word: Name
      - 2 words: Firstname+Lastname
      - >= 3 words: Firstname Middle1 Middle2+Lastname
      
    All words are formatted to Title Case.
    """
    words = [w.strip() for w in full_name.split() if w.strip()]
    if not words:
        return "Unknown"
        
    # Standardize casing to Title Case
    words = [w.capitalize() for w in words]
    
    if len(words) == 1:
        return words[0]
    elif len(words) == 2:
        return f"{words[0]}+{words[1]}"
    else:
        # 3 or more words: first N-1 parts space-separated, followed by '+' and the last part
        first_middle = " ".join(words[:-1])
        last = words[-1]
        return f"{first_middle}+{last}"


def detect_and_crop_face(img, face_cascade, eye_cascade, args):
    """Detect the highest quality face and return the cropped face image, or None."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Use robust detection parameters (from crop.py)
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=args.scale_factor,
        minNeighbors=args.min_neighbors,
        minSize=(args.min_size, args.min_size)
    )
    
    if len(faces) == 0:
        return None, None
        
    valid_faces = []
    img_h, img_w = img.shape[:2]
    
    for i, (x, y, w, h) in enumerate(faces, start=1):
        # Filter by minimum area ratio
        if args.min_area > 0.0:
            area_ratio = (w * h) / float(img_h * img_w)
            if area_ratio < args.min_area:
                continue

        # Check aspect ratio (permissive check)
        aspect_ratio = w / h
        if aspect_ratio < 0.4 or aspect_ratio > 2.0:
            continue

        # Check position (not too close to edge)
        if x < img_w * 0.02 or y < img_h * 0.02 or x + w > img_w * 0.98 or y + h > img_h * 0.98:
            continue

        # Eye detection score
        eye_score = 0
        if eye_cascade is not None:
            face_gray = gray[y:y + h, x:x + w]
            eyes = eye_cascade.detectMultiScale(face_gray, scaleFactor=1.1, minNeighbors=3)
            eye_score = len(eyes)

        # Quality scoring
        area_score = w * h
        quality_score = area_score + (eye_score * 2000) - (1000 if w < 80 or h < 80 else 0)
        
        valid_faces.append({
            'coords': (x, y, w, h),
            'quality': quality_score,
            'eye_count': eye_score
        })

    if not valid_faces:
        return None, None

    # Pick face with highest quality score
    best_face = max(valid_faces, key=lambda f: f['quality'])
    x, y, w, h = best_face['coords']

    # Expand box slightly for better framing
    pad = int(0.2 * max(w, h))
    x1 = max(0, x - pad)
    y1 = max(0, y - pad)
    x2 = min(img_w, x + w + pad)
    y2 = min(img_h, y + h + pad)
    
    cropped = img[y1:y2, x1:x2]
    return cropped, (x1, y1, x2, y2)


def save_image_under_max_size(img, output_path, max_size_bytes=1000000):
    """Save image, compressing and downscaling iteratively until size is under limit."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    quality = 95
    scale = 1.0
    orig_h, orig_w = img.shape[:2]
    
    current_img = img.copy()
    iteration = 0
    max_iterations = 25
    
    while iteration < max_iterations:
        # Save image with current quality setting
        success = cv2.imwrite(str(output_path), current_img, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        if not success:
            print(f"  Error: Failed to write image to {output_path}")
            return False
            
        file_size = output_path.stat().st_size
        if file_size < max_size_bytes:
            return True
            
        # If too large, try reducing quality
        if quality > 30:
            quality -= 5
        else:
            # If quality is already low (30), downscale dimensions
            scale *= 0.85
            new_w = int(orig_w * scale)
            new_h = int(orig_h * scale)
            
            if new_w < 100 or new_h < 100:
                # Go down to absolute minimum quality if already very small
                if quality > 10:
                    quality -= 5
                else:
                    print(f"  Warning: Reached compression limits. Output file is {file_size / 1024:.1f} KB")
                    break
            else:
                current_img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
                quality = 90  # Reset quality for new downscaled image
                
        iteration += 1
        
    return output_path.stat().st_size < max_size_bytes


def process_image(img_path, face_cascade, eye_cascade, out_dir, args):
    """Process a single image file: parse details, crop, resize, and save."""
    print(f"Processing: {img_path.name}")
    
    # 1. Parse name and ID
    parsed_name, parsed_id = parse_filename(img_path.name)
    
    # CLI arguments override parsing if specified
    name = args.name if args.name else parsed_name
    nik = args.id if args.id else parsed_id
    
    if not name:
        name = "Unknown"
        
    formatted_name = format_employee_name(name)
    
    # Format target filename
    if nik:
        out_filename = f"{formatted_name}_{nik}.jpg"
    else:
        out_filename = f"{formatted_name}.jpg"
        
    out_path = out_dir / out_filename
    
    # 2. Read image
    img = cv2.imread(str(img_path))
    if img is None:
        print(f"  Error: Failed to read image: {img_path}")
        return False
        
    processed_img = None
    face_coords = None
    
    # 3. Crop face (unless --no-crop is set)
    if not args.no_crop:
        processed_img, face_coords = detect_and_crop_face(img, face_cascade, eye_cascade, args)
        if processed_img is None:
            print("  Warning: No face detected.")
            if args.fallback_to_full:
                print("  Falling back to resizing the full image instead.")
                processed_img = img
            else:
                print("  Skipping file.")
                return False
        else:
            print(f"  Face detected and cropped.")
    else:
        processed_img = img
        print("  Skipping face crop as requested.")
        
    # 4. Save and compress under target size
    max_size_bytes = int(args.max_size * 1024 * 1024)
    success = save_image_under_max_size(processed_img, out_path, max_size_bytes)
    
    if success:
        size_kb = out_path.stat().st_size / 1024
        print(f"  Saved to: {out_path.name} ({size_kb:.1f} KB)")
        
        # Save annotated copy if requested (only when cropping was done)
        if args.annotate and face_coords is not None:
            ann_dir = out_dir / 'annotated'
            ann_dir.mkdir(exist_ok=True)
            ann_img = img.copy()
            x1, y1, x2, y2 = face_coords
            cv2.rectangle(ann_img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            ann_path = ann_dir / f"{out_path.stem}_ann.jpg"
            cv2.imwrite(str(ann_path), ann_img)
            print(f"  Saved annotation to: {ann_path.name}")
    else:
        print(f"  Error: Failed to save processed image.")
        
    return success


def parse_args():
    p = argparse.ArgumentParser(description="Crop face and resize images to below 1MB.")
    p.add_argument("input", help="Input image file path or directory containing images.")
    p.add_argument("-o", "--out-dir", default="output", help="Output directory path (default: output).")
    p.add_argument("--no-crop", action="store_true", help="Skip face cropping and resize the full image instead.")
    p.add_argument("--max-size", type=float, default=1.0, help="Maximum file size of the output image in MB (default: 1.0).")
    p.add_argument("--name", help="Explicitly specify the employee's name (overrides filename parsing).")
    p.add_argument("--id", help="Explicitly specify the employee's ID/NIK (overrides filename parsing).")
    p.add_argument("--fallback-to-full", action="store_true", default=True, help="Fall back to resizing full image if face crop fails (default: True).")
    p.add_argument("--no-fallback", action="store_false", dest="fallback_to_full", help="Disable fallback to full image resizing when face crop fails.")
    p.add_argument("--annotate", action="store_true", help="Save annotated copy showing the detected face bounding box.")
    
    # Face detection tuning parameters
    p.add_argument("--scale-factor", type=float, default=1.05, help="scaleFactor for OpenCV face detection (default: 1.05).")
    p.add_argument("--min-neighbors", type=int, default=8, help="minNeighbors for OpenCV face detection (default: 8).")
    p.add_argument("--min-size", type=int, default=50, help="Minimum width/height for detected face window (default: 50).")
    p.add_argument("--min-area", type=float, default=0.0, help="Minimum face-to-image area ratio. Skip smaller faces (default: 0.0).")
    return p.parse_args()


def main():
    args = parse_args()
    
    input_path = Path(args.input)
    out_dir = Path(args.out_dir)
    
    if not input_path.exists():
        print(f"Error: Input path does not exist: {input_path}")
        sys.exit(1)
        
    # Load cascades if cropping is enabled
    face_cascade = None
    eye_cascade = None
    if not args.no_crop:
        try:
            face_cascade_path = ensure_cascade('haarcascade_frontalface_default.xml')
            face_cascade = cv2.CascadeClassifier(face_cascade_path)
            
            # Load eye cascade for quality scoring
            try:
                eye_cascade_path = ensure_cascade('haarcascade_eye.xml')
                eye_cascade = cv2.CascadeClassifier(eye_cascade_path)
            except FileNotFoundError:
                print("Warning: Eye cascade not found; using face detection only.")
        except Exception as e:
            print(f"Error loading Haar Cascades: {e}")
            print("To run without face cropping, use the --no-crop option.")
            sys.exit(1)
            
    out_dir.mkdir(parents=True, exist_ok=True)
    
    supported_exts = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}
    
    if input_path.is_file():
        if input_path.suffix.lower() not in supported_exts:
            print(f"Error: Unsupported file format {input_path.suffix}")
            sys.exit(1)
        files_to_process = [input_path]
    else:
        files_to_process = sorted([
            p for p in input_path.iterdir()
            if p.is_file() and p.suffix.lower() in supported_exts
        ])
        
    if not files_to_process:
        print("No supported images found to process.")
        sys.exit(0)
        
    print(f"Found {len(files_to_process)} image(s) to process.")
    print("-" * 50)
    
    success_count = 0
    for file_path in files_to_process:
        if process_image(file_path, face_cascade, eye_cascade, out_dir, args):
            success_count += 1
        print()
            
    print("-" * 50)
    print(f"Finished processing. Successfully completed {success_count}/{len(files_to_process)} images.")


if __name__ == '__main__':
    main()
