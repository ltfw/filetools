# Face cropper and resizer

This repository contains tools to crop faces from images and resize them to below 1MB.

## Python Tools

### 1. Crop and Resize (`crop_resize.py`)

This tool detects faces, crops them, compresses/resizes the image to be under 1MB, and renames the output file to the format `Firstname+Lastname_ID.jpg` by parsing the input filename or accepting CLI overrides.

#### Usage

```bash
python crop_resize.py <input_path> [options]
```

Or using the virtual environment:

```bash
./venv/bin/python crop_resize.py <input_path> [options]
```

#### Naming Logic

The tool automatically extracts names and IDs from input filenames:
- `0812170098 Susantoko.JPG` -> `Susantoko_0812170098.jpg`
- `1005240708 Muhammad Anwar.JPG` -> `Muhammad+Anwar_1005240708.jpg`
- `0804180215_Noky Anresa Ferdiyanta.JPG` -> `Noky Anresa+Ferdiyanta_0804180215.jpg`

#### Key Options

- `-o`, `--out-dir`: Destination directory (default: `output/`).
- `--no-crop`: Skip face cropping and resize the full image instead.
- `--max-size`: Maximum file size in MB (default: `1.0`).
- `--name`: Explicit name to use (bypasses filename parsing).
- `--id`: Explicit ID/NIK to use (bypasses filename parsing).
- `--annotate`: Save an annotated copy with green face bounding boxes under `output/annotated/`.
- `--no-fallback`: Disable fallback to resizing full image if face crop fails.

---

### 2. Original Face Cropper (`crop.py`)

Crops faces from images placed in `photos/` and writes them to `cropped/`.

```bash
python crop.py [options]
```

---

## Installation

1. Create a virtual environment:
   ```bash
   python -m venv venv
   ```
2. Activate it and install dependencies:
   ```bash
   ./venv/bin/pip install -r requirements.txt
   ```

