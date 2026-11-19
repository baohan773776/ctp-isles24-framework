"""Seekable read-only file over HTTP range requests, so pyarrow can read single
parquet columns from the Hugging Face ISLES'24 mirror without downloading whole files."""
import io
import time
import requests

HF = "https://huggingface.co/datasets/hugging-science/isles24-stroke/resolve/main/data/"


def shard_url(i):
    return f"{HF}train-{i:05d}-of-00149.parquet"


class HTTPFile(io.RawIOBase):
    def __init__(self, url, session=None):
        self.url = url
        self.s = session or requests.Session()
        r = self.s.head(url, allow_redirects=True, timeout=60)
        r.raise_for_status()
        self.url = r.url  # follow the CDN redirect once
        self.size = int(r.headers["Content-Length"])
        self.pos = 0
        self.bytes_read = 0

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, off, whence=0):
        self.pos = {0: off, 1: self.pos + off, 2: self.size + off}[whence]
        return self.pos

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.size - self.pos
        n = min(n, self.size - self.pos)
        if n <= 0:
            return b""
        for attempt in range(5):
            try:
                r = self.s.get(self.url, headers={"Range": f"bytes={self.pos}-{self.pos + n - 1}"}, timeout=120)
                if r.status_code == 403:  # signed CDN URL expired: re-resolve
                    self.url = self.s.head(shard_url_from(self.url), allow_redirects=True, timeout=60).url
                    continue
                r.raise_for_status()
                b = r.content
                break
            except requests.RequestException:
                time.sleep(2 * (attempt + 1))
        else:
            raise IOError(f"range read failed: {self.url}")
        self.pos += len(b)
        self.bytes_read += len(b)
        return b

    def readinto(self, buf):
        b = self.read(len(buf))
        buf[:len(b)] = b
        return len(b)


def shard_url_from(url):
    name = url.split("?")[0].rsplit("/", 1)[-1]
    return HF + name
