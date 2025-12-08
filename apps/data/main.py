from app.pipeline.flows import full_sync


def main():
    full_sync()

    full_sync.serve(cron="0 0 * * 1,3,5")


if __name__ == "__main__":
    main()
