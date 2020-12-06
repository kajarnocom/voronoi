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
    input_tab = "orter"
    print(f"add_wp_to_wd: Verifying {input_spreadsheet}")
    xl = pd.ExcelFile(input_spreadsheet)
    sheet_names = xl.sheet_names
    if not input_tab in sheet_names:
        print(f"add_wp_to_wd.py error: Could not find sheet {input_tab}' in file "
              f"{input_spreadsheet}")
        sys.exit(0)

    print(f"add_wp_to_wd: reading {input_spreadsheet} / {input_tab}")
    df_personer = pd.read_excel(input_spreadsheet, sheet_name=input_tab)
    df_personer['person'] = np.arange(len(df_personer))
    df_personer['person'] = df_personer['person'].astype(str)
    return df_personer


def add_stats(df_personer, res, languages):
    # Move results to dict that can be assigned to df_personer
    stats_by_wd = {}
    for p in res:
        wd_q_kod = p['person']
        for l in languages:
            for f in ['pageviews', 'size']:
                fldname = f"{l}_{f}"
                combi_fld = f"{wd_q_kod}{fldname}"
                stats_by_wd[combi_fld] = p.get(fldname, 0)

    print(stats_by_wd)
    # Assign fields to df_personer
    for l in languages:
        for f in ['pageviews', 'size']:
            fldname = f"{l}_{f}"
            df_personer[fldname] = df_personer.apply(
                lambda row: stats_by_wd[row['person'] + fldname], axis=1)

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
            res_dict[f'{lang}_size'] = res
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
            res_dict[f'{lang}_pageviews'] = res
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
    input_spreadsheet = "Orter.xlsx"

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

df_personer = add_stats(df_personer, res, languages)

sheet_name = "add_wp_to_wd"
output_spreadsheet = input_spreadsheet.replace(".xlsx", "-output.xlsx")
df_personer.to_excel(output_spreadsheet, sheet_name)
print(f"Created {output_spreadsheet} / {sheet_name}")