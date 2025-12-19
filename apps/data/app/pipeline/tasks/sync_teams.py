from time import sleep

import polars as pl
from prefect import task

from app.services import db, tba
from app.services.tba import _TBAEndpoint
from app.utils.batch_accumulator import BatchAccumulator


@task(
    name="Sync Teams",
    description="Sync FRC teams from The Blue Alliance",
    retries=2,
    retry_delay_seconds=10,
)
def sync_teams(batch_size: int = 5):
    accumulator = BatchAccumulator(batch_size=batch_size)

    page_num = 0
    max_pages = 50

    etags = db.get_etags(_TBAEndpoint.TEAMS)

    while page_num < max_pages:
        etag_key = _TBAEndpoint.TEAMS.build(page=str(page_num))
        result = tba.get_teams(
            page=page_num,
            etag=etags.get(etag_key),
        )

        if result is None:
            sleep(0.5)
            page_num += 1
            continue

        teams_df, etag = result

        if teams_df.is_empty():
            break

        accumulator.add_data("teams", teams_df)
        if etag:
            accumulator.add_etag(etag_key, etag)

        page_num += 1

        if accumulator.should_flush(page_num, max_pages):
            if accumulator.get_data("teams"):
                combined = pl.concat(accumulator.get_data("teams"))
                db.upsert(combined, table_name="teams", conflict_key="key")
                accumulator.clear_data("teams")

            if accumulator.etag_updates:
                combined = pl.DataFrame(accumulator.etag_updates)
                db.upsert(
                    combined,
                    table_name="etags",
                    conflict_key=["endpoint"],
                )

                accumulator.clear_etags()

        sleep(0.5)

    if accumulator.has_data():
        if accumulator.get_data("teams"):
            combined = pl.concat(accumulator.get_data("teams"))
            db.upsert(combined, table_name="teams", conflict_key="key")

        if accumulator.etag_updates:
            combined = pl.DataFrame(accumulator.etag_updates)
            db.upsert(
                combined,
                table_name="etags",
                conflict_key=["endpoint"],
            )
