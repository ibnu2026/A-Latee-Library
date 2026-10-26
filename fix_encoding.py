#!/usr/bin/env python3
"""Fix encoding issues in LibraryDekstopApp.py"""

with open('LibraryDekstopApp.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace all occurrences
old_pattern = "with open(log_file, 'a') as f:"
new_pattern = "with open(log_file, 'a', encoding='utf-8') as f:"

count = content.count(old_pattern)
content = content.replace(old_pattern, new_pattern)

with open('LibraryDekstopApp.py', 'w', encoding='utf-8') as f:
    f.write(content)

print(f'✓ Fixed {count} log file encoding issues')
