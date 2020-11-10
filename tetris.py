#!/usr/bin/env python
# -*- coding: latin-1 -*-

"""
Create hierarchical .svg tree graphs like GrandPerspective on Mac
"""

import pandas as pd
import numpy as np
import kajsvg
import kajlib as lib
import sys

def tree_paint(sheet, hier, area, quality, borders):
    # Prepare SVG canvas
    svg.set_canvas("A4")
    svg.set_orientation("portrait")
    svg.reset_margins()
    svg.def_margins('outer', 'mm', 15, 13, 15, 8)
    svg.def_margins('inner', 'mm', 30, 19, 21, 14)
    svg.set_margins()
    #print("margins %s" % svg.margins)
    #print("canvas %s" % str(svg.canvas))
    #svg.set_title(f"Tetris Tree for {sheet}", "tetris.py")
    s = svg.doc_header()

    # Read CSV file into pandas DataFrame
    data_orig = pd.read_excel(commands_file, sheet_name=sheet)
    data_orig = data_orig.replace(np.nan, '', regex=True)

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
        cols = hier + [area, quality]
        #print(f"current_hier {current_hier} cols {cols}")
        data2 = data_orig[cols]
        data = data2.set_index(hier)
        hier_slash = "/".join(current_hier)
        sys.stdout.write(f"\n{hier_slash}: ")
        s += split_into_subtrees(data, current_hier, 1, x0, y0, x1, y1, item, area, quality, borders)
        y0 += margin + height
        y1 += margin + height
    s += "</svg>"
    return s

def split_into_subtrees(data, hier, level, x0, y0, x1, y1, text_field, area, quality, borders):
    #print(f"split_into_subtrees(data, {hier} level {level}, x0 {x0:5.2f}, y0 {y0:5.2f}, x0 {x1:5.2f}, y1 {y1:5.2f}, {text_field})")
    sys.stdout.write(str(level))
    sys.stdout.flush()
    rows = len(data.index)
    #print(f"rows {rows}")
    if rows == 0: # We have "split" a chunk of only one row into two chunks,
        # the second of which is obviously empty
        return ""
    #print(f"Level {level} len(hier) {len(hier)} rows {rows}")
    if rows == 1: # Now we have reached the bottom and can paint
        return paint_cell(data, x0, y0, x1, y1, text_field, area, quality, borders)
    if level == len(hier) + 1: # Maximum desired level of recursion
        return paint_cell(data, x0, y0, x1, y1, text_field, area, quality, borders)

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
    for name, group in data.groupby(current_hier)[area]:
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
        # todo Här verkar this_data bli tomt i vissa fall (rad i av tetris.csv)
        #print(f"typeof id {type(id)}")
        size = chunk[0]
        this_data = data_sorted[id:id]  # todo Denna blir tom då id = en månad!
        #print(f"id {id} size {size} tree 1 size {tree_1_size} len {len(data_1.index)} tree 2 size {tree_2_size} len {len(data_2.index)} this_data {this_data}")
        #      f" data_sorted {data_sorted}")
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
            s = split_into_subtrees(data_1, hier, level, x0, y0, x1, y_mid, text_field, area, quality, borders)
        if tree_2_size > 0:
            s += split_into_subtrees(data_2, hier, level, x0, y_mid, x1, y1, text_field, area, quality, borders)
    else:
        x_mid = x0 + first_share * (x1 - x0)
        if tree_1_size > 0:
            s = split_into_subtrees(data_1, hier, level, x0, y0, x_mid, y1, text_field, area, quality, borders)
        if tree_2_size > 0:
            s += split_into_subtrees(data_2, hier, level, x_mid, y0, x1, y1, text_field, area, quality, borders)
    return s

def paint_cell(data, x0, y0, x1, y1, text_field, area, quality, borders):

    # Find out colour of cell
    row = data.reset_index()
    quality_val = float(row[quality].mean())
    fg_color = "black"
    bg_color = borders[-1]["bg_color"]
    for limit_dict in borders:
        rule = limit_dict['rule']
        # last line is an "else" catch-up clause, if the value is empty
        if rule == "":
            break
        pot_bg_color = limit_dict["bg_color"]
        pot_fg_color = limit_dict["fg_color"]
        condition = rule[0]
        value = float(rule[1:])
        match = False
        if condition == ">":
            if quality_val > value:
                match = True
        elif condition == "=":
            if quality_val == value:
                match = True
        elif condition == "<":
            if quality_val < value:
                match = True
        #print(f"pot_bg {pot_bg_color} border {border} quality {quality_val} value {value} match {match}")
        if match:
            bg_color = pot_bg_color
            if pot_fg_color != "":
                fg_color = pot_fg_color
            break
    #print(f"quality_val {quality_val} condition {condition} value {value} bg_color {bg_color} pot {pot_bg_color}")

    fill_style = {'fill': bg_color}
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

    text_style = {'font-size': text_size, 'text-anchor': "middle", 'dominant-baseline': "central", 'fill': fg_color}
    s += svg.comment(f"{text}: max_point_size {max_point_size:.2f} textsize {text_size}")
    #s += svg.comment(f"- {text}: ratio {ratio:.2f} available width {available_width:.2f}")
    s += svg.plot_text_mm(x0 + available_width / 2, y0 + available_height / 2, text, text_style, angle=angle)
    #print(text)
    #row2 = row.values[0].astype(str)
    #row3 = map(str, row2)
    #row4 = ' '.join(row3)
    #print(f"bottom {row4} - ({x0:.2f}, {y0:.2f}) - ({x1:.2f}, {y1:.2f})")
    return s

commands_file = "tetris.xlsx"
cmds = pd.read_excel(commands_file, sheet_name='Commands')
cmds = cmds.replace(np.nan, '', regex=True)

for index, row in cmds.iterrows():
    active = row['active']
    sheet = row['sheet']
    if active == "#": # Commented out line, not to be executed
        continue
    outfile = sheet + "_" + str(index) + ".svg"
    hierstr = row['levels']
    hier = hierstr.replace(" ","").split(",")
    area = row['area']
    quality = row['quality']
    color_csv = row['colors']
    borders = []
    for i in range(1, 7):
        rule = row['rule' + str(i)]
        bg_color = row['bg_color' + str(i)]
        fg_color = row['fg_color' + str(i)]
        if bg_color != "":
            borders.append({"rule": rule, "bg_color": bg_color, "fg_color": fg_color})
    levels = "/".join(hier)
    print(f"\n{index}. {sheet} --> {outfile}: {levels} Area: {area} Quality: {quality}")

    config_files = {
        'Colors': {'filename': color_csv, 'item': 'Color',
                   'fields': 'color pf_color pass_1 hex pass_2 r g b'}}

    colors = lib.Config(**config_files['Colors'])
    _colors = {}
    for color in colors:
        _colors[color.color] = color.hex
    svg = kajsvg.SVG(_colors)

    a_str = tree_paint(sheet, hier, area, quality, borders)

    print("")
    lib.save_as(outfile, a_str, verbose=True)

#svg_filename = dict(
#    svg_icons='ge_svg_icons.svg',)
#_svg_icon_file = os.path.join(_config_file_dir, svg_filename['svg_icons'])

#_icon_dir = os.path.join(_py_dir, "svg")