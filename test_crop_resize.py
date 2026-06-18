#!/usr/bin/env python3
import sys
from pathlib import Path

from crop_resize import parse_filename, format_employee_name

def test_parsing():
    test_cases = [
        ("0812170098 Susantoko.JPG", "Susantoko", "0812170098"),
        ("1005240708 Muhammad Anwar.JPG", "Muhammad Anwar", "1005240708"),
        ("0804180215_Noky Anresa Ferdiyanta.JPG", "Noky Anresa Ferdiyanta", "0804180215"),
        ("Ainur Rofik Hidayat-Utility.JPG", "Ainur Rofik Hidayat", None),
        ("0804180215_Noky Anresa Ferdiyanta-Utility.JPG", "Noky Anresa Ferdiyanta", "0804180215"),
    ]
    
    print("Testing Filename Parsing:")
    print("-" * 50)
    all_passed = True
    for filename, expected_name, expected_id in test_cases:
        name, nik = parse_filename(filename)
        status = "PASS" if name == expected_name and nik == expected_id else "FAIL"
        if status == "FAIL":
            all_passed = False
        print(f"{filename} -> Name: '{name}' (Expected: '{expected_name}'), ID: '{nik}' (Expected: '{expected_id}') [{status}]")
        
    print("\nTesting Formatting:")
    print("-" * 50)
    format_cases = [
        ("Susantoko", "Susantoko"),
        ("Muhammad Anwar", "Muhammad+Anwar"),
        ("Noky Anresa Ferdiyanta", "Noky Anresa+Ferdiyanta"),
        ("Ainur Rofik Hidayat", "Ainur Rofik+Hidayat"),
        ("Zefanya Abinesar Dhanendra Putra", "Zefanya Abinesar Dhanendra+Putra"),
    ]
    for raw_name, expected_formatted in format_cases:
        formatted = format_employee_name(raw_name)
        status = "PASS" if formatted == expected_formatted else "FAIL"
        if status == "FAIL":
            all_passed = False
        print(f"'{raw_name}' -> '{formatted}' (Expected: '{expected_formatted}') [{status}]")
        
    if all_passed:
        print("\nALL TESTS PASSED!")
        sys.exit(0)
    else:
        print("\nSOME TESTS FAILED!")
        sys.exit(1)

if __name__ == '__main__':
    test_parsing()
