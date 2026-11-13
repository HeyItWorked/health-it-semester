"""Build practice-week-N.html from the "Where they fit" tables in practice.html.

    pip install markdown pygments
    python3 tools/build_practice.py /path/to/mellp    # a checkout of HeyItWorked/mellp

practice.html decides which exercise goes under which lecture section: edit its
tables, then rerun. Statements come from static/files/hl7-practice/README.md and
the mellp problem READMEs; solutions from each set's solutions/ folder.
"""
import html
import re
import subprocess
import sys
from pathlib import Path

import markdown
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name

ROOT = Path(__file__).resolve().parent.parent
HL7 = ROOT / "static/files/hl7-practice"
MELLP = Path(sys.argv[1])
MELLP_URL = "https://github.com/HeyItWorked/mellp/tree/main/"
LABS = {"A": "wireshark", "B": "mirth"}


def code_block(source, lang):
    """The markup the lecture pages use, so static/css/syntax.css applies."""
    if lang == "plaintext":
        inner = html.escape(source)
    else:
        inner = highlight(source, get_lexer_by_name(lang), HtmlFormatter(nowrap=True))
    return (f'<div class="language-{lang} highlighter-rouge"><div class="highlight">'
            f'<pre class="highlight"><code>{inner}</code></pre></div></div>')


def md(text):
    """Markdown to HTML: site-style code blocks and tables, headings one level down."""
    text = text.replace("<details>", '<details markdown="1">')  # hints hold markdown
    out = markdown.markdown(text, extensions=["fenced_code", "tables", "md_in_html"])
    out = re.sub(r'<pre><code(?: class="language-(\w+)")?>(.*?)</code></pre>',
                 lambda m: code_block(html.unescape(m[2]), m[1] or "plaintext"), out, flags=re.S)
    out = re.sub(r"<(/?)h(\d)", lambda m: f"<{m[1]}h{int(m[2]) + 1}", out)
    out = re.sub(r"</?blockquote>\n?", "", out)  # static/js/sidenotes.js moves blockquotes into the margin
    return out.replace("<table>", '<div class="table-wrap">\n<table>').replace("</table>", "</table>\n</div>")


def inline(text):
    return md(text).removeprefix("<p>").removesuffix("</p>")


HL7_SPECS = {
    num: (title, level, body)
    for num, title, level, body in re.findall(
        r"^## (\d\d)\. ([^\n]*) \((Easy|Medium|Hard)\)\n(.*?)(?=^## \d\d\. |^# Section |\Z)",
        (HL7 / "README.md").read_text(), flags=re.M | re.S)
}


def hl7_exercise(num):
    title, level, body = HL7_SPECS[num]
    stub = next(HL7.glob(f"p{num}_*.py")).name
    solution = (HL7 / "solutions" / stub).read_text()
    helper = ""
    if "_hl7" in solution:
        helper = ('<p>It imports <a href="static/files/hl7-practice/solutions/_hl7.py">'
                  "<code>solutions/_hl7.py</code></a>.</p>\n")
    return dict(
        id=f"hl7-practice-{num}", name=f"hl7-practice {num}", title=inline(title),
        body=f"<p><code>{level}</code></p>\n{md(body)}",
        run=(f'<p>Write it in <a href="static/files/hl7-practice/{stub}"><code>{stub}</code></a>, '
             f"then run <code>python3 test_practice.py p{num}</code>.</p>"),
        solution=helper + code_block(solution, "python"))


def mellp_exercise(num):
    folder = next((MELLP / "problems").glob(f"{num}-*")).name
    text = (MELLP / "problems" / folder / "README.md").read_text()
    title, body = re.match(r"# \d\d\. (.*?)\n(.*)", text, re.S).groups()
    body, _, run = body.rpartition("\n---\n")  # every statement ends with how to run its tests
    assert body, f"{folder}: expected '---' before the test command"
    return dict(
        id=f"mellp-{num}", name=f"mellp {num}", title=inline(title), body=md(body),
        run=(f'<p>Write it in <a href="{MELLP_URL}problems/{folder}"><code>problems/{folder}/solution.py</code></a>, '
             f"then run:</p>\n{md(run)}"),
        solution=code_block((MELLP / "solutions" / f"{folder}.py").read_text(), "python"))


def lab(letter):
    folder = LABS[letter]
    text = (MELLP / "labs" / folder / "README.md").read_text()
    title, body = re.match(r"# Lab \w: (.*?)\n(.*)", text, re.S).groups()
    return dict(
        id=f"mellp-lab-{letter.lower()}", name=f"mellp Lab {letter}", title=inline(title), body=md(body),
        run=f'<p>The lab files are in <a href="{MELLP_URL}labs/{folder}"><code>labs/{folder}/</code></a>.</p>',
        solution=None)


def nums(text):
    """'01, 04–06' -> ['01', '04', '05', '06']"""
    return [f"{n:02d}"
            for a, b in re.findall(r"(?<![\w-])(\d\d)(?:–(\d\d))?(?![\w-])", text)
            for n in range(int(a), int(b or a) + 1)]


def placement(page):
    """{week: (week title, [(lecture-section cell, [exercise, ...]), ...])} from practice.html."""
    weeks = {}
    for week, title, table in re.findall(
            r'<h2 id="week-(\d)">Week \d: <a [^>]*>(.*?)</a></h2>(.*?)</table>', page, re.S):
        rows = []
        for section, hl7_cell, mellp_cell in re.findall(
                r"<tr><td>(.*?)</td><td>(.*?)</td><td>(.*?)</td></tr>", table):
            exercises = [hl7_exercise(n) for n in nums(hl7_cell.split(":")[0])]
            for part in re.split(r"[;.] ", mellp_cell):  # "01–05: framing; 15–17: sockets. Lab A: ..."
                head = part.split(":")[0]
                is_lab = re.fullmatch(r"Lab ([AB])", head)
                exercises += [lab(is_lab[1])] if is_lab else [mellp_exercise(n) for n in nums(head)]
            rows.append((section, exercises))
        weeks[week] = (title, rows)
    return weeks


def render(week, title, rows, head, foot, mellp_commit):
    count = sum(len(exercises) for _, exercises in rows)
    contents, sections = [], []
    for cell, exercises in rows:
        anchor = re.search(r'#([\w-]+)"', cell)[1]
        name = re.sub(r"<[^>]+>", "", cell)
        links = ", ".join(f'<a href="#{e["id"]}">{e["name"]}</a>' for e in exercises)
        contents.append(f'  <li><a href="#{anchor}">{name}</a>: {links}</li>')
        sections.append(f'<h1 id="{anchor}">{name}</h1>\n\n<p>Lecture: {cell}.</p>')
        for e in exercises:
            sections.append(f'<h2 id="{e["id"]}">{e["name"]}: {e["title"]}</h2>\n\n{e["body"]}\n\n{e["run"]}')
            if e["solution"]:
                sections.append(f'<details>\n<summary>Reference solution</summary>\n{e["solution"]}\n</details>')
    return "\n\n".join([
        head.replace("Practice problems &middot;", f"Week {week} practice &middot;"),
        f'<h1 class="title">Week {week} practice</h1>\n<h2 class="subtitle">{title} · {count} exercises</h2>',
        f'<p>The full text of every practice problem that fits <a href="week-{week}.html">week {week}</a>, '
        "grouped by lecture section. Set up the two sets first: the commands are on the "
        '<a href="practice.html#the-two-sets">practice problems</a> page. Each reference solution is '
        "collapsed under its exercise; run the tests before you open it.</p>",
        "<ul>\n" + "\n".join(contents) + "\n</ul>",
        *sections,
        f'<p class="small">mellp statements and solutions are copied from mellp at commit <code>{mellp_commit}</code>.</p>',
        foot])



def main():
    page = (ROOT / "practice.html").read_text()
    weeks = placement(page)

    placed = sorted(e["id"] for _, rows in weeks.values() for _, exercises in rows for e in exercises)
    expected = sorted([f"hl7-practice-{n:02d}" for n in range(1, 19)]
                      + [f"mellp-{n:02d}" for n in range(1, 39)]
                      + ["mellp-lab-a", "mellp-lab-b"])
    assert placed == expected, f"practice.html must place every exercise once: {set(placed) ^ set(expected)}"

    head, rest = page.split('<div id="content">\n', 1)
    foot = rest[rest.index("<hr>"):]
    commit = subprocess.check_output(["git", "-C", str(MELLP), "rev-parse", "--short", "HEAD"], text=True).strip()
    for week, (title, rows) in weeks.items():
        target = ROOT / f"practice-week-{week}.html"
        target.write_text(render(week, title, rows, head + '<div id="content">', foot, commit))
        print(target.name, sum(len(exercises) for _, exercises in rows), "exercises")


main()
