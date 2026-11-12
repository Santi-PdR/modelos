"""Standard-library resource regression tests. Does not replace gradlew build or game tests."""
import hashlib
import json
from pathlib import Path
import struct
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / 'src/main/resources'
ASSETS = RES / 'assets/holorelic'


class ResourcesTest(unittest.TestCase):
    def test_original_assets_are_byte_identical(self):
        pairs = {
            'export/geo/relic_hologram.geo.json': 'geo/relic_hologram.geo.json',
            'export/animations/relic_hologram.animation.json': 'animations/relic_hologram.animation.json',
            'textures/relic_hologram.png': 'textures/relic_hologram.png',
            'textures/relic_hologram_glowing.png': 'textures/relic_hologram_glowing.png',
        }
        with zipfile.ZipFile(ROOT / 'reliquia_holografica_v3.zip') as archive:
            for source, target in pairs.items():
                with self.subTest(asset=source):
                    self.assertEqual(hashlib.sha256(archive.read('reliquia_holografica/' + source)).digest(),
                                     hashlib.sha256((ASSETS / target).read_bytes()).digest())

    def test_all_json_is_valid(self):
        for path in RES.rglob('*'):
            if path.suffix in ('.json', '.mcmeta'):
                with self.subTest(path=path):
                    json.loads(path.read_text())

    def test_animation_and_bone_contract(self):
        geo = json.loads((ASSETS / 'geo/relic_hologram.geo.json').read_text())
        model = geo['minecraft:geometry'][0]
        self.assertEqual(model['description']['identifier'], 'geometry.relic_hologram')
        bones = {bone['name'] for bone in model['bones']}
        for name in ['relic_root', 'core', 'shock_ring', 'flash', 'ring_tilt_5', 'ring_tilt_6']:
            self.assertIn(name, bones)
        for index in range(1, 9):
            self.assertIn(f'drift_{index:02}', bones)
        animations = json.loads((ASSETS / 'animations/relic_hologram.animation.json').read_text())['animations']
        expected = {'idle': 12, 'idle_dormant': 6, 'activation': 3,
                    'deactivation': 2.2, 'energy_pulse': 2.4, 'glitch': 1}
        for name, duration in expected.items():
            anim = animations['animation.relic.' + name]
            self.assertEqual(anim['animation_length'], duration)
            self.assertEqual(anim['bones']['shock_ring']['scale']['0.0'], [0, 0, 0])
            self.assertEqual(anim['bones']['flash']['scale']['0.0'], [0, 0, 0])
            self.assertTrue(set(anim['bones']).issubset(bones))

    def test_curios_datapack(self):
        slot = json.loads((RES / 'data/holorelic/curios/slots/relic.json').read_text())
        self.assertEqual(slot['size'], 1)
        self.assertEqual(slot['operation'], 'SET')
        entities = json.loads((RES / 'data/holorelic/curios/entities/player.json').read_text())
        self.assertEqual(entities['slots'], ['relic'])
        tag = json.loads((RES / 'data/curios/tags/items/relic.json').read_text())
        self.assertEqual(tag['values'], ['holorelic:holographic_core'])

    def test_png_dimensions_and_lang_parity(self):
        for path, dimension in [('textures/item/holographic_core.png', 16),
                                ('textures/relic_hologram.png', 64),
                                ('textures/relic_hologram_glowing.png', 64)]:
            data = (ASSETS / path).read_bytes()
            self.assertEqual(data[:8], b'\x89PNG\r\n\x1a\n')
            self.assertEqual(struct.unpack('>II', data[16:24]), (dimension, dimension))
        en = json.loads((ASSETS / 'lang/en_us.json').read_text())
        es = json.loads((ASSETS / 'lang/es_es.json').read_text())
        self.assertEqual(set(en), set(es))

    def test_wrapper_jar_is_valid(self):
        with zipfile.ZipFile(ROOT / 'gradle/wrapper/gradle-wrapper.jar') as jar:
            self.assertIn('org/gradle/wrapper/GradleWrapperMain.class', jar.namelist())


if __name__ == '__main__':
    unittest.main()
