"""
Lernprotokoll-Generator
=======================
Erzeugt alle Lernprotokolle als formatierte PDFs in scripts/learning_protocols/.
Ausführen: python scripts/generate_learning_protocols.py

Lernprotokoll für dieses Script selbst:
  → scripts/learning_protocols/generate_learning_protocols.pdf

Konzepte:
  - reportlab: professionelle PDF-Erzeugung in Python
  - Platypus-Layout-System von reportlab: Flowables (Absätze, Abstände, Code-Blöcke)
    werden in einer Liste gesammelt und dann durch den "story"-Mechanismus auf Seiten
    verteilt. Man denkt in Inhalten, nicht in x/y-Koordinaten.
  - Styles: ParagraphStyle definiert Schriftart, -größe, Farbe, Abstände.
    Styles werden einmal definiert und dann wiederverwendet.
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Preformatted, HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "learning_protocols")
os.makedirs(OUT_DIR, exist_ok=True)

# ── Farben ─────────────────────────────────────────────────────────────────────
COL_DARK    = colors.HexColor("#0d1b2a")
COL_BLUE    = colors.HexColor("#1a5fb4")
COL_PURPLE  = colors.HexColor("#5c3d8f")
COL_CODE_BG = colors.HexColor("#f0f4f8")
COL_MID     = colors.HexColor("#4a5568")
COL_RULE    = colors.HexColor("#cbd5e0")

# ── Styles ─────────────────────────────────────────────────────────────────────
def make_styles():
    base = getSampleStyleSheet()

    title = ParagraphStyle("proto_title",
        fontName="Helvetica-Bold", fontSize=22, textColor=COL_DARK,
        spaceAfter=4, leading=28)

    subtitle = ParagraphStyle("proto_subtitle",
        fontName="Helvetica", fontSize=13, textColor=COL_MID,
        spaceAfter=18, leading=18)

    h1 = ParagraphStyle("proto_h1",
        fontName="Helvetica-Bold", fontSize=15, textColor=COL_BLUE,
        spaceBefore=18, spaceAfter=6, leading=20)

    h2 = ParagraphStyle("proto_h2",
        fontName="Helvetica-Bold", fontSize=12, textColor=COL_DARK,
        spaceBefore=14, spaceAfter=4, leading=16)

    body = ParagraphStyle("proto_body",
        fontName="Helvetica", fontSize=10, textColor=COL_DARK,
        spaceAfter=6, leading=15, wordWrap='CJK')

    code = ParagraphStyle("proto_code",
        fontName="Courier", fontSize=8.5, textColor=COL_DARK,
        spaceAfter=8, leading=13, leftIndent=12,
        backColor=COL_CODE_BG, borderPadding=(6, 10, 6, 10))

    note = ParagraphStyle("proto_note",
        fontName="Helvetica-Oblique", fontSize=9.5, textColor=COL_MID,
        spaceAfter=6, leading=14, leftIndent=14,
        borderPadding=(4, 8, 4, 8))

    return dict(title=title, subtitle=subtitle, h1=h1, h2=h2,
                body=body, code=code, note=note)

S = make_styles()

# ── Hilfsfunktionen ────────────────────────────────────────────────────────────
def T(text, style="body"):
    """Paragraph mit dem gewählten Style."""
    return Paragraph(text, S[style])

def CODE(text):
    return Preformatted(text.strip(), S["code"])

def HR():
    return HRFlowable(width="100%", thickness=0.5, color=COL_RULE,
                      spaceAfter=10, spaceBefore=4)

def SPACE(h=6):
    return Spacer(1, h)

def save_pdf(filename, story):
    path = os.path.join(OUT_DIR, filename)
    doc = SimpleDocTemplate(
        path, pagesize=A4,
        leftMargin=2.8*cm, rightMargin=2.8*cm,
        topMargin=2.5*cm, bottomMargin=2.5*cm,
    )
    doc.build(story)
    print(f"  ✓  {filename}")

# ══════════════════════════════════════════════════════════════════════════════
# PROTOKOLLE
# ══════════════════════════════════════════════════════════════════════════════

def proto_merge_ess():
    s = []
    s += [T("merge_ess.py", "title"),
          T("ESS-Rohdaten aus 11 Runden zu einem Datensatz zusammenführen", "subtitle"),
          HR()]

    s += [T("Was macht dieses Script?", "h1"),
          T("Das Script liest die CSV-Dateien der ESS-Erhebungsrunden 1–11 ein, "
            "filtert auf 15 europäische Länder, bereinigt die Spaltennamen und "
            "stapelt alle Runden zu einem einzigen großen DataFrame. Das Ergebnis "
            "ist die Basis für alle weiteren Analysen.", "body"), SPACE(8)]

    s += [T("1 · Dateipfade per Muster finden — glob.glob()", "h1"),
          T("Anstatt Dateinamen hart einzutippen, sucht <b>glob.glob()</b> nach "
            "allen Dateien die einem Muster entsprechen:", "body"),
          CODE("import glob\n"
               "csv_files = glob.glob('/pfad/zu/ESS1/*.csv')\n"
               "# gibt z.B. zurück: ['/pfad/zu/ESS1/ESS1e06_6.csv']"),
          T("Das <b>*</b>-Zeichen steht für beliebig viele Zeichen. "
            "So findet man alle CSVs in einem Ordner ohne den genauen Dateinamen "
            "zu kennen. <b>os.path.join()</b> baut plattformunabhängige Pfade — "
            "auf Windows wäre der Trenner \\ statt /, join macht das automatisch richtig.", "body"),
          SPACE(6)]

    s += [T("2 · Daten einlesen — pandas.read_csv()", "h1"),
          T("<b>pandas</b> ist die Standard-Bibliothek für tabellarische Daten in Python. "
            "read_csv() liest eine CSV-Datei in einen <b>DataFrame</b> — stell dir das "
            "als eine Excel-Tabelle im Speicher vor, mit Spaltennamen und Zeilenindex.", "body"),
          CODE("import pandas as pd\n"
               "df = pd.read_csv('datei.csv', low_memory=False)"),
          T("<b>low_memory=False</b>: Ohne diesen Parameter liest pandas die Datei "
            "in Blöcken und rät dabei den Datentyp jeder Spalte. Das kann zu Fehlern "
            "führen. low_memory=False liest alles auf einmal und bestimmt Typen sicher.", "body"),
          SPACE(6)]

    s += [T("3 · Zeilen filtern — .isin()", "h1"),
          T("Um nur bestimmte Länder zu behalten, nutzt man <b>.isin()</b>:", "body"),
          CODE("laender = ['DE', 'FR', 'BE']\n"
               "df = df[df['cntry'].isin(laender)]"),
          T("df['cntry'] wählt eine Spalte aus. .isin(liste) gibt für jede Zeile True "
            "oder False zurück — True wenn der Wert in der Liste steht. df[maske] "
            "behält nur die True-Zeilen. Das ist kürzer und schneller als "
            "df[(df['cntry']=='DE') | (df['cntry']=='FR') | ...].", "body"),
          SPACE(6)]

    s += [T("4 · DataFrames stapeln — pandas.concat()", "h1"),
          T("Um mehrere DataFrames untereinander zu hängen:", "body"),
          CODE("alle_runden = [df1, df2, df3, ...]  # Liste von DataFrames\n"
               "gesamt = pd.concat(alle_runden, ignore_index=True)"),
          T("<b>ignore_index=True</b> nummeriert die Zeilen neu von 0 bis n. "
            "Ohne das würden die originalen Zeilennummern erhalten bleiben, was "
            "zu Dopplungen führt (mehrere Zeilen mit Index 0, 1, 2...). "
            "concat ist effizienter als eine append()-Schleife, weil nur einmal "
            "Speicher alloziert wird.", "body"),
          SPACE(6)]

    s += [T("5 · Spaltennamen bereinigen — List Comprehension", "h1"),
          T("ESS-Variablen haben in neueren Runden ein 'a'- oder 'b'-Suffix "
            "(ipcrtiva statt ipcrtiv). Um alle Runden vergleichbar zu machen, "
            "wird das entfernt:", "body"),
          CODE("def normalize(name):\n"
               "    if name.startswith('ip') and name.endswith(('a', 'b')):\n"
               "        return name[:-1]  # letztes Zeichen entfernen\n"
               "    return name\n\n"
               "df.columns = [normalize(c) for c in df.columns]"),
          T("<b>name[:-1]</b> ist ein String-Slice: negativer Index -1 = letztes Zeichen, "
            ":-1 bedeutet 'alles bis auf das letzte'. Die List Comprehension "
            "[normalize(c) for c in df.columns] wendet die Funktion auf jeden "
            "Spaltennamen an und gibt eine neue Liste zurück.", "body")]

    save_pdf("merge_ess.pdf", s)


def proto_aggregate_schwartz():
    s = []
    s += [T("aggregate_schwartz_values.py", "title"),
          T("Individuelle ESS-Antworten zu Ländermittelwerten aggregieren", "subtitle"),
          HR()]

    s += [T("Was macht dieses Script?", "h1"),
          T("Das Script liest alle ESS-Runden direkt als CSV, filtert auf gültige "
            "Schwartz-Werte (1–6), berechnet für jede Kombination Land × Jahr den "
            "Mittelwert und Median aller 14 PVQ-Variablen, und schreibt das Ergebnis "
            "in eine neue CSV. Aus ~500.000 individuellen Antworten werden so "
            "~150 kompakte Land-Jahr-Zeilen.", "body"), SPACE(8)]

    s += [T("1 · Strukturierte Daten lesen — csv.DictReader", "h1"),
          T("Das eingebaute <b>csv</b>-Modul (ohne Installation) liest jede Zeile "
            "als Dictionary — Spaltenname als Key, Zellinhalt als Value:", "body"),
          CODE("import csv\n\n"
               "with open('ess_daten.csv', encoding='utf-8') as f:\n"
               "    reader = csv.DictReader(f)\n"
               "    for row in reader:\n"
               "        land  = row['cntry']    # 'DE'\n"
               "        wert  = row['ipcrtiv']  # '4'"),
          T("DictReader liest die erste Zeile als Header und jede weitere als dict. "
            "Das ist robuster als Spalten per Index (row[3]) anzusprechen — "
            "wenn sich die Reihenfolge ändert, bleibt der Code korrekt.", "body"),
          SPACE(6)]

    s += [T("2 · Daten sammeln — defaultdict", "h1"),
          T("Ein normales dict wirft einen Fehler wenn man einen nicht-vorhandenen "
            "Key abfragt. <b>defaultdict</b> erzeugt automatisch einen Standardwert:", "body"),
          CODE("from collections import defaultdict\n\n"
               "# defaultdict(list) erzeugt automatisch eine leere Liste\n"
               "# wenn ein Key zum ersten Mal aufgerufen wird\n"
               "daten = defaultdict(list)\n\n"
               "daten['DE'].append(4.2)  # kein KeyError, obwohl 'DE' neu ist\n"
               "daten['DE'].append(3.8)\n"
               "# daten == {'DE': [4.2, 3.8]}"),
          T("Im Script wird ein verschachteltes defaultdict genutzt: "
            "daten[(land, jahr)][variable] → Liste von Werten. Tupel wie "
            "(land, jahr) können als Dictionary-Schlüssel dienen — alles "
            "Unveränderliche (Strings, Zahlen, Tupel) geht, Listen nicht.", "body"),
          SPACE(6)]

    s += [T("3 · Mittelwert und Median berechnen", "h1"),
          T("Beide Maße beschreiben die 'Mitte' einer Verteilung, aber unterschiedlich:", "body"),
          CODE("werte = [1, 2, 3, 4, 100]  # ein Ausreißer\n\n"
               "# Mittelwert: Summe / Anzahl\n"
               "mean = sum(werte) / len(werte)   # = 22.0  (stark beeinflusst)\n\n"
               "# Median: mittlerer Wert nach Sortierung\n"
               "werte.sort()\n"
               "n = len(werte)\n"
               "median = werte[n // 2]           # = 3  (robust)"),
          T("Der Median ist stabiler bei Ausreißern und besser für Skalen-Daten "
            "(1–6), weil er keine Annahmen über Abstände zwischen den Stufen macht. "
            "<b>//</b> ist Integer-Division: 5 // 2 = 2 (kein Rest).", "body"),
          SPACE(6)]

    s += [T("4 · Daten validieren — Bereichscheck", "h1"),
          T("ESS-Daten enthalten Missing-Codes (7, 8, 9) die keine echten Werte sind:", "body"),
          CODE("val = row['ipcrtiv']\n"
               "if val.strip().isdigit():\n"
               "    v = float(val)\n"
               "    if 1 <= v <= 6:       # nur gültige Werte\n"
               "        daten[key].append(v)"),
          T("Python erlaubt verkettete Vergleiche: <b>1 &lt;= v &lt;= 6</b> ist "
            "gleichbedeutend mit v >= 1 and v <= 6, aber kürzer. "
            "<b>.isdigit()</b> prüft ob der String nur aus Ziffern besteht — "
            "so werden leere Strings und Texte sicher ausgeschlossen.", "body")]

    save_pdf("aggregate_schwartz_values.pdf", s)


def proto_extract_vars():
    s = []
    s += [T("extract_vars_final.py", "title"),
          T("Gemeinsame Variablen aus ESS-HTML-Codebüchern extrahieren", "subtitle"),
          HR()]

    s += [T("Was macht dieses Script?", "h1"),
          T("Das Script liest die HTML-Codebücher aller 11 ESS-Runden, extrahiert "
            "alle Variablennamen per regulärem Ausdruck, findet die Schnittmenge "
            "(Variablen die in allen Runden vorkommen), filtert auf relevante "
            "Meinungs- und Wertevariablen, und schreibt eine Markdown-Tabelle "
            "als Dokumentation.", "body"), SPACE(8)]

    s += [T("1 · Textmuster finden — Reguläre Ausdrücke", "h1"),
          T("Reguläre Ausdrücke (Regex) beschreiben Textmuster. Python hat das "
            "Modul <b>re</b> dafür:", "body"),
          CODE("import re\n\n"
               "text = '<span>ipcrtiv</span> - Creative'\n\n"
               "# (  ) = Capture Group: dieser Teil wird gemerkt\n"
               "# [^<]+ = ein oder mehr Zeichen die KEIN < sind\n"
               "muster = r'<span>([^<]+)</span>'\n\n"
               "treffer = re.findall(muster, text)\n"
               "# → ['ipcrtiv']"),
          T("<b>re.findall()</b> gibt alle Treffer als Liste zurück. Mit Klammern "
            "(Capture Groups) werden nur die eingeklammerten Teile zurückgegeben. "
            "Das r vor dem String-Literal bedeutet 'raw string' — Backslashes werden "
            "nicht als Escape-Zeichen interpretiert, was Regex-Muster lesbarer macht.", "body"),
          SPACE(6)]

    s += [T("2 · Gemeinsame Elemente finden — Mengen", "h1"),
          T("Ein <b>set</b> ist eine ungeordnete Menge ohne Duplikate. "
            "Mengenoperationen sind sehr effizient:", "body"),
          CODE("runde1 = {'ipcrtiv', 'ipeqopt', 'vote', 'happy'}\n"
               "runde2 = {'ipcrtiv', 'ipeqopt', 'lrscale'}\n"
               "runde3 = {'ipcrtiv', 'lrscale', 'happy'}\n\n"
               "# Schnittmenge: was ist in ALLEN Runden?\n"
               "gemeinsam = runde1 & runde2 & runde3\n"
               "# → {'ipcrtiv'}\n\n"
               "# Mit &= schrittweise einschränken:\n"
               "gemeinsam = set(runde1)\n"
               "for r in [runde2, runde3]:\n"
               "    gemeinsam &= r"),
          T("Der <b>&=</b>-Operator ist die In-Place-Schnittmenge: nach jeder Runde "
            "bleiben nur Variablen die in allen bisherigen Runden vorkamen. "
            "Der <b>in</b>-Operator auf einem set ist O(1) — egal wie groß das Set, "
            "die Suche dauert konstant lang (dank Hashing).", "body"),
          SPACE(6)]

    s += [T("3 · Strings filtern — startswith() mit Tupel", "h1"),
          CODE("praefixe = ('ip', 'stf', 'trst')\n\n"
               "name = 'ipcrtiv'\n"
               "if name.startswith(praefixe):\n"
               "    print('relevant')  # → relevant\n\n"
               "# Statt umständlich:\n"
               "# if name.startswith('ip') or name.startswith('stf') or ..."),
          T("<b>startswith()</b> und <b>endswith()</b> akzeptieren ein Tupel von "
            "Strings und geben True zurück wenn einer davon passt. Das ist "
            "nicht nur kürzer, sondern auch schneller als eine Schleife.", "body"),
          SPACE(6)]

    s += [T("4 · Dateien schreiben — with open()", "h1"),
          CODE("with open('ausgabe.md', 'w', encoding='utf-8') as f:\n"
               "    f.write('| Kürzel | Beschreibung |\\n')\n"
               "    f.write('| :--- | :--- |\\n')\n"
               "    for name, label in daten:\n"
               "        f.write(f'| {name} | {label} |\\n')"),
          T("Das <b>with</b>-Statement ist ein Kontextmanager: es öffnet die Datei "
            "und schließt sie garantiert wenn der Block endet — auch bei Fehlern. "
            "encoding='utf-8' sorgt für korrekte Sonderzeichen. "
            "<b>\\n</b> im String ist ein Zeilenumbruch.", "body")]

    save_pdf("extract_vars_final.pdf", s)


def proto_extract_cofog():
    s = []
    s += [T("extract_cofog_final.py", "title"),
          T("Regierungsausgaben aus einer Excel-Datei ohne openpyxl lesen", "subtitle"),
          HR()]

    s += [T("Was macht dieses Script?", "h1"),
          T("Das Script öffnet eine Excel-Datei, extrahiert aus vier bestimmten "
            "Tabellenblättern die Ausgaben für Verteidigung, Gesundheit, Bildung "
            "und Soziales, und fügt diese Werte in den ESS-Datensatz ein. "
            "Besonderheit: statt der openpyxl-Bibliothek wird die Datei direkt "
            "als ZIP-Archiv geöffnet.", "body"), SPACE(8)]

    s += [T("1 · Was ist eine XLSX-Datei wirklich?", "h1"),
          T("Eine .xlsx-Datei ist kein geheimnisvolles Binärformat — "
            "sie ist ein ZIP-Archiv mit XML-Dateien darin:", "body"),
          CODE("# Umbenennen und öffnen:\n"
               "# datei.xlsx → datei.zip → entpacken\n"
               "#\n"
               "# Inhalt:\n"
               "# xl/workbook.xml          ← Liste aller Tabellenblätter\n"
               "# xl/sharedStrings.xml     ← alle Texte der Datei (zentraler Pool)\n"
               "# xl/worksheets/sheet1.xml ← Tabelle 1\n"
               "# xl/worksheets/sheet2.xml ← Tabelle 2"),
          T("Excel speichert Texte nicht direkt in den Zellen. Es gibt einen "
            "zentralen String-Pool (sharedStrings.xml), und Zellen speichern "
            "nur einen Index dorthin. Zahlen hingegen stehen direkt in der Zelle.", "body"),
          SPACE(6)]

    s += [T("2 · ZIP-Dateien öffnen — zipfile", "h1"),
          CODE("import zipfile\n\n"
               "with zipfile.ZipFile('datei.xlsx', 'r') as z:\n"
               "    # Dateien im Archiv auflisten:\n"
               "    print(z.namelist())\n\n"
               "    # Eine Datei darin öffnen:\n"
               "    with z.open('xl/sharedStrings.xml') as f:\n"
               "        inhalt = f.read()"),
          T("zipfile ist ein Standardmodul — keine Installation nötig. "
            "z.open() gibt einen Datei-ähnlichen Stream zurück der genau wie "
            "open() funktioniert. Das with-Statement sorgt auch hier für "
            "automatisches Schließen.", "body"),
          SPACE(6)]

    s += [T("3 · XML parsen — ElementTree", "h1"),
          T("<b>XML</b> (Extensible Markup Language) ist ein Textformat mit "
            "verschachtelten Tags, ähnlich HTML. ElementTree ist Pythons "
            "eingebauter XML-Parser:", "body"),
          CODE("import xml.etree.ElementTree as ET\n\n"
               "tree = ET.parse(datei)          # XML einlesen\n"
               "root = tree.getroot()           # wurzel-Element\n\n"
               "# Alle <row>-Elemente finden (// = beliebige Tiefe):\n"
               "for row in root.findall('.//ns:row', namespaces):\n"
               "    for cell in row.findall('ns:c', namespaces):\n"
               "        wert = cell.find('ns:v', namespaces).text"),
          T("Excel-XML hat Namespaces — lange URLs die Konflikte zwischen "
            "verschiedenen XML-Schemas vermeiden. Im Code werden diese mit "
            "einem kurzen Alias ('ns') abgekürzt.", "body"),
          SPACE(6)]

    s += [T("4 · Buchstaben in Spaltenindex umrechnen", "h1"),
          T("Excel-Spalten heißen A, B, ..., Z, AA, AB, ... Das ist Basis-26 "
            "(wie Dezimal, nur mit 26 statt 10 Symbolen):", "body"),
          CODE("# 'A' → 0, 'B' → 1, 'Z' → 25, 'AA' → 26\n"
               "col_letter = 'AB'  # aus Zellreferenz 'AB42'\n"
               "idx = 0\n"
               "for zeichen in col_letter:\n"
               "    idx = idx * 26 + (ord(zeichen) - ord('A') + 1)\n"
               "idx -= 1  # 0-basiert\n"
               "# → 27\n\n"
               "# ord() gibt den Unicode-Codepoint: ord('A') = 65"),
          T("Das ist derselbe Algorithmus wie Dezimal-Parsing: "
            "'AB' = A×26¹ + B×26⁰ = 1×26 + 2 = 28, minus 1 für 0-basiert = 27.", "body")]

    save_pdf("extract_cofog_final.pdf", s)


def proto_extract_gov():
    s = []
    s += [T("extract_gov_exp_v2.py", "title"),
          T("Excel-Datei nach relevantem Tabellenblatt durchsuchen und Daten mergen", "subtitle"),
          HR()]

    s += [T("Was macht dieses Script?", "h1"),
          T("Das Script durchsucht alle Tabellenblätter einer Eurostat-Excel-Datei "
            "dynamisch nach dem Blatt mit den Gesamtregierungsausgaben, extrahiert "
            "die Werte pro Land und Jahr, und fügt sie als neue Spalte in den "
            "bestehenden ESS-Datensatz ein.", "body"), SPACE(8)]

    s += [T("1 · Dateien binär durchsuchen", "h1"),
          T("Um das richtige Tabellenblatt zu finden, wird jede Sheet-XML auf einen "
            "bestimmten Text geprüft — direkt als Bytes:", "body"),
          CODE("with zipfile.ZipFile(xlsx_file) as z:\n"
               "    for i in range(1, 90):\n"
               "        try:\n"
               "            with z.open(f'xl/worksheets/sheet{i}.xml') as f:\n"
               "                if b'Gesamtausgaben' in f.read():\n"
               "                    gefunden = f'sheet{i}.xml'\n"
               "                    break\n"
               "        except KeyError:\n"
               "            continue  # Sheet existiert nicht"),
          T("Das <b>b</b> vor dem String (b'Text') erzeugt ein Bytes-Objekt. "
            "Dateien sind intern Bytes, kein Text — der in-Operator sucht "
            "direkt in den Bytes ohne Dekodierung. "
            "<b>except KeyError: continue</b> fängt den Fall ab dass "
            "sheet{i}.xml nicht existiert, ohne das Programm zu stoppen. "
            "Das ist EAFP: 'Easier to Ask Forgiveness than Permission' — "
            "ein typisches Python-Muster.", "body"),
          SPACE(6)]

    s += [T("2 · Kopfzeile heuristisch finden", "h1"),
          T("Eurostat-Dateien haben keine feste Zeilenposition für den Header. "
            "Lösung: suche nach einer Zeile die viele Jahreszahlen enthält:", "body"),
          CODE("for i, zeile in enumerate(daten):\n"
               "    jahre = {j: val for j, val in enumerate(zeile)\n"
               "             if val.isdigit() and 2000 <= int(val) <= 2025}\n"
               "    if len(jahre) > 5:   # Header gefunden\n"
               "        jahr_spalten = jahre\n"
               "        daten_start  = i + 1\n"
               "        break"),
          T("<b>enumerate()</b> liefert (index, wert)-Paare für jedes Element einer "
            "Liste oder eines anderen Iterables. Das Dict-Comprehension "
            "{j: val for j, val in ...} baut ein Mapping Spaltenindex → Jahreswert. "
            "Das ist Heuristik: kein festes Schema, sondern ein Merkmals-Test.", "body"),
          SPACE(6)]

    s += [T("3 · Ländercodes übersetzen — Mapping-Ketten", "h1"),
          T("Verschiedene Datenquellen nutzen verschiedene Ländercodes. "
            "Mapping-Dicts übersetzen zwischen ihnen:", "body"),
          CODE("# ESS nutzt ISO-2 (2 Buchstaben): 'DE', 'FR'\n"
               "# Eurostat nutzt Klarnamen: 'Germany', 'France'\n\n"
               "iso2_zu_iso3  = {'DE': 'DEU', 'FR': 'FRA', ...}\n"
               "iso3_zu_name  = {'DEU': 'Germany', 'FRA': 'France', ...}\n\n"
               "# Übersetzungskette:\n"
               "iso3 = iso2_zu_iso3.get('DE')       # → 'DEU'\n"
               "name = iso3_zu_name.get(iso3)        # → 'Germany'\n"
               "wert = daten.get(('Germany', '2018'), '')  # → z.B. '48.3'"),
          T("<b>dict.get(key, default)</b> gibt default zurück wenn der Key nicht "
            "existiert — kein KeyError. Das leere '' als default stellt sicher "
            "dass fehlende Werte als leer geschrieben werden.", "body"),
          SPACE(6)]

    s += [T("4 · Streaming: CSV transformieren ohne alles in den RAM zu laden", "h1"),
          CODE("with open('eingabe.csv') as f_in, open('ausgabe.csv', 'w') as f_out:\n"
               "    reader = csv.DictReader(f_in)\n"
               "    writer = csv.DictWriter(f_out, fieldnames=[...])\n"
               "    for zeile in reader:          # eine Zeile nach der anderen\n"
               "        zeile['neue_spalte'] = ...\n"
               "        writer.writerow(zeile)    # sofort schreiben"),
          T("Das <b>with A, B:</b>-Statement öffnet zwei Dateien gleichzeitig. "
            "Zeile für Zeile lesen und schreiben ist ein Streaming-Ansatz: "
            "der RAM-Verbrauch bleibt konstant, egal wie groß die Datei ist.", "body")]

    save_pdf("extract_gov_exp_v2.pdf", s)


def proto_merge_macro():
    s = []
    s += [T("merge_only_macro_v3.py", "title"),
          T("Makrodaten aus fünf verschiedenen Quellen zu einem Datensatz vereinen", "subtitle"),
          HR()]

    s += [T("Was macht dieses Script?", "h1"),
          T("Das Script liest Daten aus fünf Quellen: V-Dem Demokratie-Indizes (CSV), "
            "OECD Inflationsdaten (CSV), sowie Weltbank-Daten zu GDP, Konsum, Gini "
            "und Arbeitslosigkeit (XLSX). Alle Quellen werden zu einem einzigen "
            "Dict kombiniert und als CSV geschrieben. Das Prinzip heißt ETL: "
            "Extract → Transform → Load.", "body"), SPACE(8)]

    s += [T("1 · ETL — das Grundprinzip der Datenpipeline", "h1"),
          T("ETL beschreibt den Ablauf jedes Datenintegrations-Scripts:", "body"),
          CODE("# Extract: Daten aus Quellen lesen\n"
               "with open('vdem.csv') as f:\n"
               "    for zeile in csv.DictReader(f):\n"
               "        rohdaten.append(zeile)\n\n"
               "# Transform: Typen konvertieren, Codes vereinheitlichen\n"
               "for zeile in rohdaten:\n"
               "    zeile['year'] = int(zeile['year'])\n\n"
               "# Load: in Zielformat schreiben\n"
               "with open('ergebnis.csv', 'w') as f:\n"
               "    writer.writerows(ergebnis)"),
          T("ETL ist das Grundmuster aller Datenpipelines — von kleinen Scripts "
            "bis zu Apache Spark. Das Denken in diesen drei Phasen hilft, "
            "Datenprobleme strukturiert zu lösen.", "body"),
          SPACE(6)]

    s += [T("2 · Daten akkumulieren — dict.setdefault()", "h1"),
          T("Mehrere Quellen tragen zu denselben Land-Jahr-Einträgen bei. "
            "setdefault() macht das elegant:", "body"),
          CODE("kombiniert = {}\n\n"
               "# Aus Quelle 1 (V-Dem):\n"
               "kombiniert.setdefault(('DEU', '2018'), {})['v2x_libdem'] = '0.87'\n\n"
               "# Aus Quelle 2 (OECD):\n"
               "kombiniert.setdefault(('DEU', '2018'), {})['inflation'] = '1.8'\n\n"
               "# Ergebnis:\n"
               "# {('DEU', '2018'): {'v2x_libdem': '0.87', 'inflation': '1.8'}}"),
          T("setdefault(key, default) prüft ob key schon im Dict ist. "
            "Wenn nein: setzt key auf default und gibt default zurück. "
            "Wenn ja: gibt den vorhandenen Wert zurück und lässt ihn unverändert. "
            "So kann man direkt .setdefault(...)['spalte'] = wert schreiben "
            "ohne vorher zu prüfen ob der Key existiert.", "body"),
          SPACE(6)]

    s += [T("3 · Ländercodes — ISO-Standards", "h1"),
          T("Länder haben mehrere standardisierte Code-Systeme:", "body"),
          CODE("# ISO 3166-1 alpha-2 (2 Buchstaben) — von ESS genutzt:\n"
               "# DE, FR, GB, US, JP ...\n\n"
               "# ISO 3166-1 alpha-3 (3 Buchstaben) — von V-Dem/Weltbank:\n"
               "# DEU, FRA, GBR, USA, JPN ...\n\n"
               "iso2_zu_iso3 = {'DE': 'DEU', 'FR': 'FRA', 'GB': 'GBR'}"),
          T("Wenn man Datensätze kombiniert die verschiedene Standards nutzen, "
            "muss man übersetzten. Mapping-Dicts sind die einfachste Lösung. "
            "Für größere Projekte gibt es die pycountry-Bibliothek.", "body"),
          SPACE(6)]

    s += [T("4 · Sortierten Output erzeugen", "h1"),
          CODE("for (iso, jahr) in sorted(kombiniert.keys()):\n"
               "    zeile = {'land': iso, 'jahr': jahr}\n"
               "    zeile.update(kombiniert[(iso, jahr)])\n"
               "    writer.writerow(zeile)"),
          T("<b>sorted()</b> auf einer Liste von Tupeln sortiert lexikographisch — "
            "erst nach dem ersten Element (Ländercode alphabetisch), dann nach "
            "dem zweiten (Jahr aufsteigend). "
            "<b>dict.update(anderes_dict)</b> fügt alle Key-Value-Paare aus "
            "anderes_dict ein (überschreibt bei Duplikaten).", "body")]

    save_pdf("merge_only_macro_v3.pdf", s)


def proto_generate_radars():
    s = []
    s += [T("generate_radars_ess11_all.py", "title"),
          T("Radar-Charts für 30 Länder mit matplotlib erzeugen", "subtitle"),
          HR()]

    s += [T("Was macht dieses Script?", "h1"),
          T("Das Script liest den ESS11-Rohdatensatz, berechnet Ländermediane für "
            "14 Schwartz-Variablen, aggregiert sie zu 10 Grundwerten, berechnet "
            "Δ-Scores (Abweichung vom Ländermittel) und erzeugt für jedes der "
            "30 Länder einen hochauflösenden Radar-Chart als PNG.", "body"), SPACE(8)]

    s += [T("1 · Fehlende Werte maskieren — df.replace()", "h1"),
          T("ESS kodiert fehlende Antworten als spezielle Zahlen (66, 77, 88, 99). "
            "Diese müssen vor der Berechnung entfernt werden:", "body"),
          CODE("import numpy as np\n\n"
               "missing = {66: np.nan, 77: np.nan, 88: np.nan, 99: np.nan}\n"
               "df.replace(missing, inplace=True)\n\n"
               "# np.nan = 'Not a Number' — pandas ignoriert NaN bei\n"
               "# Berechnungen wie .mean() und .median() automatisch"),
          T("np.nan (Not a Number) ist der Standard für fehlende Werte in "
            "NumPy und pandas. Wichtig: NaN ist vom Typ float — "
            "nan == nan ergibt False (das ist mathematisch korrekt, "
            "aber oft überraschend). Prüfung: pd.isna(x).", "body"),
          SPACE(6)]

    s += [T("2 · Polarkoordinaten — das Herz des Radar-Charts", "h1"),
          T("Ein Radar-Chart arbeitet mit Polarkoordinaten: "
            "jeder Wert hat einen Winkel und einen Radius. "
            "Für matplotlib braucht man kartesische Koordinaten (x, y):", "body"),
          CODE("import numpy as np\n\n"
               "N = 10  # Anzahl der Achsen\n"
               "winkel = [i * 2 * np.pi / N for i in range(N)]\n"
               "# → 10 gleichmäßig verteilte Winkel von 0 bis fast 2π\n\n"
               "def polar_zu_xy(winkel, radius):\n"
               "    x = radius * np.sin(winkel)   # Rechts-Links\n"
               "    y = radius * np.cos(winkel)   # Oben-Unten\n"
               "    return x, y\n\n"
               "# Winkel=0 → oben (12 Uhr), Winkel=π/2 → rechts (3 Uhr)"),
          T("Der Tausch von sin/cos (normalerweise x=cos, y=sin) dreht das "
            "Koordinatensystem um 90° — damit zeigt Winkel 0 nach oben "
            "statt nach rechts. np.pi ist π (3.14159...). "
            "2π Bogenmaß = 360°.", "body"),
          SPACE(6)]

    s += [T("3 · matplotlib — Grafiken erstellen", "h1"),
          CODE("import matplotlib.pyplot as plt\n\n"
               "fig, ax = plt.subplots(figsize=(11, 13))\n"
               "# fig = gesamte Grafik, ax = der Zeichenbereich darin\n\n"
               "ax.fill(px, py, color='blue', alpha=0.2)  # Fläche\n"
               "ax.plot(px, py, color='blue', linewidth=2) # Linie\n"
               "ax.text(x, y, 'Text', fontsize=10)         # Text\n\n"
               "plt.savefig('chart.png', dpi=180)\n"
               "plt.close()  # Speicher freigeben"),
          T("matplotlib unterscheidet Figure (die gesamte Grafik) und Axes "
            "(ein Koordinatensystem darin — trotz des Namens kein Plural von Axis). "
            "dpi (dots per inch) bestimmt die Auflösung: 180 dpi ergibt "
            "qualitativ hochwertige Grafiken für Print und Web.", "body"),
          SPACE(6)]

    s += [T("4 · Länderflaggen laden — requests + PIL", "h1"),
          CODE("import requests\n"
               "from PIL import Image\n"
               "from io import BytesIO\n\n"
               "url  = 'https://flagpedia.net/data/flags/w320/de.png'\n"
               "resp = requests.get(url, timeout=12)\n"
               "img  = Image.open(BytesIO(resp.content))\n\n"
               "# BytesIO: Bytes im RAM wie eine Datei behandeln\n"
               "# resp.content: die heruntergeladenen Bytes"),
          T("requests.get() macht einen HTTP-GET-Request. resp.content sind die "
            "rohen Bytes der Antwort (das Bild). BytesIO wrapping macht aus den "
            "Bytes ein datei-ähnliches Objekt das Image.open() versteht — "
            "ohne temporäre Datei auf der Festplatte.", "body")]

    save_pdf("generate_radars_ess11_all.pdf", s)


def proto_animate_html():
    s = []
    s += [T("animate_radar_de_html.py", "title"),
          T("Interaktive 60fps-HTML-Animation mit SVG und JavaScript erzeugen", "subtitle"),
          HR()]

    s += [T("Was macht dieses Script?", "h1"),
          T("Das Script berechnet Schwartz-Δ-Scores für Deutschland über 10 ESS-Runden "
            "(2002–2023), baut einen animierten Radar-Chart in SVG auf, und schreibt "
            "alles als eine einzige selbst-enthaltene HTML-Datei. Im Browser läuft "
            "die Animation mit 60fps, Übergänge zwischen Jahren sind flüssig "
            "interpoliert, und der Nutzer kann die Timeline scrubben.", "body"), SPACE(8)]

    s += [T("1 · SVG — Vektorgrafik im Browser", "h1"),
          T("<b>SVG</b> (Scalable Vector Graphics) ist ein XML-basiertes Format "
            "für Grafiken direkt im Browser. Im Gegensatz zu PNGs (Pixel) bleiben "
            "SVGs bei jeder Zoomstufe scharf:", "body"),
          CODE("<!-- SVG direkt in HTML einbetten: -->\n"
               "<svg viewBox=\"-200 -200 400 400\">\n"
               "  <circle cx=\"0\" cy=\"0\" r=\"100\" fill=\"blue\"/>\n"
               "  <polygon points=\"0,-100 87,50 -87,50\" fill=\"red\"/>\n"
               "  <text x=\"0\" y=\"0\" text-anchor=\"middle\">Hallo</text>\n"
               "</svg>"),
          T("viewBox definiert den logischen Koordinatenraum. Das SVG kann dann "
            "mit CSS auf beliebige Größe skaliert werden. JavaScript kann SVG-Elemente "
            "per document.getElementById() ansprechen und Attribute ändern — "
            "genau wie HTML-Elemente.", "body"),
          SPACE(6)]

    s += [T("2 · Animationen im Browser — requestAnimationFrame", "h1"),
          CODE("function zeichnen(zeitstempel) {\n"
               "    // zeitstempel in Millisekunden, sehr genau\n"
               "    const fortschritt = (zeitstempel % 11000) / 11000; // 0..1\n"
               "    aktualisiereGrafik(fortschritt);\n"
               "    requestAnimationFrame(zeichnen); // nächsten Frame anfordern\n"
               "}\n"
               "requestAnimationFrame(zeichnen); // starten"),
          T("<b>requestAnimationFrame</b> ruft eine Funktion kurz vor dem nächsten "
            "Browser-Repaint auf — typischerweise 60 Mal pro Sekunde. "
            "Das ist effizienter als setInterval weil der Browser die Animation "
            "pausiert wenn der Tab im Hintergrund ist, und das Timing "
            "synchron zum Bildschirm ist (kein Flimmern).", "body"),
          SPACE(6)]

    s += [T("3 · Flüssige Übergänge — Lineare Interpolation", "h1"),
          T("Um das Radar-Polygon smooth von Wert A nach Wert B zu bewegen, "
            "wird für jeden Frame ein Zwischenwert berechnet:", "body"),
          CODE("// t geht von 0.0 (Start) bis 1.0 (Ende)\n"
               "function lerp(a, b, t) {\n"
               "    return a * (1 - t) + b * t;\n"
               "}\n\n"
               "// Beispiel: von 3.0 nach 5.0, halber Weg (t=0.5):\n"
               "lerp(3.0, 5.0, 0.5)  // → 4.0\n\n"
               "// Für Arrays (alle 10 Schwartz-Werte auf einmal):\n"
               "function lerpArray(a, b, t) {\n"
               "    return a.map((v, i) => v * (1-t) + b[i] * t);\n"
               "}"),
          T("Lineare Interpolation ist das Grundprinzip hinter fast allen "
            "Animationen, Grafiken und neuronalen Netzen. "
            "Array.map() wendet eine Funktion auf jedes Element an "
            "und gibt ein neues Array zurück — kein explizites for-Loop nötig.", "body"),
          SPACE(6)]

    s += [T("4 · Bilder einbetten — base64", "h1"),
          T("Um die HTML-Datei vollständig selbst-enthaltend zu machen (keine "
            "externen Dateien nötig), wird die Flagge als Text eingebettet:", "body"),
          CODE("import base64\n"
               "from io import BytesIO\n\n"
               "# Bild in Bytes umwandeln:\n"
               "buf = BytesIO()\n"
               "bild.save(buf, format='PNG')\n"
               "bytes_daten = buf.getvalue()\n\n"
               "# Bytes als Text kodieren:\n"
               "b64_text = base64.b64encode(bytes_daten).decode()\n\n"
               "# Im HTML verwenden:\n"
               "# <image href=\"data:image/png;base64,iVBOR...\"/>"),
          T("Base64 kodiert beliebige Bytes als ASCII-Text (3 Bytes → 4 Zeichen, "
            "~33% größer). Data URLs (data:image/png;base64,...) erlauben es, "
            "Binärdaten direkt in HTML/CSS einzubetten. "
            "BytesIO ist ein In-Memory-Puffer — verhält sich wie eine Datei, "
            "schreibt aber in den RAM.", "body"),
          SPACE(6)]

    s += [T("5 · Python + HTML/JS — Code generieren", "h1"),
          T("Das Python-Script erzeugt eine HTML-Datei die JavaScript enthält. "
            "Die berechneten Daten werden per String-Konkatenation injiziert:", "body"),
          CODE("import json\n\n"
               "daten = {'jahre': [2002, 2004, ...], 'werte': [[...], ...]}\n\n"
               "html = ('<script>\\n'\n"
               "        'const DATEN = ' + json.dumps(daten) + ';\\n'\n"
               "        '</script>')"),
          T("json.dumps() konvertiert Python-Objekte (dicts, Listen, Zahlen) "
            "in einen JSON-String der direkt in JavaScript eingebettet werden kann — "
            "die Syntax ist nahezu identisch. "
            "String-Konkatenation statt f-Strings vermeidet das Escapen "
            "von JS-Klammern {} in Python-f-Strings.", "body")]

    save_pdf("animate_radar_de_html.pdf", s)


def proto_generator_itself():
    """Protokoll für diesen Generator selbst."""
    s = []
    s += [T("generate_learning_protocols.py", "title"),
          T("PDF-Lernprotokolle mit reportlab erzeugen", "subtitle"),
          HR()]

    s += [T("Was macht dieses Script?", "h1"),
          T("Dieses Script erzeugt alle Lernprotokolle als formatierte PDFs. "
            "Es nutzt reportlab — die Standard-Bibliothek für programmatische "
            "PDF-Erzeugung in Python. PDFs werden nicht pixel-weise gezeichnet, "
            "sondern aus wiederverwendbaren Layout-Bausteinen zusammengesetzt.", "body"),
          SPACE(8)]

    s += [T("1 · reportlab — PDFs programmatisch erstellen", "h1"),
          T("reportlab hat zwei Ebenen: eine Low-Level-Canvas-API "
            "(direkte Koordinaten) und das High-Level-Platypus-System "
            "(Layout-Bausteine). Platypus wird hier verwendet:", "body"),
          CODE("from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer\n"
               "from reportlab.lib.pagesizes import A4\n\n"
               "doc = SimpleDocTemplate('ausgabe.pdf', pagesize=A4)\n\n"
               "# 'story' = Liste von Bausteinen (Flowables)\n"
               "story = [\n"
               "    Paragraph('Überschrift', stil),\n"
               "    Spacer(1, 12),       # 12 Punkte Abstand\n"
               "    Paragraph('Text...', stil),\n"
               "]\n\n"
               "doc.build(story)  # verteilt Bausteine auf Seiten"),
          T("Das Platypus-Konzept: Man beschreibt Inhalte (Absätze, Abstände, "
            "Code-Blöcke) als Liste von Flowables. reportlab kümmert sich "
            "um Seitenumbrüche, Abstände und Layout.", "body"),
          SPACE(6)]

    s += [T("2 · ParagraphStyle — Text formatieren", "h1"),
          CODE("from reportlab.lib.styles import ParagraphStyle\n"
               "from reportlab.lib import colors\n\n"
               "ueberschrift = ParagraphStyle(\n"
               "    'mein_stil',\n"
               "    fontName='Helvetica-Bold',\n"
               "    fontSize=16,\n"
               "    textColor=colors.HexColor('#1a5fb4'),\n"
               "    spaceAfter=8,\n"
               "    leading=20,  # Zeilenabstand\n"
               ")"),
          T("Styles werden einmal definiert und dann wiederverwendet — "
            "dasselbe Prinzip wie CSS. leading ist der Abstand von einer "
            "Textzeilen-Oberkante zur nächsten (Zeilenabstand).", "body"),
          SPACE(6)]

    s += [T("3 · Preformatted — Code-Blöcke", "h1"),
          CODE("from reportlab.platypus import Preformatted\n\n"
               "code_stil = ParagraphStyle('code',\n"
               "    fontName='Courier',  # Monospace-Font\n"
               "    fontSize=8.5,\n"
               "    backColor=colors.HexColor('#f0f4f8'),\n"
               "    borderPadding=(6, 10, 6, 10),\n"
               ")\n\n"
               "code_block = Preformatted('x = 1 + 2', code_stil)"),
          T("Preformatted behält Einrückungen und Zeilenumbrüche exakt bei "
            "(wie das <pre>-Tag in HTML). Courier ist der klassische "
            "Monospace-Font der vorinstalliert ist — keine Schriftdatei nötig.", "body")]

    save_pdf("generate_learning_protocols.pdf", s)


def proto_dashboard():
    s = []
    s += [T("dashboard/app.py + data_pipeline.py + figures/", "title"),
          T("Interaktives Dash-Portfolio-Dashboard für Schwartz-Wertorientierungen", "subtitle"),
          HR()]

    s += [T("Was macht dieses Dashboard?", "h1"),
          T("Das Dashboard visualisiert Schwartz-Wertorientierungen aus dem European Social Survey "
            "(ESS1–11, 2002–2023) für 14 europäische Länder in vier interaktiven Tabs: "
            "Radar-Chart (Länderprofil), Radar-Overlay (Ländervergleich), "
            "Parallelkoordinaten (Dimensionsvergleich) und eine choroplethische Europakarte. "
            "Es nutzt Dash/Plotly als Webframework und läuft lokal unter http://127.0.0.1:8050.", "body"),
          SPACE(8)]

    s += [T("1 · Dash — Python-Webapps ohne JavaScript", "h1"),
          T("Dash ist ein Framework das HTML-Layouts und interaktive Plotly-Charts "
            "mit Python-Callbacks verbindet. Kein JavaScript nötig:", "body"),
          CODE("from dash import Dash, dcc, html, Input, Output, callback\n\n"
               "app = Dash(__name__)\n\n"
               "app.layout = html.Div([\n"
               "    dcc.Dropdown(id='land', options=['DE','FR'], value='DE'),\n"
               "    dcc.Graph(id='radar'),\n"
               "])\n\n"
               "@app.callback(Output('radar', 'figure'), Input('land', 'value'))\n"
               "def update(land):\n"
               "    return make_figure(land)\n\n"
               "app.run(debug=True)"),
          T("Callbacks sind Python-Funktionen die automatisch aufgerufen werden wenn "
            "ein Input-Komponenten-Wert sich ändert. Input() und Output() binden "
            "DOM-Elemente (via id) an Callback-Parameter.", "body"),
          SPACE(6)]

    s += [T("2 · go.Scatterpolar — Radar-Chart in Plotly", "h1"),
          T("Plotly's Radar-Chart nutzt Polarkoordinaten mit kategorischen Achsen:", "body"),
          CODE("import plotly.graph_objects as go\n\n"
               "fig = go.Figure(go.Scatterpolar(\n"
               "    theta=['SD', 'UN', 'BE', 'TR', 'CO'],  # Achsenbeschriftungen\n"
               "    r=[-0.3, 0.5, -0.8, 0.4, -0.1],       # Werte (Δ-Scores)\n"
               "    fill='toself',            # Fläche unter dem Polygon füllen\n"
               "    line=dict(color='#1a5fb4', width=2),\n"
               "))\n"
               "fig.update_layout(polar=dict(\n"
               "    angularaxis=dict(direction='clockwise', rotation=90),\n"
               "    radialaxis=dict(range=[-1.4, 1.75]),\n"
               "))"),
          T("direction='clockwise' + rotation=90: der erste Wert erscheint oben "
            "(12-Uhr-Position), weitere gehen im Uhrzeigersinn — genau wie die "
            "bestehenden matplotlib-Radarcharts. fill='toself' füllt das Polygon "
            "bis zur eigenen Kontur (nicht bis zum Ursprung).", "body"),
          SPACE(6)]

    s += [T("3 · go.Parcoords — Parallelkoordinaten", "h1"),
          T("Parallelkoordinaten visualisieren mehrdimensionale Daten als Linien "
            "über senkrecht angeordneten Achsen:", "body"),
          CODE("fig = go.Figure(go.Parcoords(\n"
               "    dimensions=[\n"
               "        dict(label='Offenheit', values=df['dim_openness']),\n"
               "        dict(label='Bewahrung',  values=df['dim_conservation']),\n"
               "    ],\n"
               "    line=dict(\n"
               "        color=df['land_idx'],       # numerischer Index je Land\n"
               "        colorscale=schrittweise_farben,  # diskrete Farbskala\n"
               "        showscale=False,\n"
               "    ),\n"
               "))"),
          T("go.Parcoords erwartet eine kontinuierliche Farbskala, obwohl wir "
            "diskrete Länder-Farben wollen. Lösung: eine Stufenfarb-Skala — "
            "jedes Band [i/n, (i+1)/n] bekommt genau eine Farbe. "
            "cmin=0, cmax=n mappt den Integer-Index auf die Skala.", "body"),
          SPACE(6)]

    s += [T("4 · go.Choropleth — Europakarte", "h1"),
          T("Choropleth-Karten färben Länder nach einem Zahlenwert ein:", "body"),
          CODE("fig = go.Figure(go.Choropleth(\n"
               "    locations=['DEU', 'FRA', 'POL'],  # ISO-3-Codes\n"
               "    z=[0.12, -0.08, 0.31],            # Wert je Land\n"
               "    colorscale='RdBu_r',              # divergierend, Rot=hoch\n"
               "    zmid=0,                           # Mitte der Farbskala\n"
               "))\n"
               "fig.update_layout(geo=dict(\n"
               "    scope='europe',\n"
               "    projection_type='natural earth',\n"
               "    lonaxis=dict(range=[-15, 35]),\n"
               "    lataxis=dict(range=[35, 72]),\n"
               "))"),
          T("locationmode='ISO-3' (Standard) mappt dreistellige Ländercodes auf "
            "Plotly's eingebauten GeoJSON. scope='europe' zeigt nur Europa. "
            "Länder ohne Daten erscheinen automatisch in hellem Grau. "
            "zmid=0 zentriert die Farbskala am Nullpunkt.", "body"),
          SPACE(6)]

    s += [T("5 · pathlib.Path — portable Dateipfade", "h1"),
          T("Statt absoluter Pfade nutzt das Dashboard Path(__file__).parent "
            "um Dateien relativ zur eigenen Position zu finden:", "body"),
          CODE("from pathlib import Path\n\n"
               "_THIS_DIR = Path(__file__).parent      # Ordner dieser Datei\n"
               "DATA_PATH = _THIS_DIR.parent / 'data' / 'ess_data.csv'\n\n"
               "# Funktioniert auf Windows, Mac und Linux\n"
               "# __file__ ist der absolute Pfad der aktuell laufenden Datei"),
          T("/ (Slash-Operator) bei Path-Objekten verbindet Pfadteile — "
            "Path('a') / 'b' / 'c' ergibt Path('a/b/c'). "
            ".parent gibt den Eltern-Ordner zurück. "
            "Das eliminiert hartcodierte absolute Pfade und macht "
            "das Projekt auf jedem Rechner portabel.", "body")]

    save_pdf("dashboard.pdf", s)


def proto_parallel_micro():
    s = [T("Individual-Level Parallel Coordinates", "title"),
         T("dashboard/data_pipeline.py  ·  dashboard/figures/parallel.py  ·  "
           "dashboard/app.py (Tab 3)", "subtitle"),
         HR(),
         T("Was dieses Modul tut", "h1"),
         T("Dieses Modul lädt individuelle ESS-Befragte aus allen 11 Erhebungsrunden "
           "(2002–2023) für 14 europäische Länder, ordnet jede Person ihrer dominanten "
           "Schwartz-Dimension zu (Openness to Change, Self-Transcendence, Conservation "
           "oder Self-Enhancement), und visualisiert 1 200 geschichtete Stichproben "
           "(300 pro Dimension) in einem Parallelkoordinaten-Diagramm. "
           "Die 12 Achsen zeigen soziale Einstellungsvariablen aus dem ESS: "
           "interpersonales Vertrauen, Institutionenvertrauen, Lebenszufriedenheit, "
           "politische Orientierung, Religiosität und mehr. "
           "Ein Dropdown hebt eine Dimension hervor, während die anderen verblassen.", "body"),
         SPACE(10),

         T("1 · usecols — selektives Laden großer CSV-Dateien", "h1"),
         T("Die ESS-CSVs haben bis zu 600 Spalten, aber wir brauchen nur rund 20. "
           "pandas.read_csv() liest standardmäßig alle Spalten. Mit usecols laden "
           "wir nur das, was wirklich gebraucht wird:", "body"),
         CODE("# Nur benötigte Spalten lesen — viel schneller bei breiten CSVs\n"
              "header = pd.read_csv(path, nrows=0)          # nur Spaltennamen\n"
              "header.columns = header.columns.str.lower()  # normalisieren\n"
              "avail = [c for c in needed if c in header.columns]\n\n"
              "df = pd.read_csv(path, usecols=avail, low_memory=False)"),
         T("Zuerst die Spaltennamen mit nrows=0 laden, dann die tatsächlich "
           "vorhandenen Spalten filtern — so werden Fehler vermieden, wenn eine "
           "Variable in einem bestimmten ESS-Runde fehlt.", "body"),
         SPACE(6),

         T("2 · Ipsatisierung — personenzentrierte Werteprofile", "h1"),
         T("Die 21 PVQ-Items werden auf einer 1–6-Skala bewertet. Verschiedene "
           "Personen nutzen die Skala unterschiedlich (manche sagen generell 'sehr "
           "wichtig', andere 'wenig wichtig'). Ipsatisierung entfernt diesen "
           "Bias, indem der persönliche Mittelwert über alle Items subtrahiert wird:", "body"),
         CODE("pvq_mean = df[pvq_cols].mean(axis=1)  # Mittelwert je Person\n"
              "ip = df[pvq_cols].sub(pvq_mean, axis=0)  # zentrierte Items\n\n"
              "# Dimensionswert = Mittelwert der zugehörigen Items\n"
              "df['_oc'] = ip[['ipcrtiv', 'ipadvnt', 'ipgdtim']].mean(axis=1)\n"
              "df['_st'] = ip[['iphlppl', 'ipeqopt', 'ipudrst']].mean(axis=1)"),
         T("sub(pvq_mean, axis=0) subtrahiert die Zeilenwerte — axis=0 bedeutet, "
           "dass die Series pvq_mean entlang der Zeilen ausgerichtet wird. "
           "Das Ergebnis: positive Werte = relativ wichtiger als der eigene Schnitt, "
           "negative = relativ weniger wichtig.", "body"),
         SPACE(6),

         T("3 · np.argmax — dominante Dimension bestimmen", "h1"),
         T("Jede Person bekommt die Dimension zugeordnet, auf der sie den höchsten "
           "ipsatisierten Wert hat:", "body"),
         CODE("dim_arr = df[['_oc', '_st', '_co', '_se']].values  # numpy-Array\n"
              "dim_idx = np.argmax(dim_arr, axis=1)               # Index des Max pro Zeile\n\n"
              "dim_names = ['Openness to Change', 'Self-Transcendence',\n"
              "             'Conservation', 'Self-Enhancement']\n"
              "df['dominant_dim'] = [dim_names[i] for i in dim_idx]\n"
              "df['dim_id'] = dim_idx.astype(float)"),
         T("np.argmax(array, axis=1) gibt für jede Zeile den Spaltenindex des "
           "maximalen Werts zurück. Das Ergebnis ist ein Integer-Array der Länge n. "
           "dim_id als float ist notwendig, weil Plotly's Parcoords-Farbskala "
           "einen numerischen Wert erwartet.", "body"),
         SPACE(6),

         T("4 · Fehlende Werte bei Likert-Skalen", "h1"),
         T("Im ESS werden fehlende Antworten durch hohe Zahlen kodiert: "
           "77 = weiß nicht, 88 = keine Antwort, 99 = nicht anwendbar. "
           "Für Skalen mit maximal 10 Punkten sind alle Werte > 10 automatisch "
           "fehlende Codes:", "body"),
         CODE("_valid_max = {\n"
              "    'ppltrst': 10, 'lrscale': 10, 'happy': 10,\n"
              "    'gincdif': 5,  'aesfdrk': 4,\n"
              "}\n"
              "for col in MICRO_ATTRS:\n"
              "    df[col] = pd.to_numeric(df[col], errors='coerce')\n"
              "    df[col] = df[col].where(df[col] <= _valid_max.get(col, 10))\n\n"
              "# Imputation: fehlende Werte mit Runden-Median ersetzen\n"
              "medians = df.groupby('essround')[col].transform('median')\n"
              "df[col] = df[col].fillna(medians)"),
         T("where(Bedingung) behält gültige Werte und setzt ungültige auf NaN. "
           "groupby().transform('median') berechnet den Median pro Gruppe und "
           "gibt eine Series derselben Länge zurück — ideal für Imputation ohne "
           "Loop.", "body"),
         SPACE(6),

         T("5 · Richtungsumkehrung von Skalen", "h1"),
         T("Zwei Variablen sind so kodiert, dass niedrige Zahlen 'gut' bedeuten. "
           "Damit höher = positiver auf allen Achsen gilt:", "body"),
         CODE("# gincdif: 1=stimme stark zu (Umverteilung) → soll HOCh sein\n"
              "df['redistr_supp'] = 6 - df['gincdif']  # Bereich bleibt 1–5\n\n"
              "# aesfdrk: 1=sehr sicher → soll HOCh sein\n"
              "df['safety'] = 5 - df['aesfdrk']         # Bereich bleibt 1–4"),
         T("Einfache lineare Transformation: neuer_wert = (max+1) - alter_wert. "
           "Dadurch bleibt der Wertebereich gleich, aber die Richtung kehrt sich um. "
           "Die Bezeichnung auf der Achse erklärt die neue Interpretation.", "body"),
         SPACE(6),

         T("6 · Geschichtete Zufallsstichprobe", "h1"),
         T("Mit ~50 000 Befragten pro Dimension wäre das Diagramm unlesbar. "
           "Eine Zufallsstichprobe von 300 pro Gruppe (1 200 gesamt) macht es "
           "handhabbar, ohne eine Dimension zu bevorzugen:", "body"),
         CODE("rng = np.random.RandomState(seed)   # reproduzierbarer Zufall\n"
              "parts = []\n"
              "for dim in dim_names:\n"
              "    sub = df[df['dominant_dim'] == dim]\n"
              "    n   = min(sample_per_dim, len(sub))   # nicht mehr als vorhanden\n"
              "    parts.append(sub.sample(n=n, random_state=rng))\n\n"
              "result = pd.concat(parts, ignore_index=True)"),
         T("RandomState(seed) erzeugt einen deterministischen Zufallsgenerator — "
           "gleicher Seed = gleiche Stichprobe bei jedem Start. "
           "DataFrame.sample(n, random_state=rng) zieht ohne Zurücklegen. "
           "pd.concat(ignore_index=True) setzt die Zeilenindizes zurück.", "body"),
         SPACE(6),

         T("7 · Diskrete Stufenfarbskala für Plotly Parcoords", "h1"),
         T("go.Parcoords unterstützt nur kontinuierliche Farbskalen — "
           "diskrete Gruppenfarben erfordern einen Trick mit Stufenfunktionen:", "body"),
         CODE("# dim_id: 0=Openness, 1=Transcendence, 2=Conservation, 3=Enhancement\n"
              "# cmin=0, cmax=4 → dim_id=0 liegt bei Position 0.0, dim_id=3 bei 0.75\n\n"
              "colorscale = []\n"
              "for i, dim in enumerate(DIMS):\n"
              "    lo = i / 4                          # Stufenstart\n"
              "    hi = (i + 1) / 4                   # Stufenende\n"
              "    rgba = hex_to_rgba(DIM_COLORS[dim], 0.22)  # transparente Farbe\n"
              "    colorscale.append([lo, rgba])\n"
              "    colorscale.append([(hi - 1e-9) if i < 3 else 1.0, rgba])"),
         T("Jede Stufe besteht aus zwei identischen Einträgen mit fast gleichem "
           "Positionswert — so interpoliert Plotly nicht zwischen den Stufen. "
           "Die 1e-9-Korrektur verhindert, dass der erste Wert der nächsten Stufe "
           "schon die neue Farbe annimmt.", "body"),
         SPACE(6),

         T("8 · Highlight-Effekt durch RGBA-Transparenz", "h1"),
         T("Um eine Dimension hervorzuheben, werden die anderen nahezu unsichtbar:", "body"),
         CODE("def _dim_colorscale(highlight):  # highlight: None oder Dim-Name\n"
              "    scale = []\n"
              "    for i, dim in enumerate(DIMS):\n"
              "        if highlight is None:\n"
              "            rgba = hex_to_rgba(DIM_COLORS[dim], 0.22)   # alle sichtbar\n"
              "        elif dim == highlight:\n"
              "            rgba = hex_to_rgba(DIM_COLORS[dim], 0.65)   # hervorgehoben\n"
              "        else:\n"
              "            rgba = 'rgba(160,160,160,0.04)'              # fast unsichtbar\n"
              "        ...  # Stufeneinträge wie oben"),
         T("hex_to_rgba('#3584e4', 0.65) erzeugt 'rgba(53,132,228,0.65)'. "
           "RGBA-Farben in der Parcoords-Farbskala steuern direkt die "
           "Linienopazität — ohne globale line.opacity, die alle Linien gleich "
           "behandeln würde. Das erlaubt per-Gruppe-Transparenz.", "body")]

    save_pdf("parallel_micro.pdf", s)


def proto_scatter_corr():
    s = [T("Correlation Scatter Tab", "title"),
         T("dashboard/figures/scatter.py  ·  dashboard/data_pipeline.py  ·  "
           "dashboard/app.py (Tab Correlations)", "subtitle"),
         HR(),
         T("Was dieses Modul tut", "h1"),
         T("Dieses Modul visualisiert Pearson-Korrelationen zwischen Ländermitteln "
           "von 17 Prädiktoren (ESS-Sozialvariablen, externe Makroindikatoren, "
           "COFOG-Staatsausgaben) und den vier Schwartz-Dimensionen. "
           "Analyseeinheit: ein Mittelwert pro Land über alle ESS-Runden (N bis zu 39). "
           "Ein Dropdown wählt die X-Achse (Prädiktor); ein zweites wählt eine oder "
           "alle vier Dimensionen. Die Visualisierung zeigt OLS-Regressionsgerade, "
           "95 %-Konfidenzband, Länderkürzel-Labels und Hover mit genauen Werten.", "body"),
         SPACE(10),

         T("1 · scipy.stats.linregress — OLS-Regression in einer Zeile", "h1"),
         T("Die einfache lineare Regression (OLS) zwischen zwei Arrays liefert "
           "alle nötigen Statistiken in einem Aufruf:", "body"),
         CODE("from scipy import stats\n\n"
              "slope, intercept, r, p, stderr = stats.linregress(x, y)\n\n"
              "# slope    = Steigung der Regressionsgeraden\n"
              "# intercept = y-Achsenabschnitt\n"
              "# r         = Pearson-Korrelationskoeffizient\n"
              "# p         = zweiseitiger p-Wert für H0: slope=0\n"
              "# stderr    = Standardfehler der Steigung"),
         T("Bei N bis zu 39 (df bis zu 37) steigt die Teststärke erheblich. p < 0.05 wird als "
           "Signifikanzgrenze verwendet (†), da auch schwache Trends bei kleinem "
           "N substantiell bedeutsam sein können.", "body"),
         SPACE(6),

         T("2 · Parametrisches CI-Band um die Regressionsgerade", "h1"),
         T("Das Konfidenzband zeigt, wo die wahre Gerade mit 95 % Wahrscheinlichkeit "
           "liegt. Formel (analytisch, ohne Bootstrap):", "body"),
         CODE("mse    = np.sum((y - (slope*x + intercept))**2) / (n - 2)\n"
              "se_y   = np.sqrt(mse)                 # Root-MSE\n"
              "x_bar  = x.mean()\n"
              "ss_x   = np.sum((x - x_bar)**2)       # Streuung in x\n"
              "t_crit = stats.t.ppf(0.975, df=n-2)   # t* für 95 % CI\n\n"
              "# Standardfehler des Fitted-Values an jedem x_fit-Punkt:\n"
              "se_band = se_y * np.sqrt(1/n + (x_fit - x_bar)**2 / ss_x)\n\n"
              "ci_lo = y_fit - t_crit * se_band\n"
              "ci_hi = y_fit + t_crit * se_band"),
         T("Das Band ist an den Enden breiter als in der Mitte — weil die "
           "Unsicherheit wächst, je weiter man sich vom Datenschwerpunkt entfernt. "
           "stats.t.ppf(0.975, df) gibt den t-Wert für das obere 2.5 %-Quantil "
           "der t-Verteilung mit df Freiheitsgraden.", "body"),
         SPACE(6),

         T("3 · fill='tonexty' — Fläche zwischen zwei Scatter-Traces", "h1"),
         T("Um das CI-Band als Fläche zu zeichnen, werden zwei unsichtbare Linien "
           "(obere und untere Grenze) mit fill='tonexty' verbunden:", "body"),
         CODE("# Obere Grenze — unsichtbar, definiert den oberen Rand\n"
              "fig.add_trace(go.Scatter(\n"
              "    x=x_fit, y=ci_hi,\n"
              "    mode='lines', line=dict(width=0),\n"
              "    showlegend=False, hoverinfo='skip',\n"
              "))\n\n"
              "# Untere Grenze — füllt bis zur oberen Grenze\n"
              "fig.add_trace(go.Scatter(\n"
              "    x=x_fit, y=ci_lo,\n"
              "    mode='lines', line=dict(width=0),\n"
              "    fill='tonexty',             # Fläche bis zum vorherigen Trace\n"
              "    fillcolor='rgba(53,132,228,0.10)',\n"
              "    showlegend=False, hoverinfo='skip',\n"
              "))"),
         T("fill='tonexty' füllt die Fläche zwischen diesem und dem unmittelbar "
           "davor hinzugefügten Trace. Die Reihenfolge der add_trace()-Aufrufe "
           "ist daher entscheidend: erst obere Grenze, dann untere.", "body"),
         SPACE(6),

         T("4 · customdata + hovertemplate — strukturierte Tooltips", "h1"),
         T("Statt automatischer Hover-Texte übergibt customdata strukturierte Daten "
           "und hovertemplate formatiert sie mit Platzhaltern:", "body"),
         CODE("fig.add_trace(go.Scatter(\n"
              "    x=x_vals, y=y_vals,\n"
              "    customdata=np.stack(\n"
              "        [country_names, flags, x_vals, y_vals], axis=1\n"
              "    ),\n"
              "    hovertemplate=(\n"
              "        '%{customdata[1]}  <b>%{customdata[0]}</b><br>'\n"
              "        'Trust: %{customdata[2]:.3f}<br>'\n"
              "        'Openness: %{customdata[3]:.3f}'\n"
              "        '<extra></extra>'   # unterdrückt den Trace-Namen\n"
              "    ),\n"
              "))"),
         T("customdata ist ein 2D-Array mit einer Zeile pro Datenpunkt. "
           "np.stack([a,b,c], axis=1) transponiert eine Liste von 1D-Arrays zu "
           "einem N×3-Array. Im hovertemplate greifen %{customdata[i]} auf Spalte i "
           "zu. <extra></extra> entfernt den automatischen Trace-Namen aus dem Tooltip.", "body"),
         SPACE(6),

         T("5 · make_subplots — 2×2 Subplot-Raster", "h1"),
         T("Für die Übersicht aller vier Dimensionen gleichzeitig:", "body"),
         CODE("from plotly.subplots import make_subplots\n\n"
              "fig = make_subplots(\n"
              "    rows=2, cols=2,\n"
              "    horizontal_spacing=0.12,\n"
              "    vertical_spacing=0.16,\n"
              ")\n\n"
              "# Traces einem bestimmten Subplot zuordnen:\n"
              "fig.add_trace(go.Scatter(...), row=1, col=1)\n"
              "fig.add_trace(go.Scatter(...), row=1, col=2)\n\n"
              "# Achsen eines bestimmten Subplots formatieren:\n"
              "fig.update_xaxes(title_text='Trust', row=1, col=1)\n"
              "fig.update_yaxes(title_text='Openness (Δ)', row=1, col=1)"),
         T("make_subplots erstellt intern ein 'grid_ref', das row/col-Koordinaten "
           "auf Achsenindizes abbildet (x1, x2, x3, x4 für vier Subplots). "
           "Ohne make_subplots schlägt add_trace(..., row=1, col=1) mit einem "
           "AttributeError fehl.", "body"),
         SPACE(6),

         T("6 · Annotation-Referenzen in Subplots", "h1"),
         T("Texte wie 'r = +0.72 ** p = 0.003' werden per add_annotation() "
           "in einen bestimmten Subplot eingetragen. Referenzen folgen dem Schema "
           "'x{n} domain' / 'y{n} domain' (n = Subplot-Nummer):", "body"),
         CODE("ax_i = (row - 1) * 2 + col      # Subplot-Nummer 1-4\n"
              "xref = 'x domain' if ax_i == 1 else f'x{ax_i} domain'\n"
              "yref = 'y domain' if ax_i == 1 else f'y{ax_i} domain'\n\n"
              "fig.add_annotation(\n"
              "    text='r = +0.72**  p = 0.003',\n"
              "    xref=xref, yref=yref,   # relativ zur Subplot-Fläche\n"
              "    x=0.98, y=0.98,         # rechts oben (0–1 = links–rechts)\n"
              "    xanchor='right', yanchor='top',\n"
              "    showarrow=False,\n"
              ")"),
         T("'x domain' / 'y domain' bedeutet: Koordinaten relativ zur Breite/Höhe "
           "des jeweiligen Subplot-Bereichs (0 = linke/untere Kante, 1 = rechte/"
           "obere Kante). 'paper' wäre relativ zur gesamten Figure. "
           "Für Subplot 1 lautet die Referenz 'x domain', für Subplot 2 'x2 domain', usw.", "body")]

    save_pdf("scatter_corr.pdf", s)


# ── Alle erzeugen ──────────────────────────────────────────────────────────────
print("Erzeuge Lernprotokolle als PDF...\n")
proto_merge_ess()
proto_aggregate_schwartz()
proto_extract_vars()
proto_extract_cofog()
proto_extract_gov()
proto_merge_macro()
proto_generate_radars()
proto_animate_html()
proto_generator_itself()
proto_dashboard()
proto_parallel_micro()
proto_scatter_corr()
print("\nFertig. Alle PDFs in scripts/learning_protocols/")
