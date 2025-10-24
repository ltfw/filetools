# Face cropper

This small script crops faces from images placed in the `photos/` folder and writes the results to a `cropped/` folder.

Quick start

1. Create/put images into `photos/` (jpg/png/etc).
2. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

3. Run:

```bash
python crop.py
```

Advanced options

- Require eyes inside detected faces to reduce false positives:

```bash
python crop.py --verify-eyes
```

- Skip tiny detections by minimum area (ratio of image area). Example: skip faces smaller than 1% of the image area:

```bash
python crop.py --min-area 0.01
```

- Save annotated copies with rectangles:

```bash
python crop.py --annotate
```

Notes

- The script uses OpenCV's Haar cascade bundled with `opencv-python`.
- If no faces are detected for an image you'll see `0 face(s)` for that file.
- Output files are named like `originalname_face1.jpg`.
