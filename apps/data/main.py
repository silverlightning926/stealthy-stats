from datetime import timedelta

from app.pipeline.flows import full_sync, live_sync


def main():
    full_sync()

    full_sync.serve(cron="0 0 * * 1,3,5")
    live_sync.serve(
        interval=timedelta(
            minutes=3,
        )
    )


if __name__ == "__main__":
    main()
