#!/usr/bin/env python3
"""Remove emojis from LibraryDekstopApp.py"""

with open('LibraryDekstopApp.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace emojis with text
replacements = {
    '✓': '[OK]',
    '❌': '[ERROR]',
    '⚠️': '[WARN]',
    '📊': '[INFO]',
    '📋': '[DATA]',
    '📐': '[LAYOUT]',
    '🔍': '[CHECK]',
    '🎯': '[TARGET]',
    '📖': '[OPEN]',
    '📱': '[PHONE]',
    '🔧': '[TOOL]',
    '🏷️': '[TAG]',
    '💾': '[SAVE]',
    '✅': '[SUCCESS]',
    '🎨': '[ART]',
}

for emoji, text in replacements.items():
    content = content.replace(emoji, text)

with open('LibraryDekstopApp.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('[OK] Removed emojis from code')
