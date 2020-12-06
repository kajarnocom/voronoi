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

def process_corpus(input_spreadsheet):
    # Verify that the input sheet exists
    input_tab = "core_corpus"
    print(f"beslaktade: Verifying {input_spreadsheet}")
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


def to_list(dict):
    # Move results to dict that can be assigned to df_personer
    lst = ['']
    nr = 0
    for l in dict:
        for pg in dict[l]['pages']:
            nr += 1
            l_to = dict[l]['pages'][pg]['to']
            l_from = dict[l]['pages'][pg]['from']
            row = {'nr': nr, 'title': pg, 'lang': l, 'to': l_to, 'from': l_from}
            row2 = (nr, pg, l, l_to, l_from)
            lst.append(row2)
    return lst


def find_languages(wd_sheet):
    languages = []
    for fld in wd_sheet.columns:
        if "_title" in fld:
            languages.append(fld[0:2])
    return languages


async def get_links(title, lang, stat, client, res_dict):
    url = f"https://{lang}.wikipedia.org/w/api.php?"
    #print(f"get_links {title} {lang} {stat}")
    if stat == 'links':
        to_from = 'from'
    elif stat == 'linkshere':
        to_from = 'to'
    else:
        print("beslaktade only supports 'links' and 'linkshere'")
        return 0
    params = {'action': 'query', 'format': 'json', 'titles': title,
              'prop': stat}
    r = await client.get(url, params = params)
    try:
        res_pages = list(r.json()['query']['pages'].values())
        cnt = len(res_pages)
        if cnt> 1:
            print(f"len({title} ({lang}) = {len}")
        article_links = res_pages[0][stat]
        for lnk in article_links:
            lnk_title = lnk['title']
            lnk_missing = links[lang]['pages'].get(lnk_title) == None
            if lnk_missing:
                links[lang]['pages'][lnk_title] = {'to': 0, 'from': 0}
            links[lang]['pages'][lnk_title][to_from] += 1
            #print(f"title {lnk_title} {links[lang]['pages'][lnk_title][to_from]}")
    except KeyError as e:
        print(f"Error with {e} for page {title} / {stat}: {r.json()}")
    except json.decoder.JSONDecodeError as e:
        print(f"Problem with json data for {title} / {stat}: {e}")

async def get_all_links():
    tasks = []
    async with httpx.AsyncClient(timeout=None) as client:
        for p in res:
            for l in languages:
                title = p[f'{l}_title']
                if isinstance(title, str):
                    tasks.append(get_links(title, l, 'links', client, p))
                    tasks.append(get_links(title, l, 'linkshere', client, p))
        await asyncio.gather(*tasks)

# Identify right input file
parameter_given = len(sys.argv) > 1
if parameter_given:
    input_spreadsheet = sys.argv[1]
else:
    input_spreadsheet = "Core_corpus.xlsx"

# Verify that the input file exists
if not os.path.exists(input_spreadsheet):
    print(f"add_wp_to_wd.py error: Could not find input file {input_spreadsheet} "
          f"(cwd = {os.getcwd()})")
    sys.exit(0)
else:
    print(f"add_wp_to_wd.py: Opening {input_spreadsheet} (cwd = {os.getcwd()})")

df_corpus = process_corpus(input_spreadsheet)
res = df_corpus.to_dict("records")

languages = find_languages(df_corpus)
print(languages)

links = {}
for lang in ['sv', 'fi', 'en', 'de']:
    links[lang] = {'pages': {}}

print(f"beslaktade asyncio starting to get stats; will take a while...")
asyncio.run(get_all_links())

#print(links)
link_list = to_list(links)

labels = ['nr', 'title', 'lang', 'to', 'from']
df_links = pd.DataFrame.from_records(link_list, columns=labels)
print(df_links)
sheet_name = "links"
output_spreadsheet = input_spreadsheet.replace(".xlsx", "-output.xlsx")
df_links.to_excel(output_spreadsheet, sheet_name)
print(f"Created {output_spreadsheet} / {sheet_name}")