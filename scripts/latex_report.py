"""Editable, self-contained LaTeX output for the team report."""

from html.parser import HTMLParser
from pathlib import Path
import re
import shutil


def latex_escape(value) -> str:
    replacements = {"\\":r"\textbackslash{}", "&":r"\&", "%":r"\%", "$":r"\$",
                    "#":r"\#", "_":r"\_", "{":r"\{", "}":r"\}",
                    "~":r"\textasciitilde{}", "^":r"\textasciicircum{}"}
    return "".join(replacements.get(char,char) for char in str(value))


class ReportText(HTMLParser):
    def __init__(self, plain=False):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.plain = plain

    def handle_starttag(self, tag, attrs):
        if tag == "br":
            self.parts.append("\n" if self.plain else r"\newline{}")
        elif not self.plain and tag in {"b", "i"}:
            self.parts.append(r"\textbf{" if tag=="b" else r"\emph{")

    def handle_endtag(self, tag):
        if not self.plain and tag in {"b", "i"}:
            self.parts.append("}")

    def handle_data(self, data):
        self.parts.append(data if self.plain else latex_escape(data))


def report_text(text, plain=False):
    parser=ReportText(plain)
    parser.feed(text)
    return "".join(parser.parts)


class LatexReport:
    def __init__(self, output: Path):
        self.output=output
        self.parts=[]

    def paragraph(self, text, style="Body"):
        # These references identify document sections; LaTeX pagination is automatic.
        text=re.sub(r"\bpages\b","sections",text,flags=re.IGNORECASE)
        text=re.sub(r"\bpage (?=\d)","section ",text,flags=re.IGNORECASE)
        if style=="Code":
            code=re.sub(r"\n[ \t]+(?=--)"," ",report_text(text,plain=True))
            self.parts.append("\\begin{lstlisting}\n"+code+"\n\\end{lstlisting}")
            return
        value=report_text(text)
        if text.startswith("Input SHA-256: "):
            value="Input SHA-256: \\texttt{\\seqsplit{"+latex_escape(text.split(": ",1)[1])+"}}"
        if style=="Title":
            value="{\\LARGE\\bfseries "+value+"\\par}\\medskip"
        elif style=="Heading":
            value="\\section*{"+value+"}"
        elif style=="Sub":
            value="\\subsection*{"+value+"}"
        elif style=="Caption":
            value="{\\small "+value+"\\par}"
        self.parts.append(value+"\n\\par\\medskip")

    def table(self, rows, widths):
        def cell(value):
            text=latex_escape(value)
            if "_" in str(value):
                text=text.replace(r"\_",r"\_\allowbreak{}").replace(".",r".\allowbreak{}")
            return text
        total=sum(widths)
        columns="".join(r">{\RaggedRight\arraybackslash}p{\dimexpr"+f"{width/total:.6f}"+
                        r"\linewidth-2\tabcolsep\relax}" for width in widths)
        header=" & ".join(r"\textbf{"+cell(v)+"}" for v in rows[0])+r" \\ \midrule"
        lines=[r"\begingroup\small",r"\begin{longtable}{"+columns+"}",r"\toprule",header,
               r"\endfirsthead",r"\toprule",header,r"\endhead"]
        lines += [" & ".join(cell(v) for v in row)+r" \\ \addlinespace[3pt]" for row in rows[1:]]
        lines += [r"\bottomrule",r"\end{longtable}",r"\endgroup"]
        self.parts.append("\n".join(lines))

    def figure(self, source: Path, caption: str):
        images=self.output.parent/"images"
        images.mkdir(parents=True,exist_ok=True)
        target=images/source.name
        if source.resolve()!=target.resolve():
            shutil.copy2(source,target)
        self.parts.append(r"\begin{center}\includegraphics[width=\linewidth,height=0.45\textheight,keepaspectratio]{images/"+
                          source.name+r"}\end{center}")

    def page(self):
        self.parts.append(r"\clearpage")

    def write(self):
        header=r"""% Editable team document. Normal simulation runs do not overwrite this file.
% Explicit regeneration replaces manual edits. Keep images/ with this project.
\documentclass[a4paper,11pt]{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{lmodern}
\usepackage[margin=20mm]{geometry}
\usepackage{graphicx,longtable,array,booktabs,ragged2e,seqsplit,listings}
\usepackage{xcolor,hyperref}
\definecolor{navy}{HTML}{19364F}
\hypersetup{colorlinks=true,linkcolor=navy,urlcolor=navy,pdftitle={Smart Grids Team Guide}}
\lstset{basicstyle=\ttfamily\small,breaklines=true,columns=fullflexible,keepspaces=true}
\setlength{\parindent}{0pt}
\setlength{\emergencystretch}{3em}
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{1.15}
\begin{document}
"""
        self.output.parent.mkdir(parents=True,exist_ok=True)
        self.output.write_text(header+"\n\n".join(self.parts)+"\n\\end{document}\n",encoding="utf-8")
