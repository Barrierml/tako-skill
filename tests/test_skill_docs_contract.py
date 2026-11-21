import hashlib
import os
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def has_valid_mp3_header(data: bytes) -> bool:
    if data.startswith(b'ID3'):
        return True
    return len(data) >= 2 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0


class SkillDocsContract(unittest.TestCase):
    def test_bingtang_audio_assets_exist_valid_and_distinct(self):
        samples = [
            ROOT / 'assets/audio/voice-bingtang-warm.mp3',
            ROOT / 'assets/audio/voice-bingtang-lively.mp3',
            ROOT / 'assets/audio/voice-bingtang-radio.mp3',
        ]
        digests = set()
        for path in samples:
            self.assertTrue(path.is_file(), f'missing audio asset: {path}')
            data = path.read_bytes()
            self.assertGreater(
                len(data),
                20 * 1024,
                f'{path.name} expected > 20KB, got {len(data)} bytes',
            )
            self.assertTrue(
                has_valid_mp3_header(data),
                f'{path.name} missing ID3/MPEG frame header',
            )
            digests.add(hashlib.sha256(data).hexdigest())
        self.assertEqual(len(digests), 3, 'bingtang audio samples must have distinct SHA256 digests')

    def test_references_and_executable_scripts_exist(self):
        for rel in ('references/audio.md', 'references/consult.md'):
            path = ROOT / rel
            self.assertTrue(path.is_file(), f'missing reference doc: {rel}')
        for rel in ('scripts/tako-audio.sh', 'scripts/tako-consult.sh'):
            path = ROOT / rel
            self.assertTrue(path.is_file(), f'missing helper script: {rel}')
            self.assertTrue(
                os.access(path, os.X_OK),
                f'helper script must be executable: {rel}',
            )

    def test_skill_and_readme_cover_five_capabilities_without_legacy_bans_or_old_repo(self):
        required_scripts = (
            'tako-image.sh',
            'tako-video.sh',
            'tako-audio.sh',
            'tako-search.sh',
            'tako-consult.sh',
            'tako-systemone.sh',
        )
        banned_phrases = (
            'not for ordinary chat or speech',
            'do not use this skill for speech',
            '当前 skill 不提供语音',
        )
        historical_markers = ('曾用名', '重定向', 'redirect', 'previous', 'formerly', 'deprecated')

        for rel in ('SKILL.md', 'README.md'):
            content = (ROOT / rel).read_text(encoding='utf-8')
            lower = content.lower()
            for script in required_scripts:
                self.assertTrue(script in content, f'{rel} missing capability script {script}')
            for phrase in banned_phrases:
                self.assertFalse(phrase in lower, f'{rel} still contains outdated ban: {phrase}')
            for idx, line in enumerate(content.splitlines(), start=1):
                if 'Barrierml/tako-skill' in line:
                    line_lower = line.lower()
                    self.assertTrue(
                        any(marker in line_lower for marker in historical_markers),
                        f'{rel}:{idx} contains old repo Barrierml/tako-skill outside historical note: {line}',
                    )
                    self.assertNotRegex(
                        line,
                        r'(npx\s+skills\s+add|git\s+clone)\b.*Barrierml/tako-skill',
                        f'{rel}:{idx} install command must use tako-dev/tako-skill',
                    )

        readme = (ROOT / 'README.md').read_text(encoding='utf-8')
        self.assertTrue(
            re.search(r'npx\s+skills\s+add\s+tako-dev/tako-skill\b', readme),
            'README.md install command must reference tako-dev/tako-skill',
        )


if __name__ == '__main__':
    unittest.main()
