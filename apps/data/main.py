from datetime import timedelta

from prefect import serve

from app.pipeline.flows import full_sync, live_sync


def main():
    full_sync()

    full_sync_deployment = full_sync.to_deployment(
        name="full-sync-deployment", cron="0 0 * * 1,3,5"
    )

    live_sync_deployment = live_sync.to_deployment(
        name="live-sync-deployment", interval=timedelta(minutes=10)
    )

    serve(full_sync_deployment, live_sync_deployment)  # type: ignore


if __name__ == "__main__":
    main()
