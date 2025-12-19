import polars as pl


class BatchAccumulator:
    def __init__(self, batch_size: int):
        self._batch_size = batch_size
        self._data: dict[str, list[pl.DataFrame]] = {}
        self._etags: list[dict[str, str]] = []

    def add_data(self, key: str, df: pl.DataFrame) -> None:
        if df.is_empty():
            return

        if key not in self._data:
            self._data[key] = []

        self._data[key].append(df)

    def get_data(self, key: str) -> list[pl.DataFrame]:
        return self._data.get(key, [])

    def clear_data(self, key: str) -> None:
        if key in self._data:
            self._data[key] = []

    def add_etag(self, endpoint: str, etag: str) -> None:
        self._etags.append({"endpoint": endpoint, "etag": etag})

    def get_etags(self) -> list[dict[str, str]]:
        return self._etags

    def has_etags(self) -> bool:
        return bool(self._etags)

    def clear_etags(self) -> None:
        self._etags = []

    def should_flush(self, iteration: int, total: int) -> bool:
        return iteration % self._batch_size == 0 or iteration == total

    def has_data(self) -> bool:
        return bool(self._data) or bool(self._etags)
