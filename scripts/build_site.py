# -*- coding: utf-8 -*-
"""Sklada gotowa strone: powloka z repo + profil klienta -> katalog wyjsciowy.

W repo nie ma zadnych danych przykladowych. Profil klienta (poza repo) wnosi
tresc (tresc.json), dane demo (data/, downloads/) i obrazek podgladu.
"""
import io, os, sys, json, shutil

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHELL = os.path.join(REPO, "web")

SZABLONY = (
    ("index.html", "<!--{{%s}}-->"),
    ("app.js",     "/*{{%s}}*/"),
    ("app.css",    "/*{{%s}}*/"),
)
WSPOLNE = ("assets", "vercel.json", ".vercelignore")
Z_PROFILU = ("data", "downloads", "share.jpg")


def read(p):
    return io.open(p, encoding="utf-8", newline="").read()


def write(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, "w", encoding="utf-8", newline="").write(s)


def render(tpl, slots, marker):
    """Marker zajmuje cala linie: pusty slot usuwa ja w calosci."""
    pre, post = marker.split("%s")
    out = []
    for line in tpl.split("\n"):
        st = line.strip()
        if st.startswith(pre) and st.endswith(post) and len(st) > len(pre) + len(post):
            key = st[len(pre):len(st) - len(post)]
            if key in slots:
                out.extend(slots[key])
                continue
            raise SystemExit("profil nie ma slotu '%s'" % key)
        out.append(line)
    return "\n".join(out)


def build(profile_dir, out_dir):
    tresc = json.loads(read(os.path.join(profile_dir, "tresc.json")))
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)
    for fname, marker in SZABLONY:
        tpl = read(os.path.join(SHELL, fname + ".tpl"))
        write(os.path.join(out_dir, fname), render(tpl, tresc[fname], marker))
    for item in WSPOLNE:
        src = os.path.join(SHELL, item)
        if os.path.exists(src):
            dst = os.path.join(out_dir, item)
            shutil.copytree(src, dst) if os.path.isdir(src) else shutil.copy2(src, dst)
    for item in Z_PROFILU:
        src = os.path.join(profile_dir, item)
        if os.path.exists(src):
            dst = os.path.join(out_dir, item)
            shutil.copytree(src, dst) if os.path.isdir(src) else shutil.copy2(src, dst)
    return out_dir


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit("uzycie: build_site.py <katalog-profilu> <katalog-wyjsciowy>")
    print("zbudowano:", build(sys.argv[1], sys.argv[2]))
