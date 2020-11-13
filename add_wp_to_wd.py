#!/usr/bin/env python
# -*- coding: latin-1 -*-

"""
Add Wikipedia statistics (pageviews, size) to Wikidata xlsx made with sparql
"""

import pandas as pd
import numpy as np
import httpx
import asyncio
import json
import sys
import os

def process_wd_personer(input_spreadsheet):
    # Verify that the input sheet exists
    input_tab = "wd-personer"
    prio_tab = "wd-personer-prioritet"
    places_tab = "wd-place"
    print(f"add_wp_to_wd: Verifying {input_spreadsheet}")
    xl = pd.ExcelFile(input_spreadsheet)
    sheet_names = xl.sheet_names
    if not input_tab in sheet_names:
        print(f"add_wp_to_wd.py error: Could not find sheet {input_tab}' in file "
              f"{input_spreadsheet}")
        sys.exit(0)
    if not prio_tab in sheet_names:
        print(f"add_wp_to_wd.py error: Could not find sheet {prio_tab}' in file "
              f"{input_spreadsheet}")
        sys.exit(0)
    if not places_tab in sheet_names:
        print(f"add_wp_to_wd.py error: Could not find sheet {places_tab}' in file "
              f"{input_spreadsheet}")
        sys.exit(0)

    print(f"add_wp_to_wd: reading {input_spreadsheet} / {input_tab}")
    df_personer = pd.read_excel(input_spreadsheet, sheet_name=input_tab)
    print(f"add_wp_to_wd: reading {input_spreadsheet} / {prio_tab}")
    df_prio = pd.read_excel(input_spreadsheet, sheet_name=prio_tab)

    print(f"add_wp_to_wd: condensing {input_tab} by occupation")
    # Add 'prio' column (for occupation priority) to df_personer
    prio_by_occupation = {}
    for i, row in df_prio.iterrows():
        occupation = row['occupationLabel']
        prio_by_occupation[occupation] = i
    prio_by_occupation[''] = len(prio_by_occupation) + 1
    df_personer = df_personer.replace(np.nan, '', regex=True)
    df_personer['prio'] = df_personer.apply(
        lambda row: prio_by_occupation[row['occupationLabel']], axis=1)

    # Condense df_personer, picking highest-prio occupation
    df_personer = df_personer.sort_values(['personLabel', 'prio'])
    df_personer = df_personer.drop_duplicates(subset='personLabel', keep="first")

    print(f"add_wp_to_wd: adding new fields")
    for event in ['birth', 'death']:
        df_personer[f'{event}date'] = df_personer.apply(
            lambda row: str(row[f'{event}dateLabel']), axis=1)
        df_personer[f'{event}date'] = df_personer.apply(
            lambda row: row[f'{event}date'][0:10]
            if len(row[f'{event}date'])>10 else row[f'{event}date'], axis=1)
        df_personer[f'{event}year'] = df_personer.apply(
            lambda row: row[f'{event}date'][0:4]
            if len(row[f'{event}date'])>4 else row[f'{event}date'], axis=1)
        df_personer[f'{event}century'] = df_personer.apply(
            lambda row: row[f'{event}date'][0:2] + "00"
            if len(row[f'{event}date'])>2 else row[f'{event}date'], axis=1)
        del df_personer[f'{event}dateLabel']
    del df_personer['prio']

    print(f"add_wp_to_wd: reading {input_spreadsheet} / {places_tab}")
    df_places = pd.read_excel(input_spreadsheet, sheet_name=places_tab)
    df_places = df_places.replace(np.nan, '', regex=True)
    levels_by_place= {}
    for i, row in df_places.iterrows():
        l1 = row['landskap']
        l2 = row['landskapsdel']
        l3 = row['kommun']
        l4 = row['ort']
        levels_by_place[l4] = [l1, l2, l3]
    levels_by_place[''] = ['', '', '']
    for event in ['birth', 'death']:
        df_personer[f'{event}_landskap'] = df_personer.apply(
            lambda row: levels_by_place[row[f'{event}placeLabel']][0], axis=1)
        df_personer[f'{event}_landskapsdel'] = df_personer.apply(
            lambda row: levels_by_place[row[f'{event}placeLabel']][1], axis=1)
        df_personer[f'{event}_kommun'] = df_personer.apply(
            lambda row: levels_by_place[row[f'{event}placeLabel']][2], axis=1)

    return df_personer


def find_languages(wd_sheet):
    languages = []
    for fld in wd_sheet.columns:
        if "_title" in fld:
            languages.append(fld[0:2])
    return languages


async def get_wp_stat(title, lang, stat, client, res_dict):
    url = f"https://{lang}.wikipedia.org/w/api.php?"
    if stat == 'size':
        params = {'action': 'query', 'format': 'json', 'titles': title,
                  'prop': 'revisions', 'rvprop': 'size'}
        r = await client.get(url, params = params)
        try:
            res_pages = list(r.json()['query']['pages'].values())
            res = res_pages[0]['revisions'][0]['size']
            res_dict['size'] = res
            print(f"title {title} lang {lang} size {res}")
        except KeyError as e:
            print(f"Error with {e} for page {title} / {stat}: {r.json()}")
        except json.decoder.JSONDecodeError as e:
            print(f"Problem with json data for {title} / {stat}: {e}")
    elif stat == 'pageviews':
        params = {'action': 'query', 'format': 'json', 'titles': title,
                  'prop': 'pageviews'}
        r = await client.get(url, params = params)
        try:
            res_pages = list(r.json()['query']['pages'].values())
            pageviews = res_pages[0]['pageviews'].values()
            res = sum([int(x) for x in pageviews if x and str(x).isdigit()])
            res_dict['pageviews'] = res
            print(f"title {title} lang {lang} pageviews {res}")
        except KeyError as e:
            print(f"Error with {e} for page {title} / {stat}: {r.json()}")
        except json.decoder.JSONDecodeError as e:
            print(f"Problem with json data for {title} / {stat}: {e}")
    else:
        print("add_wp_to_wd only supports 'pageviews' and 'size'")
        return 0

async def get_wp_stats():
    tasks = []
    async with httpx.AsyncClient(timeout=None) as client:
        for p in res:
            for l in languages:
                title = p[f'{l}_title']
                if title != "":
                    tasks.append(get_wp_stat(title, l, 'pageviews', client, p))
                    tasks.append(get_wp_stat(title, l, 'size', client, p))
        await asyncio.gather(*tasks)

# Identify right input file
parameter_given = len(sys.argv) > 1
if parameter_given:
    input_spreadsheet = sys.argv[1]
else:
    input_spreadsheet = "voronoi.xlsx"

# Verify that the input file exists
if not os.path.exists(input_spreadsheet):
    print(f"add_wp_to_wd.py error: Could not find input file {input_spreadsheet} "
          f"(cwd = {os.getcwd()})")
    sys.exit(0)
else:
    print(f"add_wp_to_wd.py: Opening {input_spreadsheet} (cwd = {os.getcwd()})")

df_personer = process_wd_personer(input_spreadsheet)
res = df_personer.to_dict("records")

languages = find_languages(df_personer)
print(languages)

print(f"add_wp_to_wd asyncio starting to get stats; will take a while...")
asyncio.run(get_wp_stats())

sheet_name = "add_wp_to_wd"
output_spreadsheet = input_spreadsheet.replace(".xlsx", "-output.xlsx")
df_personer.to_excel(output_spreadsheet, sheet_name)
print(f"Created {output_spreadsheet} / {sheet_name}")