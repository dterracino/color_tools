#!/usr/bin/env python3
"""Find filaments with + in type or finish."""

import json
from pathlib import Path


def main():
    data = json.load(open('color_tools/data/filaments.json'))
    
    plus_finish = [f for f in data if f.get('finish') and '+' in f.get('finish')]
    plus_type = [f for f in data if '+' in f.get('type', '')]
    
    print(f"Filaments with + in finish: {len(plus_finish)}")
    print(f"Filaments with + in type: {len(plus_type)}")
    
    if plus_finish:
        print("\nFinish samples:")
        import pprint
        pprint.pprint(plus_finish[:5], width=120)
    
    if plus_type:
        print("\nType samples:")
        import pprint
        pprint.pprint(plus_type[:5], width=120)


if __name__ == '__main__':
    main()
