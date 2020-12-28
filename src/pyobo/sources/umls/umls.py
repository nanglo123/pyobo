# -*- coding: utf-8 -*-

"""Converter for UMLS.

Run with ``python -m pyobo.sources.umls``
"""

import itertools as itt
import operator
import os
import zipfile

import click
import pandas as pd
from tqdm import tqdm

from ...identifier_utils import normalize_prefix
from ...io_utils import open_map_tsv
from ...path_utils import ensure_path
from ...struct import Obo, Reference, Synonym, SynonymTypeDef, Term

HERE = os.path.abspath(os.path.dirname(__file__))
SYNONYM_TYPE_PATH = os.path.join(HERE, 'synonym_types.tsv')

RRF_COLUMNS = [
    'CUI',
    'LAT - Language',
    'TS - Term Status',
    'LUI - Local Unique Identifier',
    'STT - String Type',
    'SUI - Unique Identifier for String',
    'ISPREF - is preferred',
    'AUI - Unique atom identifier',
    'SAUI - Source atom identifier',
    'SCUI - Source concept identifier',
    'SDUI - Source descriptor identifier',
    'SAB - source name',
    'TTY - Term Type in Source',
    'CODE',
    'STR',
    'SRL',
    'SUPPRESS',
    'CVF',
    '?',
]

PREFIX = 'umls'
VERSION = '2020AA'
SOURCE_VOCAB_URL = 'https://www.nlm.nih.gov/research/umls/sourcereleasedocs/index.html'
URL = 'https://download.nlm.nih.gov/umls/kss/2020AA/umls-2020AA-mrconso.zip'

synonym_abb = open_map_tsv(SYNONYM_TYPE_PATH)


def get_obo() -> Obo:
    """Get UMLS as OBO."""
    return Obo(
        iter_terms=iter_terms,
        name='Unified Medical Language System',
        ontology=PREFIX,
        synonym_typedefs=[
            SynonymTypeDef.from_text(v)
            for v in synonym_abb.values()
        ],
        auto_generated_by=f'bio2obo:{PREFIX}',
        data_version=VERSION,
    )


def iter_terms():
    """Iterate over UMLS terms."""
    # FIXME needs automated scrapy step where you put in user/password
    path = ensure_path(PREFIX, url=URL, version=VERSION)
    with zipfile.ZipFile(path) as zip_file:
        with zip_file.open('MRCONSO.RRF', mode='r') as file:
            it = tqdm(file, unit_scale=True, desc='[umls] parsing')
            lines = (
                line.decode('utf-8').strip().split('|')
                for line in it
            )
            for cui, cui_lines in itt.groupby(lines, key=operator.itemgetter(0)):
                df = pd.DataFrame(list(cui_lines), columns=RRF_COLUMNS)
                df = df[df['LAT - Language'] == 'ENG']
                idx = (
                    (df['ISPREF - is preferred'] == 'Y')
                    & (df['TS - Term Status'] == 'P')
                    & (df['STT - String Type'] == 'PF'),
                )
                pref_rows_df = df.loc[idx]
                if len(pref_rows_df.index) != 1:
                    it.write(f'no preferred term for umls:{cui}. got {len(pref_rows_df.index)}')
                    continue

                df['TTY - Term Type in Source'] = df['TTY - Term Type in Source'].map(synonym_abb.__getitem__)

                _r = pref_rows_df.iloc[0]
                sdf = df[['SAB - source name', 'CODE', 'TTY - Term Type in Source', 'STR']]

                synonyms = []
                xrefs = []
                for source, identifier, synonym_type, synonym in sdf.values:
                    norm_source = normalize_prefix(source)
                    if norm_source is None or not identifier:
                        provenance = []
                    else:
                        ref = Reference(prefix=norm_source, identifier=identifier)
                        provenance = [ref]
                        xrefs.append(ref)
                    synonyms.append(Synonym(
                        name=synonym,
                        provenance=provenance,
                        type=SynonymTypeDef.from_text(synonym_type),
                    ))

                xrefs = sorted(set(xrefs), key=lambda reference: (reference.prefix, reference.identifier))

                term = Term(
                    reference=Reference(prefix=PREFIX, identifier=cui, name=_r['STR']),
                    synonyms=synonyms,
                    xrefs=xrefs,
                )
                yield term


@click.command()
def main():
    """Cache the OBO content."""
    get_obo().write_default()


if __name__ == '__main__':
    main()
