"""Check exported fixtures statistics"""
import json
from pathlib import Path

fixtures_file = Path(__file__).parent.parent / 'fixtures' / 'initial_data.json'

with open(fixtures_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

models = {}
for item in data:
    model = item['model']
    if model not in models:
        models[model] = []
    models[model].append(item)

print('Exported Data Statistics:')
print('=' * 50)
for model in sorted(models.keys()):
    count = len(models[model])
    print(f'{model}: {count} records')
print('=' * 50)
print(f'Total: {len(data)} records')
print(f'\nFile: {fixtures_file}')
print(f'Size: {fixtures_file.stat().st_size:,} bytes')






