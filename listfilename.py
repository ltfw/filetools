#!/usr/bin/env python3
"""List and rename files in the cropped/ directory using employee data.

Usage: python listfilename.py
"""

import os
import re
import shutil
import zipfile
from datetime import datetime
from pathlib import Path


def load_employee_data():
    """Load employee data from employees.txt file."""
    script_dir = Path(__file__).resolve().parent
    employees_file = script_dir / 'employees.txt'
    
    if not employees_file.exists():
        print(f"Employee data file not found: {employees_file}")
        return {}
    
    employees = {}
    
    try:
        with open(employees_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # Skip header line
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
                
            parts = line.split(';')
            if len(parts) >= 3:
                nama_lengkap = parts[0].strip()
                nik = parts[1].strip()
                departemen = parts[2].strip()
                
                # Create multiple lookup keys for better matching
                employees[nama_lengkap.upper()] = {
                    'nama_lengkap': nama_lengkap,
                    'nik': nik,
                    'departemen': departemen
                }
                
                # Also add partial name matches
                name_parts = nama_lengkap.split()
                for part in name_parts:
                    if len(part) > 2:  # Only use parts longer than 2 characters
                        employees[part.upper()] = {
                            'nama_lengkap': nama_lengkap,
                            'nik': nik,
                            'departemen': departemen
                        }
    
    except Exception as e:
        print(f"Error loading employee data: {e}")
        return {}
    
    return employees


def find_employee_match(filename, employees):
    """Find matching employee for a filename."""
    # Remove _face.jpg suffix and clean the name
    clean_name = filename.replace('_face.jpg', '').replace('_ann.jpg', '')
    
    # Try exact match first
    if clean_name.upper() in employees:
        return employees[clean_name.upper()]
    
    # Try to match the first part of the filename (before any dash or hyphen)
    name_part = clean_name.split('-')[0].split('_')[0].strip()
    if name_part.upper() in employees:
        return employees[name_part.upper()]
    
    # Try partial matches with the first part
    name_parts = name_part.split()
    for part in name_parts:
        if len(part) > 2 and part.upper() in employees:
            return employees[part.upper()]
    
    # Try fuzzy matching (simple approach) - but be more strict
    for emp_key, emp_data in employees.items():
        if len(emp_key) > 3:  # Only check longer names
            # Check if the first part of filename matches the beginning of employee name
            for filename_part in name_parts:
                if len(filename_part) > 3:
                    # More strict matching - check if filename part is at the start of employee name
                    if emp_key.startswith(filename_part.upper()):
                        return emp_data
    
    return None


def rename_files_with_employee_data():
    """Rename files in cropped/ folder using employee data."""
    script_dir = Path(__file__).resolve().parent
    cropped_dir = script_dir / 'cropped'
    rename_dir = script_dir / 'rename'

    if not cropped_dir.exists():
        print(f"Cropped directory not found: {cropped_dir}")
        return

    # Ensure rename directory exists
    rename_dir.mkdir(exist_ok=True)

    # Load employee data
    employees = load_employee_data()
    if not employees:
        print("No employee data loaded.")
        return

    print(f"Loaded {len(set(emp['nama_lengkap'] for emp in employees.values()))} unique employees")
    print("=" * 60)

    # Process files
    files = sorted(cropped_dir.iterdir())
    copied_count = 0
    unmatched_files = []

    for file_path in files:
        if file_path.is_file() and file_path.name.endswith('_face.jpg'):
            # Find matching employee
            employee = find_employee_match(file_path.name, employees)

            if employee:
                # Create new filename based on name length
                full_name = employee['nama_lengkap']
                name_parts = full_name.split()

                if len(name_parts) >= 3:
                    # For names with more than 3 words: firstName+middleName lastName_nik
                    first_middle = ' '.join(name_parts[:-1])  # All parts except last
                    last_name = name_parts[-1]  # Last part
                    new_name = f"{first_middle}+{last_name}_{employee['nik']}.jpg"
                else:
                    # For names with 3 words or less: firstName+lastName_nik
                    new_name = f"{full_name.replace(' ', '+')}_{employee['nik']}.jpg"

                new_path = rename_dir / new_name

                # Check if target file already exists
                if new_path.exists():
                    print(f"WARNING: Target file already exists: {new_name}")
                    continue

                try:
                    # Copy file to rename directory preserving metadata
                    shutil.copy2(file_path, new_path)
                    print(f"✓ Copied: {file_path.name}")
                    print(f"  → {new_name}")
                    print(f"  Employee: {employee['nama_lengkap']} ({employee['departemen']})")
                    print()
                    copied_count += 1
                except Exception as e:
                    print(f"✗ Error copying {file_path.name}: {e}")
            else:
                unmatched_files.append(file_path.name)
                print(f"? No match found for: {file_path.name}")

    print("=" * 60)
    print(f"Successfully copied: {copied_count} files")
    print(f"Unmatched files: {len(unmatched_files)}")

    if unmatched_files:
        print("\nUnmatched files:")
        for filename in unmatched_files:
            print(f"  - {filename}")


def preview_renames():
    """Preview what files would be renamed without actually renaming."""
    script_dir = Path(__file__).resolve().parent
    cropped_dir = script_dir / 'cropped'
    
    if not cropped_dir.exists():
        print(f"Cropped directory not found: {cropped_dir}")
        return
    
    # Load employee data
    employees = load_employee_data()
    if not employees:
        print("No employee data loaded.")
        return
    
    print("PREVIEW: Files that would be renamed")
    print("=" * 60)
    
    # Process files
    files = sorted(cropped_dir.iterdir())
    match_count = 0
    unmatched_files = []
    
    for file_path in files:
        if file_path.is_file() and file_path.name.endswith('_face.jpg'):
            # Find matching employee
            employee = find_employee_match(file_path.name, employees)
            
            if employee:
                # Create new filename
                full_name = employee['nama_lengkap']
                name_parts = full_name.split()
                
                if len(name_parts) >= 3:
                    # For names with more than 3 words: firstName+middleName lastName_nik
                    first_middle = ' '.join(name_parts[:-1])  # All parts except last
                    last_name = name_parts[-1]  # Last part
                    new_name = f"{first_middle}+{last_name}_{employee['nik']}.jpg"
                else:
                    # For names with 3 words or less: firstName+lastName_nik
                    new_name = f"{full_name.replace(' ', '+')}_{employee['nik']}.jpg"
                
                print(f"✓ {file_path.name}")
                print(f"  → {new_name}")
                print(f"  Employee: {employee['nama_lengkap']} ({employee['departemen']})")
                print()
                match_count += 1
            else:
                unmatched_files.append(file_path.name)
                print(f"? No match: {file_path.name}")
    
    print("=" * 60)
    print(f"Files that would be renamed: {match_count}")
    print(f"Unmatched files: {len(unmatched_files)}")


def backup_cropped_photos():
    """Create a backup of all photos in the cropped/ directory."""
    script_dir = Path(__file__).resolve().parent
    cropped_dir = script_dir / 'cropped'
    backup_dir = script_dir / 'backups'
    
    if not cropped_dir.exists():
        print(f"Cropped directory not found: {cropped_dir}")
        return
    
    # Create backup directory if it doesn't exist
    backup_dir.mkdir(exist_ok=True)
    
    # Generate timestamp for backup filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"cropped_photos_backup_{timestamp}.zip"
    backup_path = backup_dir / backup_filename
    
    # Get all image files in cropped directory
    image_files = []
    for file_path in cropped_dir.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']:
            image_files.append(file_path)
    
    if not image_files:
        print("No image files found in cropped directory.")
        return
    
    print(f"Creating backup of {len(image_files)} photos...")
    print(f"Backup file: {backup_path}")
    print("-" * 50)
    
    try:
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
            total_size = 0
            for i, file_path in enumerate(image_files, 1):
                # Add file to zip with relative path
                arcname = file_path.name
                zipf.write(file_path, arcname)
                
                # Calculate file size
                file_size = file_path.stat().st_size
                total_size += file_size
                
                print(f"{i:3d}. {file_path.name} ({file_size / 1024:.1f} KB)")
        
        # Get backup file size
        backup_size = backup_path.stat().st_size
        compression_ratio = (1 - backup_size / total_size) * 100 if total_size > 0 else 0
        
        print("-" * 50)
        print(f"✓ Backup created successfully!")
        print(f"  Original size: {total_size / 1024 / 1024:.2f} MB")
        print(f"  Backup size: {backup_size / 1024 / 1024:.2f} MB")
        print(f"  Compression: {compression_ratio:.1f}%")
        print(f"  Files backed up: {len(image_files)}")
        print(f"  Backup location: {backup_path}")
        
    except Exception as e:
        print(f"✗ Error creating backup: {e}")
        # Clean up failed backup file
        if backup_path.exists():
            backup_path.unlink()


def list_cropped_files():
    """List all files in the cropped/ directory."""
    script_dir = Path(__file__).resolve().parent
    cropped_dir = script_dir / 'cropped'
    
    if not cropped_dir.exists():
        print(f"Cropped directory not found: {cropped_dir}")
        return
    
    print(f"Files in {cropped_dir}:")
    print("-" * 50)
    
    # Get all files in the directory
    files = sorted(cropped_dir.iterdir())
    
    if not files:
        print("No files found in cropped directory.")
        return
    
    # List all files
    for i, file_path in enumerate(files, 1):
        if file_path.is_file():
            # Get file size
            file_size = file_path.stat().st_size
            size_kb = file_size / 1024
            
            print(f"{i:3d}. {file_path.name} ({size_kb:.1f} KB)")
    
    print("-" * 50)
    print(f"Total files: {len([f for f in files if f.is_file()])}")


def main():
    """Main function with menu options."""
    print("CROPPED FILES MANAGER")
    print("=" * 50)
    print("1. List all files")
    print("2. Preview renames (using employee data)")
    print("3. Rename files (using employee data)")
    print("4. Show employee data stats")
    print("5. Backup cropped photos")
    print("=" * 50)
    
    try:
        choice = input("Enter your choice (1-5): ").strip()
        
        if choice == '1':
            list_cropped_files()
        elif choice == '2':
            preview_renames()
        elif choice == '3':
            confirm = input("Are you sure you want to rename files? (y/N): ").strip().lower()
            if confirm == 'y':
                rename_files_with_employee_data()
            else:
                print("Operation cancelled.")
        elif choice == '4':
            employees = load_employee_data()
            if employees:
                unique_employees = set(emp['nama_lengkap'] for emp in employees.values())
                departments = set(emp['departemen'] for emp in employees.values())
                print(f"Total unique employees: {len(unique_employees)}")
                print(f"Total departments: {len(departments)}")
                print("\nDepartments:")
                for dept in sorted(departments):
                    count = len([emp for emp in employees.values() if emp['departemen'] == dept])
                    print(f"  - {dept}: {count} employees")
            else:
                print("No employee data loaded.")
        elif choice == '5':
            backup_cropped_photos()
        else:
            print("Invalid choice. Running default (list files)...")
            list_cropped_files()
            
    except KeyboardInterrupt:
        print("\nOperation cancelled.")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == '__main__':
    main()
