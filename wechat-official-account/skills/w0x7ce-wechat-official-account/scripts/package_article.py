"""Package reviewed Markdown and an HTML fragment; no conversion or cloud writes."""
import argparse
import base64
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import tempfile
from urllib.parse import unquote, urlsplit
import zipfile

MIME = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
        '.gif': 'image/gif', '.webp': 'image/webp'}
TEMPLATE = Path(__file__).resolve().parents[1] / 'assets/copy-page.html'


def local_image(source, value):
    url = urlsplit(value)
    name = unquote(url.path)
    relative = Path(name)
    if (url.scheme or url.netloc or url.query or url.fragment or '\\' in name
            or relative.is_absolute() or not relative.parts or relative.parts[0] != 'images'
            or '..' in relative.parts):
        raise ValueError('Images must use relative images/ paths: ' + value)
    target = source / relative
    if not target.resolve().is_relative_to(source.resolve()) or target.is_symlink():
        raise ValueError('Image escapes source: ' + value)
    if not target.is_file() or target.suffix.lower() not in MIME:
        raise ValueError('Missing or unsupported image: ' + value)
    return target


class Fragment(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=False)
        self.source, self.output, self.images = source, [], []

    def handle_starttag(self, tag, attrs):
        if tag in {'html', 'head', 'body', 'script', 'style', 'link', 'iframe', 'object',
                   'embed', 'form', 'input', 'button', 'h1', 'svg', 'video', 'audio', 'base', 'meta'}:
            raise ValueError('Unsupported element in body fragment: ' + tag)
        mapped = []
        for key, value in attrs:
            if key.lower().startswith('on') or key in {'srcset', 'background'}:
                raise ValueError('Interactive or external asset attribute: ' + key)
            if key == 'style' and re.search(r'url\s*\(|@import|expression\s*\(', value or '', re.I):
                raise ValueError('External or executable style')
            if key == 'href' and value and urlsplit(value.strip()).scheme.lower() not in {'', 'http', 'https', 'mailto'}:
                raise ValueError('Unsupported link scheme')
            if tag == 'img' and key == 'src':
                file = local_image(self.source, value or '')
                self.images.append(file.relative_to(self.source).as_posix())
                value = 'data:' + MIME[file.suffix.lower()] + ';base64,' + base64.b64encode(file.read_bytes()).decode('ascii')
            mapped.append(key if value is None else key + '="' + html.escape(value, quote=True) + '"')
        if tag == 'img' and not any(key == 'src' for key, _ in attrs):
            raise ValueError('Image has no source')
        self.output.append('<' + tag + (' ' + ' '.join(mapped) if mapped else '') + '>')

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        self.output.append('</' + tag + '>')

    def handle_data(self, data):
        self.output.append(data)

    def handle_entityref(self, name):
        self.output.append('&' + name + ';')

    def handle_charref(self, name):
        self.output.append('&#' + name + ';')


def package(source, cover, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists() or output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError('Use a new output directory outside the source tree.')
    if any(file.is_symlink() for file in source.rglob('*')):
        raise ValueError('Source cannot contain symlinks.')
    markdown = (source/'article.md').read_text(encoding='utf-8')
    first = markdown.splitlines()[0] if markdown else ''
    if not first.startswith('# ') or not first[2:].strip():
        raise ValueError('article.md must begin with an H1 title.')
    title = first[2:].strip()
    if not '\n'.join(markdown.splitlines()[1:]).strip():
        raise ValueError('Markdown body is empty.')
    for name in re.findall(r'!\[[^\]]*\]\(<?([^\s)>]+)>?(?:\s+"[^"]*")?\)', markdown):
        local_image(source, name)
    fragment = (source/'body.html').read_text(encoding='utf-8')
    if not fragment.strip():
        raise ValueError('HTML body is empty.')
    parser = Fragment(source)
    parser.feed(fragment)
    parser.close()
    cover_file = local_image(source, cover)
    # Validate everything before creating the final output.
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='wechat-package-', dir=output.parent) as temp:
        stage = Path(temp)/'delivery'
        portable = stage/'source'
        portable.mkdir(parents=True)
        for name in ['article.md', 'body.html', 'sources.json', 'README.md']:
            file = source/name
            if file.is_file():
                shutil.copy2(file, portable/name)
        shutil.copytree(source/'images', portable/'images')
        if not (portable/'README.md').exists():
            (portable/'README.md').write_text('# 文章來源\n\narticle.md 為正文來源；body.html 為同版正文排版片段。\nimages/ 保留原圖與封面，搬移請保留目錄結構。\n獨立 HTML 可複製正文與題目；平台不接受內嵌圖片時使用原圖補入。\n', encoding='utf-8')
        rendered = TEMPLATE.read_text(encoding='utf-8')
        rendered = rendered.replace('@@TITLE@@', html.escape(title)).replace('@@BODY@@', ''.join(parser.output))
        (stage/'article.html').write_text(rendered, encoding='utf-8')
        shutil.copy2(cover_file, stage/('cover'+cover_file.suffix.lower()))
        with zipfile.ZipFile(stage/'source.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
            for file in sorted(portable.rglob('*')):
                if file.is_file():
                    archive.write(file, 'source/'+file.relative_to(portable).as_posix())
        manifest = {'title': title, 'body_images': parser.images,
                    'scope': 'Local packaging only; content parity and platform persistence require separate checks.',
                    'sha256': {p.relative_to(stage).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in sorted(stage.rglob('*')) if p.is_file()}}
        (stage/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        stage.rename(output)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--cover', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = package(args.source, args.cover, args.output)
        print(json.dumps({'output': str(args.output.resolve()), 'title': result['title']}, ensure_ascii=False))
    except (ValueError, OSError) as exc:
        parser.exit(1, str(exc)+'\n')


if __name__ == '__main__':
    main()
