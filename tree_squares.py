#!/usr/bin/env python
# -*- coding: latin-1 -*-

"""
Create hierarchical .svg tree graphs like GrandPerspective on Mac
"""

import pandas as pd
import kajsvg
import kajlib as lib

def tree_paint(infile, hier, num_flds):
    # Prepare SVG canvas
    svg.set_canvas("A4")
    svg.set_orientation("portrait")
    svg.reset_margins()
    svg.def_margins('outer', 'mm', 15, 13, 15, 8)
    svg.def_margins('inner', 'mm', 30, 19, 21, 14)
    print("margins %s" % svg.margins)
    svg.set_margins()
    print("canvas %s" % str(svg.canvas))
    svg.set_title(f"Tetris Tree for {infile}", "tree_squares.py")
    s = svg.doc_header()

    # Read CSV file into pandas DataFrame
    data_orig = pd.read_csv(infile)

    #scale = 1 - 81. / 175
    scale = 1
    margin = 5
    height = 68 * scale

    x0 = margin
    x1 = 205
    y0 = margin
    y1 = y0 + height

    current_hier = []
    for item in hier:
        current_hier.append(item)
        cols = hier + num_flds
        data2 = data_orig[cols]
        data = data2.set_index(hier)
        textfield = (num_flds[0] if item == 'namn' else item)
        textfield = num_flds[0]
        print(f"current_hier {current_hier}")
        s += split_into_subtrees(data, current_hier, 1, x0, y0, x1, y1, item, textfield)
        y0 += margin + height
        y1 += margin + height

    s += "</svg>"
    return s

def split_into_subtrees(data, hier, level, x0, y0, x1, y1, text_field, num_fld):
    print("split_into_subtrees(data, %s, %s, %s, %s, %s, %s, %s)" %
     (hier, level, x0, y0, x1, y1, text_field))
    rows = len(data.index)
    if rows == 0: # We have "split" a chunk of only one row into two chunks,
        # the second of which is obviously empty
        return ""
    #print(f"Level {level} len(hier) {len(hier)} rows {rows}")
    if rows == 1: # Now we have reached the bottom and can paint
        return paint_cell(data, x0, y0, x1, y1, text_field)
    if level == len(hier) + 1: # Maximum desired level of recursion
        return paint_cell(data, x0, y0, x1, y1, text_field)

    # The splitting algorithm may have de-sorted the data
    #data_index = data.set_index(hier)
    data_sorted = data.sort_index()
    #print(f"hier {hier} index {data_sorted.index}")
    #print(f"depth {data_sorted.index.lexsort_depth}")

    # Go one level deeper, if only one entry on this level
    current_hier = hier[0:level]
    EntriesOnThisLevel = len(data_sorted.groupby(current_hier).size().index)
    if EntriesOnThisLevel == 1:
        level += 1
        current_hier = hier[0:level]

    # Sort the entries on this level by size, descending order
    chunksizes = []
    for name, group in data.groupby(current_hier)[num_fld]:
        chunksizes += [(group.sum(), name)]
    sorted_chunks = sorted(chunksizes, key = lambda x: x[0], reverse=True)
    #print(f"EntriesOnThisLevel {EntriesOnThisLevel}, Chunksizes {chunksizes}")

    # Separate the entries into two chunks, as equal in size as can be
    data_1 = pd.DataFrame()
    data_2 = pd.DataFrame()
    tree_1_size = tree_2_size = 0
    s = ""
    for chunk in sorted_chunks:
        id = chunk[1]
        size = chunk[0]
        #print(f"id {id} size {size} data_sorted {data_sorted}")
        this_data = data_sorted[id:id]
        if tree_1_size <= tree_2_size:
            tree_1_size += size
            data_1 = pd.concat([data_1, this_data])
        else:
            tree_2_size += size
            data_2 = pd.concat([data_2, this_data])

    # Now recursively split both of the two chunks
    first_share = tree_1_size / (tree_1_size + tree_2_size)
    aspect_ratio = (y1 - y0) / (x1 - x0)
    IsPortrait = aspect_ratio > 1
    if IsPortrait:
        y_mid = y0 + first_share * (y1 - y0)
        if tree_1_size > 0:
            s = split_into_subtrees(data_1, hier, level, x0, y0, x1, y_mid, text_field, num_fld)
        if tree_2_size > 0:
            s += split_into_subtrees(data_2, hier, level, x0, y_mid, x1, y1, text_field, num_fld)
    else:
        x_mid = x0 + first_share * (x1 - x0)
        if tree_1_size > 0:
            s = split_into_subtrees(data_1, hier, level, x0, y0, x_mid, y1, text_field, num_fld)
        if tree_2_size > 0:
            s += split_into_subtrees(data_2, hier, level, x_mid, y0, x1, y1, text_field, num_fld)
    return s

def paint_cell(data, x0, y0, x1, y1, text_field):

    # Find out colour of cell
    row = data.reset_index()
    fill = "black"
    """
    kmh = row['kmh'].sum()
    if kmh < 10:
        color = 'Wiki'
    elif kmh < 10.5:
        color = 'Ankdammen'
    else:
        color = 'Fredrika'

    if text_field == 'namn':
        kon = row['kon']
        if kon == 'kvinna':
            color = 'Wiki'
        else:
            color = 'Fazer'
    else:
    color = 'Fredrika'
    if text_field == 'namn':
        text_field = 'init'
        kon = row['kon2'].min()
        if kon == 1:
            color = 'Fazer'
        else:
            color = 'Wiki'
    if text_field == 'namn':
        text_field = 'init'
        kon = row['kon2'].min()
        if kon == 1:
            color = 'Fazer'
        else:
            color = 'Wiki'
    rader = row['rader'].mean()
    if rader < 1000:
        color = 'Wiki'
    elif rader < 3000:
        color = 'Ankdammen'
    else:
        color = 'Fredrika'
    """
    #days = row['days'].mean()
    bytes = row['bytes'].mean()
    files = row['files'].mean()
    #print(f"files {files}")
    """
    if files > 15:
        color = 'Blue 1'
        fill = 'white'
    elif files > 9:
        color = 'Blue 2'
        fill = 'white'
    elif files > 6:
        color = 'Blue 3'
        fill = 'white'
    elif files > 3:
        color = 'Blue 4'
        fill = 'white'
    elif files > 1:
        color = 'Blue 5'
    else:
        color = 'Blue 6'
    if days > 300:
        color = 'Brown 2'
        fill = 'white'
    elif days > 150:
        color = 'Brown 4'
        fill = 'white'
    else:
        color = 'Brown 6'
    """
    filesize = bytes/files
    if filesize > 10000000:
        color = 'Wiki'
        if filesize > 20000000:
            fill = 'white'
    elif filesize > 5000000:
        color = 'Ankdammen'
    else:
        color = 'Fredrika'
    #color = 'Fredrika'

    fill_style = {'fill': color}
    s = svg.plot_rect_mm(x0, y0, x1 - x0, y1 - y0, fill_style)

    # Find out text to write in cell
    text = row[text_field].min()
    available_width = x1 - x0
    available_height = y1 - y0
    is_portrait = available_height > available_width
    angle = (-90 if is_portrait else 0)
    max_point_size = 0.9 * (available_width if is_portrait else available_height)
    text = str(text)
    text_width = len(text)
    ratio = max(available_width / text_width, available_height / text_width)
    text_size = min(max_point_size, min(24, 0.1 * int(14 * ratio)))

    text_style = {'font-size': text_size, 'text-anchor': "middle", 'dominant-baseline': "central", 'fill': fill}
    s += svg.comment(f"{text}: max_point_size {max_point_size:.2f} textsize {text_size}")
    #s += svg.comment(f"- {text}: ratio {ratio:.2f} available width {available_width:.2f}")
    s += svg.plot_text_mm(x0 + available_width / 2, y0 + available_height / 2, text, text_style, angle=angle)
    #print(text)
    #row2 = row.values[0].astype(str)
    #row3 = map(str, row2)
    #row4 = ' '.join(row3)
    #print(f"bottom {row4} - ({x0:.2f}, {y0:.2f}) - ({x1:.2f}, {y1:.2f})")
    return s


infile = '/Users/kaj/Code/tetris/kaj_sprang_2019.csv'
outfile = '/Users/kaj/Code/tetris/kaj_sprang_2019.svg'
#hier = ['land', 'ort', 'rutt', 'datum']
hier = ['man', 'land', 'rutt', 'datum']
num_flds = ['km', 'kmh']

infile = '/Users/kaj/Code/tetris/finlandssvenskar.csv'
outfile = '/Users/kaj/Code/tetris/finlandssvenskar.svg'
# namn,kon,yrke,tid,ort,rader
hier = ['tid', 'kon']
hier = ['yrke', 'kon']
hier = ['tid', 'ort', 'yrke', 'namn']
hier = ['ort', 'yrke', 'kon']
hier = ['kon', 'yrke']
num_flds = ['antal', 'rader', 'kon2', 'arh', 'init']


infile = '/Users/kaj/Code/tetris/commits_2009-2019.csv'
outfile = '/Users/kaj/Code/tetris/commits_2009-2019.svg'
hier = ['org', 'who', 'date']
num_flds = ['sum', 'count', 'files']

infile = '/Users/kaj/Code/tetris/backlog_2019-12-31.csv'
outfile = '/Users/kaj/Code/tetris/backlog_2019-12-31.svg'
hier = ['type', 'author', 'pr']
num_flds = ['count', 'delandupd', 'days']

infile = '/Users/kaj/Code/tetris/fyrk_ink_2019.csv'
outfile = '/Users/kaj/Code/tetris/fyrk_ink_2019.svg'
hier = ['hier1', 'hier2', 'hier3']
num_flds = ['betrag']

infile = '/Users/kaj/Code/tetris/a_utg.csv'
outfile = '/Users/kaj/Code/tetris/a_utg.svg'
hier = ['hier1', 'hier2', 'hier3']
num_flds = ['betrag']

infile = '/Users/kaj/Code/tetris/kajdisk_pic_2019.csv'
outfile = '/Users/kaj/Code/tetris/kajdisk_pic_2019.svg'
hier = ['hier1', 'hier2', 'hier3']
num_flds = ['bytes','files']

config_files = {
    'Colors': {'filename': 'pf_colors.csv', 'item': 'Color',
               'fields': 'color pf_color pass_1 hex pass_2 r g b'}}

colors = lib.Config(**config_files['Colors'])
_colors = {}
for color in colors:
    _colors[color.color] = color.hex
svg = kajsvg.SVG(_colors)

a_str = tree_paint(infile, hier, num_flds)

lib.save_as(outfile, a_str, verbose=True)

#svg_filename = dict(
#    svg_icons='ge_svg_icons.svg',)
#_svg_icon_file = os.path.join(_config_file_dir, svg_filename['svg_icons'])

#_icon_dir = os.path.join(_py_dir, "svg")