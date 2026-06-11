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
    s += [T("dashboard/app.py + data_pipeline.py + theme.py + figures/", "title"),
          T("Interaktives Dash-Dashboard für Schwartz-Wertorientierungen (ESS Runde 11)", "subtitle"),
          HR()]

    s += [T("Was macht dieses Dashboard?", "h1"),
          T("Das Dashboard visualisiert Schwartz-Wertorientierungen aus dem European Social "
            "Survey Runde 11 (2023, 30 Länder, ~50 000 Befragte) in fünf Tabs: About (Hero + "
            "Methodik), Country Profile (Radar), Country Deep Dive (regionale Choroplethen, "
            "Regionalkorrelate, soziale Gradienten für DE/CH), Correlations (FDR-korrigierte "
            "Heatmap + Scatter + Mehrebenenmodelle) und Value Space (PCA + K-Means mit "
            "Silhouettenvalidierung). Die Architektur trennt strikt: data_pipeline.py "
            "(Daten), theme.py (Design-Tokens + Plotly-Template), layouts.py (statisches "
            "Layout), figures/ (eine Datei pro Diagrammtyp), app.py (Callbacks).", "body"),
          SPACE(8)]

    s += [T("1 · Personenzentrierte Schwartz-Scores mit Gewichten", "h1"),
          T("Die methodische Kernlogik: PVQ-Items werden umgepolt (7 - x, denn 1 = "
            "'sehr ähnlich'), pro Person am eigenen Mittelwert zentriert (Ipsatisierung) "
            "und erst dann mit dem ESS-Analysegewicht anweight aggregiert:", "body"),
          CODE("rev  = 7 - df[ALL_PVQ_ITEMS]            # höher = stärkere Zustimmung\n"
               "mrat = rev.mean(axis=1)                  # persönlicher Mittelwert\n"
               "for key, items in PVQ21_ITEMS.items():\n"
               "    df[f'c_{key}'] = rev[items].mean(axis=1) - mrat\n\n"
               "# Gewichteter Länder-Mittelwert (np.average mit weights)\n"
               "np.average(vals[mask], weights=weights[mask])"),
          T("Ohne Umpolung wären alle Vorzeichen invertiert (historischer Bug); ohne "
            "Gewichte wären über-repräsentierte Gruppen (städtisch, gebildet) "
            "übergewichtet. Befragte mit weniger als 16 von 21 gültigen Items werden "
            "ausgeschlossen.", "body"),
          SPACE(6)]

    s += [T("2 · Plotly-Template als zentrales Design-System", "h1"),
          T("Statt Schriftart und Farben in jeder Figur zu wiederholen, registriert "
            "theme.py einmal ein Template und setzt es als Default:", "body"),
          CODE("import plotly.io as pio\n"
               "import plotly.graph_objects as go\n\n"
               "template = go.layout.Template()\n"
               "template.layout = go.Layout(\n"
               "    font=dict(family='Inter, sans-serif', size=12.5),\n"
               "    paper_bgcolor='#ffffff',\n"
               "    hoverlabel=dict(bgcolor='white'),\n"
               ")\n"
               "pio.templates['values'] = template\n"
               "pio.templates.default = 'values'      # gilt ab jetzt überall"),
          T("Jede go.Figure() erbt das Template automatisch. Die CSS-Seite spiegelt "
            "dieselben Tokens als CSS-Variablen (:root { --c-primary: ... }) — eine "
            "Quelle der Wahrheit pro Medium, beide in theme.py dokumentiert.", "body"),
          SPACE(6)]

    s += [T("3 · dash-mantine-components — fertige UI-Bausteine", "h1"),
          T("Native Dash-Dropdowns sehen nach Browser-Defaults aus. Die "
            "Mantine-Bibliothek liefert konsistent gestylte Komponenten:", "body"),
          CODE("import dash_mantine_components as dmc\n\n"
               "app.layout = dmc.MantineProvider(    # Pflicht-Wrapper\n"
               "    theme={'fontFamily': 'Inter, sans-serif'},\n"
               "    children=html.Div([...]),\n"
               ")\n\n"
               "dmc.Select(id='country', data=[{'value': 'DE', 'label': 'Germany'}],\n"
               "           searchable=True, radius='md')\n"
               "dmc.SegmentedControl(id='td-country', data=[...], fullWidth=True)\n"
               "dmc.Accordion(...)   # Info-Panels ohne eigene Callbacks"),
          T("Wichtig: dmc 2.x benötigt Dash >= 3 und app = Dash(external_stylesheets="
            "dmc.styles.ALL). dmc.Accordion ersetzt die früheren button-basierten "
            "Info-Panels samt ihrer vier Toggle-Callbacks — der Auf/Zu-Zustand lebt "
            "komplett im Browser.", "body"),
          SPACE(6)]

    s += [T("4 · Dynamisch eingebundene Inputs und PreventUpdate", "h1"),
          T("Die Hero-Buttons existieren erst, wenn der About-Tab gerendert wird. "
            "Dash feuert Callbacks beim Einhängen solcher Komponenten erneut — "
            "trotz prevent_initial_call=True:", "body"),
          CODE("@app.callback(Output('main-tabs', 'value'),\n"
               "              Input('hero-btn-profile', 'n_clicks'),\n"
               "              Input('hero-btn-deep', 'n_clicks'),\n"
               "              prevent_initial_call=True)\n"
               "def hero_navigate(profile_clicks, deep_clicks):\n"
               "    if not profile_clicks and not deep_clicks:\n"
               "        raise PreventUpdate          # Mount-Feuerung abfangen\n"
               "    return 'tab-1' if ctx.triggered_id == 'hero-btn-profile' \\\n"
               "           else 'tab-deep'"),
          T("Ohne den Guard springt das Dashboard beim Laden sofort auf Tab 1, "
            "weil beide n_clicks=0-Werte als 'Trigger' ankommen. Generell gilt: "
            "Callbacks, deren Inputs in dynamisch gerenderten Tabs leben, müssen "
            "den Null-Klick-Fall explizit behandeln.", "body"),
          SPACE(6)]

    s += [T("5 · Vorberechnung statt Live-Berechnung (Render-Deployment)", "h1"),
          T("Die ESS-Rohdaten (Nutzungsbedingungen!) bleiben lokal. "
            "export_precomputed.py schreibt kleine aggregierte CSVs, die der "
            "Server liest. Jeder Loader prüft zuerst den Cache:", "body"),
          CODE("def load_data() -> pd.DataFrame:\n"
               "    cached = _load_precomputed('df_main')   # precomputed/df_main.csv\n"
               "    if cached is not None:\n"
               "        return cached\n"
               "    micro = add_person_scores(read_ess11_micro())  # nur lokal\n"
               "    return build_country_aggregates(micro)"),
          T("Vorteile: schneller Serverstart, keine 700-MB-Rohdaten im Deployment, "
            "und die Korrelations-Heatmap wird sogar nur einmal beim App-Start "
            "gebaut, weil sie keine veränderlichen Inputs mehr hat.", "body")]

    save_pdf("dashboard.pdf", s)


def proto_build_regional():
    s = [T("build_regional.py", "title"),
         T("GISCO-NUTS-Geometrien + Eurostat-Regionalindikatoren für den Deep-Dive-Tab", "subtitle"),
         HR(),
         T("Was dieses Script tut", "h1"),
         T("Es lädt die NUTS-2021-Regionsgrenzen vom GISCO-Dienst der EU, "
           "beschneidet sie auf Deutschland (NUTS-1, Bundesländer) und die Schweiz "
           "(NUTS-2, Grossregionen), und holt fünf Regionalindikatoren "
           "(BIP/Kopf, Arbeitslosigkeit, Tertiärquote, Medianalter, Bevölkerungsdichte) "
           "über die Eurostat-API — jeweils das neueste verfügbare Jahr pro Region. "
           "Ergebnis: precomputed/nuts_regions.geojson und df_regional_indicators.csv.", "body"),
         SPACE(10),

         T("1 · GeoJSON — Geometrien als JSON", "h1"),
         T("GeoJSON ist ein Standardformat für Geodaten: eine FeatureCollection "
           "enthält Features mit geometry (Polygon-Koordinaten) und properties "
           "(Metadaten wie NUTS_ID):", "body"),
         CODE('{ "type": "FeatureCollection",\n'
              '  "features": [\n'
              '    { "type": "Feature",\n'
              '      "geometry": { "type": "Polygon", "coordinates": [...] },\n'
              '      "properties": { "NUTS_ID": "DE1", "NUTS_NAME": "Baden-W..." }\n'
              '    } ] }'),
         T("GISCO bietet die Dateien in mehreren Auflösungen (60M/20M/10M/03M) und "
           "pro NUTS-Ebene an. 10M ist ein guter Kompromiss: glatte Umrisse, "
           "trotzdem nur ~70 KB nach dem Zuschnitt auf 23 Regionen. "
           "separators=(',', ':') beim json.dumps spart Whitespace.", "body"),
         SPACE(6),

         T("2 · Eurostat-API und das JSON-stat-Format", "h1"),
         T("Die Eurostat-Dissemination-API liefert Daten als JSON-stat 2.0: "
           "die Werte stehen in einem flachen Dictionary, dessen Schlüssel ein "
           "linearer Index über alle Dimensionskombinationen ist:", "body"),
         CODE("# Anfrage: ein Datensatz, feste Filter, mehrere Regionen\n"
              "params = [('format', 'JSON'), ('unit', 'PC'), ('sex', 'T')]\n"
              "params += [('geo', g) for g in REGIONS]   # geo darf wiederholt werden\n"
              "resp = requests.get(url, params=params, timeout=120)\n\n"
              "# Antwort: payload['id'] = ['unit','sex','geo','time']  (Dim-Reihenfolge)\n"
              "#          payload['size'] = [1, 1, 23, 30]             (Kardinalität)\n"
              "#          payload['value'] = {'0': 48600, '1': ...}    (flacher Index)"),
         T("Der flache Index funktioniert wie ein Zahlensystem mit gemischter Basis: "
           "Index = geo_pos * stride_geo + time_pos * stride_time, wobei die Strides "
           "rückwärts aus den Dimensionsgrößen multipliziert werden. Die Dekodierung "
           "ist eine Modulo/Division-Schleife:", "body"),
         CODE("strides = [1] * len(sizes)\n"
              "for i in range(len(sizes) - 2, -1, -1):\n"
              "    strides[i] = strides[i + 1] * sizes[i + 1]\n\n"
              "coords = [(flat // strides[i]) % sizes[i] for i in range(len(sizes))]"),
         SPACE(6),

         T("3 · 'Neuestes Jahr pro Gruppe' mit groupby().tail(1)", "h1"),
         T("Ein häufiges Muster: pro Region nur die jüngste Beobachtung behalten:", "body"),
         CODE("latest = (df.sort_values('time')\n"
              "            .groupby('geo', as_index=False)\n"
              "            .tail(1))     # letzte Zeile je Gruppe = neuestes Jahr"),
         T("sort_values vor groupby garantiert die Reihenfolge innerhalb jeder Gruppe; "
           "tail(1) nimmt die letzte. Alternative wie idxmax funktionieren auch, "
           "aber tail(1) bleibt lesbar, wenn es Bindungen oder NaNs gibt.", "body"),
         SPACE(6),

         T("4 · Choropleth mit eigenem GeoJSON (featureidkey)", "h1"),
         T("So verbindet der Deep-Dive-Tab die Geometrien mit den Daten:", "body"),
         CODE("go.Choropleth(\n"
              "    geojson=feature_collection,\n"
              "    locations=df['region'],              # z. B. 'DE1', 'CH04'\n"
              "    featureidkey='properties.NUTS_ID',   # Matching-Schlüssel\n"
              "    z=df['dim_conservation'],\n"
              "    zmid=0,                              # divergierende Skala um 0\n"
              ")\n"
              "fig.update_geos(fitbounds='locations', visible=False)"),
         T("featureidkey sagt Plotly, welches Property im GeoJSON mit locations "
           "verglichen wird. fitbounds='locations' zoomt automatisch auf die "
           "vorhandenen Regionen; visible=False blendet die Weltkarte darunter aus. "
           "Regionen mit zu kleinem n bekommen einen zweiten, grauen Trace — "
           "ehrlicher als unzuverlässige Schätzwerte einzufärben.", "body")]

    save_pdf("build_regional.pdf", s)


def proto_build_mlm():
    s = [T("build_mlm.py", "title"),
         T("Mehrebenenmodelle (MixedLM): Individuen in Ländern", "subtitle"),
         HR(),
         T("Was dieses Script tut", "h1"),
         T("Für jede der vier Schwartz-Dimensionen schätzt es ein lineares "
           "gemischtes Modell auf den ~48 000 ESS11-Befragten: individuelle "
           "Prädiktoren (Alter, Geschlecht, Bildung, Stadt/Land, Religiosität) und "
           "Länder-Prädiktoren (BIP/Kopf, Gini) gleichzeitig, mit zufälligen "
           "Länder-Intercepts. Die Ergebnisse (Koeffizienten, ICC) landen als JSON "
           "in precomputed/ und werden im Correlations-Tab angezeigt.", "body"),
         SPACE(10),

         T("1 · Warum Mehrebenenmodelle?", "h1"),
         T("Länderkorrelationen können Komposition (wer dort lebt) nicht von "
           "Kontext (wie das Land ist) trennen — und Individualkorrelationen "
           "ignorieren, dass Befragte in Ländern geclustert sind (verletzte "
           "Unabhängigkeitsannahme, zu kleine Standardfehler). Das gemischte Modell "
           "löst beides:", "body"),
         CODE("# y_ij = Score von Person i in Land j\n"
              "y_ij = b0 + b1*alter_ij + b2*bildung_ij     # Komposition\n"
              "          + g1*bip_j    + g2*gini_j          # Kontext\n"
              "          + u_j + e_ij                        # zufälliger Intercept + Rest"),
         SPACE(6),

         T("2 · statsmodels MixedLM mit Formel-API", "h1"),
         CODE("import statsmodels.formula.api as smf\n\n"
              "model = smf.mixedlm(\n"
              "    'dim_openness ~ age_z + female + eduyrs_z + urban + relig_z'\n"
              "    ' + gdp_z + gini_z',\n"
              "    df, groups=df['cntry'],          # Cluster-Variable\n"
              ").fit(reml=True)\n\n"
              "model.params      # feste Effekte (b, g)\n"
              "model.bse         # Standardfehler\n"
              "model.cov_re      # Varianz des zufälligen Intercepts"),
         T("groups= definiert die Cluster (Länder). REML (restricted maximum "
           "likelihood) ist der Standard für Varianzkomponenten. Die Formel-API "
           "übernimmt das Anlegen der Design-Matrix inklusive Intercept.", "body"),
         SPACE(6),

         T("3 · ICC — wie viel Varianz liegt zwischen Ländern?", "h1"),
         T("Der Intraklassen-Korrelationskoeffizient kommt aus dem Nullmodell "
           "(nur Intercept + zufälliger Ländereffekt):", "body"),
         CODE("null = smf.mixedlm('y ~ 1', df, groups=df['cntry']).fit(reml=True)\n"
              "var_u = float(null.cov_re.iloc[0, 0])   # Varianz zwischen Ländern\n"
              "var_e = float(null.scale)               # Varianz innerhalb\n"
              "icc = var_u / (var_u + var_e)"),
         T("Ergebnis hier: 7-18 % je nach Dimension. Heißt: über 80 % der "
           "Wertunterschiede liegen INNERHALB von Ländern — ein Länderprofil ist "
           "ein Durchschnitt, keine Kulturessenz. Das relativiert die "
           "Länder-Scatterplots methodisch korrekt.", "body"),
         SPACE(6),

         T("4 · z-Standardisierung für vergleichbare Koeffizienten", "h1"),
         CODE("def _zscore(s):\n"
              "    return (s - s.mean()) / s.std()\n\n"
              "df['age_z'] = _zscore(df['agea'])\n"
              "df['gdp_z'] = _zscore(macro['wb_gdp_per_capita_ppp'])  # über Länder"),
         T("Nach z-Standardisierung bedeutet ein Koeffizient: 'Änderung des "
           "Scores pro Standardabweichung des Prädiktors' — Alter und BIP werden "
           "direkt vergleichbar. Binäre Variablen (female, urban) bleiben 0/1 "
           "und lesen sich als Gruppendifferenz.", "body")]

    save_pdf("build_mlm.pdf", s)


def proto_scatter_corr():
    s = [T("Correlation Tab mit FDR-Korrektur", "title"),
         T("dashboard/figures/scatter.py  ·  dashboard/app.py (Tab Correlations)", "subtitle"),
         HR(),
         T("Was dieses Modul tut", "h1"),
         T("Dieses Modul visualisiert Pearson-Korrelationen zwischen Länderwerten "
           "von 19 Prädiktoren (gewichtete ESS-Sozialvariablen, externe "
           "Makroindikatoren 2023, COFOG-Staatsausgaben) und den vier "
           "Schwartz-Dimensionen — als Heatmap und als Scatter mit OLS-Gerade und "
           "95 %-Konfidenzband. Analyseeinheit: die 30 Länder der ESS-Runde 11. "
           "Signifikanzsterne basieren auf Benjamini-Hochberg-korrigierten "
           "q-Werten über alle 76 Tests.", "body"),
         SPACE(10),

         T("1 · Multiples Testen und die Benjamini-Hochberg-Prozedur", "h1"),
         T("76 Tests bei alpha = 0.05 erzeugen im Schnitt ~4 falsch-positive "
           "'Befunde'. BH kontrolliert stattdessen die False-Discovery-Rate: den "
           "erwarteten Anteil falscher Entdeckungen unter den als signifikant "
           "markierten:", "body"),
         CODE("def _bh_qvalues(p):\n"
              "    m = len(p)\n"
              "    order = np.argsort(p)\n"
              "    ranked = p[order] * m / (np.arange(m) + 1)   # p * m / Rang\n"
              "    # Monotonie von hinten erzwingen:\n"
              "    ranked = np.minimum.accumulate(ranked[::-1])[::-1]\n"
              "    q = np.empty(m); q[order] = np.clip(ranked, 0, 1)\n"
              "    return q"),
         T("Der Trick: p-Werte aufsteigend sortieren, jeden mit m/Rang "
           "multiplizieren, dann von hinten kumulativ das Minimum nehmen, damit "
           "q-Werte monoton bleiben. np.minimum.accumulate auf dem umgedrehten "
           "Array ist die vektorisierte Form dieser Rückwärtsschleife. "
           "Die Heatmap zeigt p UND q — Transparenz statt Sternchen-Magie.", "body"),
         SPACE(6),

         T("2 · scipy.stats.linregress — OLS-Regression in einer Zeile", "h1"),
         CODE("from scipy import stats\n\n"
              "slope, intercept, r, p, stderr = stats.linregress(x, y)"),
         T("Liefert Steigung, Achsenabschnitt, Pearson-r, zweiseitigen p-Wert "
           "(H0: slope = 0) und den Standardfehler der Steigung in einem Aufruf. "
           "Mit N = 30 Ländern ist die Power begrenzt; einzelne einflussreiche "
           "Länder können r deutlich verschieben — daher der Hinweis 'descriptive, "
           "not causal' im Methoden-Panel.", "body"),
         SPACE(6),

         T("3 · Parametrisches CI-Band um die Regressionsgerade", "h1"),
         CODE("mse    = np.sum((y - (slope*x + intercept))**2) / (n - 2)\n"
              "x_bar  = x.mean()\n"
              "ss_x   = np.sum((x - x_bar)**2)\n"
              "t_crit = stats.t.ppf(0.975, df=n-2)\n\n"
              "se_band = np.sqrt(mse) * np.sqrt(1/n + (x_fit - x_bar)**2 / ss_x)\n"
              "ci_lo, ci_hi = y_fit - t_crit*se_band, y_fit + t_crit*se_band"),
         T("Das Band ist an den Enden breiter als in der Mitte — die Unsicherheit "
           "wächst mit der Entfernung vom Datenschwerpunkt. stats.t.ppf(0.975, df) "
           "ist das obere 2.5 %-Quantil der t-Verteilung.", "body"),
         SPACE(6),

         T("4 · fill='tonexty' — Fläche zwischen zwei Traces", "h1"),
         CODE("fig.add_trace(go.Scatter(x=x_fit, y=ci_hi, mode='lines',\n"
              "                         line=dict(width=0), hoverinfo='skip'))\n"
              "fig.add_trace(go.Scatter(x=x_fit, y=ci_lo, mode='lines',\n"
              "                         line=dict(width=0),\n"
              "                         fill='tonexty',      # bis zum vorherigen Trace\n"
              "                         fillcolor='rgba(37,99,235,0.10)'))"),
         T("fill='tonexty' füllt die Fläche zwischen diesem und dem unmittelbar "
           "davor hinzugefügten Trace — die Reihenfolge der add_trace()-Aufrufe "
           "ist entscheidend.", "body"),
         SPACE(6),

         T("5 · customdata + hovertemplate — strukturierte Tooltips", "h1"),
         CODE("fig.add_trace(go.Scatter(\n"
              "    x=x_vals, y=y_vals,\n"
              "    customdata=np.stack([names, flags, x_vals, y_vals], axis=1),\n"
              "    hovertemplate=('%{customdata[1]} <b>%{customdata[0]}</b><br>'\n"
              "                   'Trust: %{customdata[2]:.3f}'\n"
              "                   '<extra></extra>'),\n"
              "))"),
         T("customdata ist ein 2D-Array (eine Zeile pro Punkt); "
           "%{customdata[i]} greift im Template auf Spalte i zu. "
           "<extra></extra> unterdrückt den automatischen Trace-Namen.", "body"),
         SPACE(6),

         T("6 · Hierarchisches Clustering der Heatmap-Zeilen", "h1"),
         T("Die 19 Prädiktor-Zeilen werden so sortiert, dass ähnliche "
           "Korrelationsmuster nebeneinander liegen:", "body"),
         CODE("from scipy.cluster.hierarchy import linkage, leaves_list\n"
              "from scipy.spatial.distance import pdist\n\n"
              "dist  = pdist(r_matrix, metric='euclidean')  # paarweise Distanzen\n"
              "order = leaves_list(linkage(dist, method='average'))"),
         T("pdist liefert die kondensierte Distanzmatrix, linkage baut den "
           "Dendrogramm-Baum (average linkage = UPGMA), leaves_list gibt die "
           "Blattreihenfolge zurück — eine Permutation der Zeilenindizes, die "
           "ähnliche Zeilen benachbart anordnet.", "body")]

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
proto_build_regional()
proto_build_mlm()
proto_scatter_corr()
print("\nFertig. Alle PDFs in scripts/learning_protocols/")
