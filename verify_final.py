#!/usr/bin/env python
"""Final verification for all changes"""

print('='*60)
print('LATEE LIBRARY - FINAL VERIFICATION')
print('='*60)

# 1. Check user admin
print('\n[1] ADMIN USER CHECK')
try:
    from LibraryDekstopApp import Database
    db = Database()
    users = db.list_users()
    admin_exists = any(u[1] == 'admin' for u in users)
    if admin_exists:
        print('  OK - User "admin" exists')
    else:
        print('  WARNING - User "admin" not found')
    print(f'  Total Users: {len(users)}/14')
    for user in users:
        print(f'    * {user[1]:15} ({user[2]})')
except Exception as e:
    print(f'  ERROR: {e}')

# 2. Check navbar re-added
print('\n[2] NAVBAR CHECK')
with open('modern_ui_setup.py', 'r', encoding='utf-8') as f:
    content = f.read()
    if 'NavbarWidget' in content and 'navbar_widget' in content:
        print('  OK - Navbar re-added to top')
    else:
        print('  WARNING - Navbar code not found')

# 3. Check sidebar still present
print('\n[3] SIDEBAR CHECK')
with open('modern_ui_setup.py', 'r', encoding='utf-8') as f:
    content = f.read()
    if 'SidebarNavigation' in content:
        print('  OK - Sidebar navigation present')
    else:
        print('  WARNING - Sidebar code not found')

# 4. Check code imports properly
print('\n[4] IMPORT CHECK')
try:
    from LibraryDekstopApp import *
    print('  OK - All imports successful')
except Exception as e:
    print(f'  ERROR: {e}')

print('\n' + '='*60)
print('VERIFICATION COMPLETE')
print('='*60)
