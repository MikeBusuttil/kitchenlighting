"""Drawing-only annotations for the component placement PDF."""
import pcbnew as pcb

from pcb_legend import LEGEND_HEADERS, legend_rows


def point(x, y):
    return pcb.VECTOR2I(pcb.FromMM(x), pcb.FromMM(y))


def label(board, value, x, y, size=1.8):
    item = pcb.PCB_TEXT(board)
    item.SetText(value)
    item.SetPosition(point(x, y))
    item.SetTextSize(point(size, size))
    item.SetTextThickness(pcb.FromMM(size * .13))
    item.SetHorizJustify(pcb.GR_TEXT_H_ALIGN_LEFT)
    item.SetVertJustify(pcb.GR_TEXT_V_ALIGN_CENTER)
    item.SetLayer(pcb.Cmts_User)
    board.Add(item)
    return item


def line(board, start, end, width=.12):
    item = pcb.PCB_SHAPE(board)
    item.SetShape(pcb.SHAPE_T_SEGMENT)
    item.SetStart(point(*start))
    item.SetEnd(point(*end))
    item.SetWidth(pcb.FromMM(width))
    item.SetLayer(pcb.Cmts_User)
    board.Add(item)


def add_legend(board):
    """Use the open right-hand area of the A4 landscape assembly sheet."""
    columns = (122, 151, 212, 282)
    top, row_height = 38, 4.8
    rows = [LEGEND_HEADERS, *legend_rows()]
    label(board, 'COMPONENT LEGEND', columns[0], 32, 2.2)
    for row_number, row in enumerate(rows):
        y = top + (row_number + .5) * row_height
        for column_number, value in enumerate(row):
            item = label(board, value, columns[column_number] + 1.5, y)
            available = columns[column_number + 1] - columns[column_number] - 3
            if pcb.ToMM(item.GetBoundingBox().GetWidth()) > available:
                raise ValueError(f'Legend text exceeds its column: {value}')
    bottom = top + len(rows) * row_height
    if bottom > 160:
        raise ValueError('Component legend overlaps the assembly title block')
    for x in columns:
        line(board, (x, top), (x, bottom))
    for row_number in range(len(rows) + 1):
        y = top + row_number * row_height
        line(board, (columns[0], y), (columns[-1], y))
    label(board, 'Exact manufacturer part numbers: pcb-bom.csv.', columns[0], bottom + 4, 1.5)

