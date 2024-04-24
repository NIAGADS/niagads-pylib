#!/usr/bin/env python3

import argparse
from niagads.db.postgres.postgres_async import AsyncDatabase 
from niagads.filer.parser import FILERMetadataParser


if __name__ == 'main':
    argparser = argparse.parser()
    argparser