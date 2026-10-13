#!/usr/bin/env python

import argparse
import asyncio
import os
from collections import defaultdict

from sqlalchemy import delete, select

from niagads.database import DatabaseSessionManager
from niagads.database.genomicsdb.schema.admin.etl import ETLRun
from niagads.database.genomicsdb.schema.variant.documents import Variant


async def main(commit=False):
    session_manager = DatabaseSessionManager(os.environ["DATABASE_URI"])
    duplicates = defaultdict(list)

    try:
        async with session_manager.session_ctx() as session:
            print("Querying GWASTrackLoader run IDs.")
            run_ids = await session.scalars(
                select(ETLRun.etl_run_id).where(
                    ETLRun.plugin_name == "GWASTrackLoader",
                    ETLRun.is_test_run.is_(False),
                    # ETLRun.rows_processed > 0,
                )
            )

            for run_id in run_ids:
                print(f"Querying variants for run {run_id}.")
                variants = await session.execute(
                    select(Variant).where(Variant.run_id == run_id)
                )

                for (variant,) in variants:
                    duplicates[variant.niagads_id].append(variant)

            duplicates = {
                niagads_id: variants
                for niagads_id, variants in duplicates.items()
                if len(variants) > 1
            }

            print(f"Found {len(duplicates)} duplicates.")

            variant_ids_to_delete = []
            for niagads_id, variants in duplicates.items():
                retained = min(
                    variants,
                    key=lambda variant: (
                        not variant.is_annotated,
                        variant.creation_date,
                        variant.variant_id,
                    ),
                )
                ids_to_delete = [
                    variant.variant_id
                    for variant in variants
                    if variant.variant_id != retained.variant_id
                ]
                variant_ids_to_delete.extend(ids_to_delete)
                print(f"{niagads_id}: {ids_to_delete}")

            if variant_ids_to_delete:
                print("Deleting duplicate variants.")
                await session.execute(
                    delete(Variant).where(Variant.variant_id.in_(variant_ids_to_delete))
                )
                if commit:
                    await session.commit()
                else:
                    await session.rollback()
    finally:
        await session_manager.close()

    print(f"num duplicates: {len(duplicates)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.commit))
