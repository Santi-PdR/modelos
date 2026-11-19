#!/usr/bin/env python3
"""Assemble only katana sources/assets for an isolated Forge test build."""
import json, shutil
from pathlib import Path
root=Path(__file__).resolve().parents[2]
stage=root/'build-katana-input'
if stage.exists(): shutil.rmtree(stage)
shutil.copytree(root/'katana_stain/forge/java', stage/'java')
shutil.copytree(root/'katana_stain/forge/resources', stage/'resources')
source = root/'src/main/java/com/capatest/katana'
target = stage/'java/com/stainkatana/katana'
target.mkdir(parents=True, exist_ok=True)
for path in source.glob('*.java'):
 text=path.read_text(encoding='utf8')
 text=text.replace('com.capatest.katana','com.stainkatana.katana')
 text=text.replace('import com.capatest.CapaTestMod;', 'import com.stainkatana.StainKatanaMod;')
 text=text.replace('CapaTestMod.MOD_ID','StainKatanaMod.MOD_ID')
 text=text.replace('item.capatest.katana_stain', 'item.stainkatana.katana_stain')
 (target/path.name).write_text(text,encoding='utf8')
src=root/'src/main/resources/assets/capatest'; dst=stage/'resources/assets/stainkatana'
paths=['animations/item/katana_stain.animation.json','geo/item/katana_stain.geo.json',
       'models/item/katana_stain.json','textures/item/katana_stain.png','textures/item/katana_stain_icon.png']
for name in paths:
 p=dst/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src/name,p)
for lang in ('es_es','en_us'):
 data=json.loads((src/'lang'/f'{lang}.json').read_text(encoding='utf8'))
 data={k.replace('capatest','stainkatana'):v for k,v in data.items() if k.startswith('item.capatest.katana_stain') or k=='itemGroup.capatest.legados'}
 p=dst/'lang'/f'{lang}.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
print('Solo katana preparada en',stage.relative_to(root))
