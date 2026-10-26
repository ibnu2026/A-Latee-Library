#!/usr/bin/env python
"""Final verification script for all modifications"""

import re
import sys

print('='*60)
print('LATEE LIBRARY - FINAL VERIFICATION')
print('='*60)

# 1. Check emoji removal
print('\n[1] EMOJI REMOVAL CHECK')
with open('LibraryDekstopApp.py', 'r', encoding='utf-8') as f:
    content = f.read()
    emoji_pattern = r'[\U0001F300-\U0001F9FF]|[\u2600-\u27BF]|[\u2300-\u23FF]'
    emojis = re.findall(emoji_pattern, content)
    if emojis:
        print(f'  WARNING: Found {len(emojis)} emoji(s)')
    else:
        print('  OK - All emojis removed from LibraryDekstopApp.py')

# 2. Check sidebar modifications
print('\n[2] SIDEBAR MODIFICATIONS')
with open('sidebar_navigation.py', 'r', encoding='utf-8') as f:
    sidebar_content = f.read()
    if 'logo_widget' not in sidebar_content and 'logo_title' not in sidebar_content:
        print('  OK - Header/logo section removed from sidebar')
    else:
        print('  WARNING - Header section still present')

# 3. Check user limit
print('\n[3] USER LIMIT CHECK')
with open('LibraryDekstopApp.py', 'r', encoding='utf-8') as f:
    content = f.read()
    if 'existing_count >= 14' in content and 'maks 14 akun' in content:
        print('  OK - User limit changed to 14')
    else:
        print('  WARNING - User limit not updated correctly')

# 4. Check user amin
print('\n[4] DATABASE CHECK')
try:
    from LibraryDekstopApp import Database
    db = Database()
    users = db.list_users()
    print(f'  Total Users: {len(users)}/14')
    amin_exists = any(u[1] == 'amin' for u in users)
    if amin_exists:
        print('  OK - User "amin" exists')
    else:
        print('  WARNING - User "amin" not found')
    for user in users:
        print(f'    * {user[1]:15} ({user[2]})')
except Exception as e:
    print(f'  ERROR - Database error: {e}')

# 5. Check header removal
print('\n[5] HEADER REMOVAL CHECK')
with open('modern_ui_setup.py', 'r', encoding='utf-8') as f:
    content = f.read()
    if 'header_widget' not in content and 'HeaderWidget' not in content:
        print('  OK - Header widget completely removed')
    else:
        print('  WARNING - Header widget code still present')

print('\n' + '='*60)
print('VERIFICATION COMPLETE')
print('='*60)
