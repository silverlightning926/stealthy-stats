import polars as pl


class BatchAccumulator:
    def __init__(self, batch_size: int):
        self.batch_size = batch_size
        self.data: dict[str, list[pl.DataFrame]] = {}
        self.etag_updates: list[dict[str, str]] = []

    def add_data(self, key: str, df: pl.DataFrame) -> None:
        if df.is_empty():
            return

        if key not in self.data:
            self.data[key] = []

        self.data[key].append(df)

    def add_etag(self, endpoint: str, etag: str) -> None:
        self.etag_updates.append({"endpoint": endpoint, "etag": etag})

    def should_flush(self, iteration: int, total: int) -> bool:
        return iteration % self.batch_size == 0 or iteration == total

    def has_data(self) -> bool:
        return bool(self.data) or bool(self.etag_updates)

    def get_data(self, key: str) -> list[pl.DataFrame]:
        return self.data.get(key, [])

    def clear_data(self, key: str) -> None:
        if key in self.data:
            self.data[key] = []

    def clear_etags(self) -> None:
        self.etag_updates = []
