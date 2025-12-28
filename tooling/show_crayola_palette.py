#!/usr/bin/env python3
"""Display Crayola palette colors."""

from color_tools.palette import load_palette

p = load_palette('crayola')

print('Crayola Crayon Colors Palette')
print('=' * 60)
print(f'\nTotal: {len(p.records)} colors\n')

print('First 30 colors:')
print('-' * 60)
for i, c in enumerate(p.records[:30], 1):
    print(f'{i:3}. {c.name:30} {c.hex:10} RGB{c.rgb}')

print('\n...')
print(f'\nLast 10 colors:')
print('-' * 60)
for i, c in enumerate(p.records[-10:], len(p.records)-9):
    print(f'{i:3}. {c.name:30} {c.hex:10} RGB{c.rgb}')
