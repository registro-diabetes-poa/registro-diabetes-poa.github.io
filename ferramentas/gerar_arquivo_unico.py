"""Gera o arquivo único do site (todas as páginas, CSS e imagens embutidos) para enviar a colegas.

Uso, rodando de dentro da pasta do site:
    python ferramentas/gerar_arquivo_unico.py . site-RPDM-PA.html

Navegação no arquivo gerado: âncoras (#sobre, #dados...) + CSS :target/:has, sem JavaScript.
O arquivo gerado NÃO vai para o GitHub (está no .gitignore).
"""
import re, sys, base64, pathlib

SITE = pathlib.Path(sys.argv[1])
OUT = pathlib.Path(sys.argv[2])
order = ["index", "sobre", "dados", "metodologia", "publicacoes", "transparencia", "equipe", "contato"]
sec_id = {"index": "inicio"}  # demais: id da seção = nome do arquivo

def sid(name): return sec_id.get(name, name)

sections = []
for name in order:
    h = (SITE / f"{name}.html").read_text(encoding="utf-8")
    m = re.search(r'<main class="main">\s*(<section id="([\w-]+)">.*</section>)\s*</main>', h, re.S)
    assert m and m.group(2) == sid(name), name
    sections.append(m.group(1))
body = "\n\n".join(sections)

idx = (SITE / "index.html").read_text(encoding="utf-8")
nav = re.search(r'(<nav id="topnav">.*?</nav>)', idx, re.S).group(1)
nav = re.sub(r' class="active" aria-current="page"', "", nav)
footer = re.search(r"(<footer>.*?</footer>)", idx, re.S).group(1)

doc = nav + "\n\n<main class=\"main\">\n\n" + body + "\n\n</main>\n\n" + footer

# links entre páginas -> âncoras internas
def fix_href(m):
    href = m.group(1)
    page, _, frag = href.partition("#")
    if page.endswith(".html") and page[:-5] in order:
        return 'href="#%s"' % (frag or sid(page[:-5]))
    return m.group(0)
doc = re.sub(r'href="([^"]+)"', fix_href, doc)

# imagens embutidas (no HTML e no CSS)
def data_uri(path):
    mime = "image/jpeg" if path.endswith((".jpg", ".jpeg")) else "image/png"
    return f"data:{mime};base64," + base64.b64encode((SITE / path).read_bytes()).decode()
for img in set(re.findall(r'src="(assets/[^"]+)"', doc)):
    doc = doc.replace(f'src="{img}"', f'src="{data_uri(img)}"')

css = (SITE / "style.css").read_text(encoding="utf-8")
for img in set(re.findall(r'url\("(assets/[^"]+)"\)', css)):
    css = css.replace(f'url("{img}")', f'url("{data_uri(img)}")')
ids = [sid(n) for n in order]
css += """
/* ARQUIVO ÚNICO: mostra uma seção por vez conforme a âncora da URL.
   Fica dentro de @supports: em navegadores sem :has (Firefox antes de 121,
   Safari antes de 15.4) a regra inteira seria descartada e TODAS as páginas
   sumiriam. Sem suporte, as páginas aparecem uma embaixo da outra e o menu
   rola até a página clicada. */
main > section { scroll-margin-top: var(--nav-h); }
@supports selector(:has(a)) {
main > section { display: none; }
main > section:target,
main > section:has(:target),
main:not(:has(:target)) > #inicio { display: block; }
""" + ",\n".join(f'body:has(#{i}:target, #{i} :target) .nav-links a[href="#{i}"]' for i in ids) + \
""" { color: var(--blue-dark); background: #DDE8F5; font-weight: 600; }
body:not(:has(main :target)) .nav-links a[href="#inicio"] { color: var(--blue-dark); background: #DDE8F5; font-weight: 600; }
}
"""

head = re.search(r"<head>(.*?)</head>", idx, re.S).group(1)
head = head.replace('  <link rel="stylesheet" href="style.css" />\n', "")
html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>{head}  <style>
{css}  </style>
</head>
<body>

{doc}

</body>
</html>
"""
assert "assets/" not in html and ".html\"" not in html.split("<body>")[1]
OUT.write_text(html, encoding="utf-8")
print(OUT, len(html))
