"""Перевірка внутрішніх посилань сайту перед публікацією.

Проходить усі HTML- і CSS-файли сховища й шукає:
- посилання на сторінки, яких немає;
- зображення, стилі й скрипти, яких немає;
- якорі (#розділ), яких немає на сторінці;
- шляхи з косою рискою на початку: на GitHub Pages сайт живе в підпапці, тож вони ведуть не туди;
- різницю у великих і малих літерах: GitHub Pages їх розрізняє, а Windows ні.

Зовнішні сайти не перевіряються: скрипт нікуди не звертається через інтернет.
Використовує лише стандартну бібліотеку Python, нічого не встановлює.
Код виходу: 0 — помилок немає, 1 — є помилки (тоді перевірка в GitHub стає червоною).
"""
import os
import re
import sys
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit

SKIP_DIRS = {'.git', '.github', '.claude', 'node_modules'}
ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else '.')


class Page(HTMLParser):
    """Збирає з HTML усі адреси (href, src, srcset) і всі якорі (id)."""

    def __init__(self):
        super().__init__()
        self.refs = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get('id'):
            self.ids.add(a['id'])
        if tag == 'a' and a.get('name'):
            self.ids.add(a['name'])
        for attr in ('href', 'src', 'poster'):
            if a.get(attr):
                self.refs.append((attr, a[attr], self.getpos()[0]))
        if a.get('srcset'):
            for part in a['srcset'].split(','):
                url = part.strip().split(' ')[0]
                if url:
                    self.refs.append(('srcset', url, self.getpos()[0]))


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def exists_exact(path):
    """Чи є файл саме з таким написанням великих і малих літер."""
    rel = os.path.relpath(path, ROOT)
    if rel.startswith('..'):
        return False
    current = ROOT
    for part in rel.split(os.sep):
        if part in ('', '.'):
            continue
        if not os.path.isdir(current) or part not in os.listdir(current):
            return False
        current = os.path.join(current, part)
    return True


ids_cache = {}


def ids_of(path):
    if path not in ids_cache:
        page = Page()
        page.feed(read(path))
        ids_cache[path] = page.ids
    return ids_cache[path]


def refs_of(path):
    text = read(path)
    if path.endswith('.html'):
        page = Page()
        page.feed(text)
        return page.refs
    refs = []  # CSS: url(...) і @import
    for m in re.finditer(r'url\(\s*(["\']?)([^)"\']+)\1\s*\)', text):
        refs.append(('url()', m.group(2), text[:m.start()].count('\n') + 1))
    for m in re.finditer(r'@import\s+["\']([^"\']+)', text):
        refs.append(('@import', m.group(1), text[:m.start()].count('\n') + 1))
    return refs


def check(path):
    errors = []
    for attr, url, line in refs_of(path):
        url = url.strip()
        parts = urlsplit(url)
        if url.startswith('#') and len(url) == 1:
            continue  # заглушка href="#": свідомо порожнє посилання
        if parts.scheme or url.startswith('//'):
            continue  # зовнішні адреси, tel:, mailto:, data: — не перевіряємо
        if url.startswith('/'):
            errors.append((line, url, 'шлях із косою рискою на початку: на GitHub Pages він веде не туди'))
            continue
        target = os.path.normpath(os.path.join(os.path.dirname(path), unquote(parts.path))) if parts.path else path
        if os.path.isdir(target):
            target = os.path.join(target, 'index.html')
        if not exists_exact(target):
            note = ' (є файл з іншими великими/малими літерами)' if os.path.exists(target) else ''
            errors.append((line, url, 'файлу немає' + note))
            continue
        if parts.fragment and target.endswith('.html') and unquote(parts.fragment) not in ids_of(target):
            errors.append((line, url, f'на сторінці немає розділу #{parts.fragment}'))
    return errors


def main():
    sys.stdout.reconfigure(encoding='utf-8')  # щоб українські літери читалися в будь-якій консолі
    files = []
    for folder, dirs, names in os.walk(ROOT):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        files += [os.path.join(folder, n) for n in sorted(names) if n.endswith(('.html', '.css'))]

    found = []
    for path in files:
        rel = os.path.relpath(path, ROOT).replace(os.sep, '/')
        for line, url, why in check(path):
            found.append((rel, line, url, why))

    pages = sum(f.endswith('.html') for f in files)
    print(f'Перевірено файлів: {len(files)} (HTML-сторінок: {pages}).')

    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if not found:
        print('Битих внутрішніх посилань не знайдено.')
        if summary:
            with open(summary, 'a', encoding='utf-8') as f:
                f.write(f'### ✅ Посилання в порядку\nПеревірено файлів: {len(files)}.\n')
        return 0

    print(f'Знайдено помилок: {len(found)}')
    for rel, line, url, why in found:
        print(f'  {rel}, рядок {line}: {url} — {why}')
        if os.environ.get('GITHUB_ACTIONS'):
            # Позначка, яку GitHub показує прямо біля рядка у вкладці «Files changed»
            print(f'::error file={rel},line={line}::{url} — {why}')
    if summary:
        with open(summary, 'a', encoding='utf-8') as f:
            f.write(f'### ❌ Знайдено битих посилань: {len(found)}\n\n| Файл | Рядок | Посилання | Що не так |\n|---|---|---|---|\n')
            for rel, line, url, why in found:
                f.write(f'| `{rel}` | {line} | `{url}` | {why} |\n')
    return 1


if __name__ == '__main__':
    sys.exit(main())
