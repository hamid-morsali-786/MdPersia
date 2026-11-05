"""Native editable Word list definitions, including restarts and mixed nesting."""
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


def element(name, value=None):
    node = OxmlElement('w:' + name)
    if value is not None:
        node.set(qn('w:val'), str(value))
    return node


def new_list(document, ordered, start=1):
    root = document.part.numbering_part.element
    abstracts = [int(n.get(qn('w:abstractNumId'))) for n in root.findall(qn('w:abstractNum'))]
    numbers = [int(n.get(qn('w:numId'))) for n in root.findall(qn('w:num'))]
    aid, nid = max(abstracts, default=-1) + 1, max(numbers, default=0) + 1
    abstract = element('abstractNum')
    abstract.set(qn('w:abstractNumId'), str(aid))
    abstract.append(element('multiLevelType', 'multilevel'))
    for depth in range(9):
        lvl = element('lvl')
        lvl.set(qn('w:ilvl'), str(depth))
        lvl.extend([element('start', 1), element('numFmt', 'decimal' if ordered else 'bullet'),
                    element('lvlText', f'%{depth + 1}.' if ordered else '•'), element('lvlJc', 'left')])
        abstract.append(lvl)
    # Abstract definitions precede concrete num elements in the schema.
    root.insert(len(root.findall(qn('w:abstractNum'))), abstract)
    num = element('num')
    num.set(qn('w:numId'), str(nid))
    num.append(element('abstractNumId', aid))
    for depth in range(9):
        override = element('lvlOverride')
        override.set(qn('w:ilvl'), str(depth))
        override.append(element('startOverride', start))
        num.append(override)
    root.append(num)
    return nid


def apply_list(paragraph, number, depth, rtl):
    props = paragraph._p.get_or_add_pPr()
    num = element('numPr')
    num.extend([element('ilvl', min(depth, 8)), element('numId', number)])
    props.append(num)
    indent = props.find(qn('w:ind'))
    if indent is None:
        indent = element('ind')
        props.append(indent)
    indent.set(qn('w:right' if rtl else 'w:left'), str(360 * (depth + 1)))
    indent.set(qn('w:hanging'), '240')
