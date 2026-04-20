with open('/home/claude/paper0_v1.py', 'r') as f:
    content = f.read()

# Insert the table just before the axioms section
old = 'story.append(H2("2.4 Axioms for neg"))'

new = ('story.append(H2("2.4 Complement and antipode compared"))\n'
       'story.append(P(\n'
       '    "The two operators are most clearly compared in a single table. "\n'
       '    "Reading down each column gives the full logic of that operator; "\n'
       '    "reading across each row shows precisely where they agree and where "\n'
       '    "they diverge. The Boolean collapse is the case where the two columns "\n'
       '    "become identical — requiring the third and fourth rows to both become "\n'
       '    "equalities simultaneously."))\n'
       '\n'
       '# Two-column comparison table\n'
       'from reportlab.platypus import Table, TableStyle\n'
       'from reportlab.lib import colors as rl_colors\n'
       '\n'
       'tbl_data = [\n'
       '    ["", "Complement", "Antipode"],\n'
       '    ["Operation", "not", "neg"],\n'
       '    ["Repetition", "not(not(A)) = A", "neg(neg(A)) ⊆ A"],\n'
       '    ["Intersection", "A ∩ not(A) = ∅", "A ∩ neg(A) = ∅"],\n'
       '    ["Union", "A ∪ not(A) = U", "A ∪ neg(A) ⊊ U"],\n'
       ']\n'
       '\n'
       'col_widths = [2.8*cm, 4.0*cm, 4.0*cm]\n'
       'tbl = Table(tbl_data, colWidths=col_widths)\n'
       'tbl.setStyle(TableStyle([\n'
       '    ("FONTNAME",  (0,0), (-1,0),  "Times-Bold"),\n'
       '    ("FONTNAME",  (0,1), (0,-1),  "Times-Italic"),\n'
       '    ("FONTNAME",  (1,1), (1,1),   "Courier-Bold"),\n'
       '    ("FONTNAME",  (2,1), (2,1),   "Courier-Bold"),\n'
       '    ("FONTNAME",  (1,2), (-1,-1), "Courier"),\n'
       '    ("FONTSIZE",  (0,0), (-1,-1), 8.5),\n'
       '    ("LEADING",   (0,0), (-1,-1), 12),\n'
       '    ("ALIGN",     (0,0), (-1,-1), "CENTER"),\n'
       '    ("VALIGN",    (0,0), (-1,-1), "MIDDLE"),\n'
       '    ("TOPPADDING",(0,0), (-1,-1), 4),\n'
       '    ("BOTTOMPADDING",(0,0),(-1,-1),4),\n'
       '    ("LINEBELOW", (0,0), (-1,0),  0.6, rl_colors.black),\n'
       '    ("LINEBELOW", (0,-1),(-1,-1), 0.6, rl_colors.black),\n'
       '    ("LINEABOVE", (0,0), (-1,0),  0.6, rl_colors.black),\n'
       '    ("LINEBEFORE",(1,0), (1,-1),  0.4, rl_colors.black),\n'
       '    ("LINEBEFORE",(2,0), (2,-1),  0.4, rl_colors.black),\n'
       '    ("BACKGROUND",(0,0), (-1,0),  rl_colors.HexColor("#f0f0f0")),\n'
       '    ("BACKGROUND",(0,1), (0,-1),  rl_colors.HexColor("#f8f8f8")),\n'
       '    # Highlight the differing rows\n'
       '    ("TEXTCOLOR", (2,2), (2,2),   rl_colors.HexColor("#aa0000")),\n'
       '    ("TEXTCOLOR", (2,4), (2,4),   rl_colors.HexColor("#aa0000")),\n'
       ']))\n'
       'story.append(SP(6))\n'
       'story.append(tbl)\n'
       'story.append(SP(4))\n'
       'story.append(P(\n'
       '    "The red entries in the antipode column mark the two points of departure "\n'
       '    "from the complement: deflation instead of involution (row 2), and "\n'
       '    "strict inclusion instead of identity (row 4). These are not independent "\n'
       '    "— the Boolean collapse theorem shows they must change together. "\n'
       '    "The agreement on intersection (row 3) is the shared commitment: "\n'
       '    "opposition is genuine in both logics."))\n'
       'story.append(SP(4))\n'
       'story.append(H2("2.5 Axioms for neg"))')

if old in content:
    content = content.replace(old, new)
    print("Table inserted.")
else:
    print("Target not found.")

# Fix subsequent section numbers
for old_n, new_n in [
    ('story.append(H2("2.5 Axioms for neg"))', 'story.append(H2("2.5 Axioms for neg"))'),
    ('story.append(H2("2.6 Structural consequences"))', 'story.append(H2("2.6 Structural consequences"))'),
]:
    pass  # numbers already correct from previous patch

with open('/home/claude/paper0_v1.py', 'w') as f:
    f.write(content)
print("Done.")