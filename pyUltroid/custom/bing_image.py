# Written by dot arc (@moiusrname)
# Bing Scrapper Source: https://github.com/gurugaurav/bing_image_downloader

import asyncio
import imghdr
from functools import partial
from pathlib import Path
from random import choice, shuffle
from re import match, search, findall
from urllib.parse import quote_plus, unquote

import aiohttp

from .. import LOGS
from ..fns import some_random_headers
from ..fns.misc import split_list
from ..fns.helper import (
    _get_filename_from_url,
    async_searcher,
    check_filename,
    run_async,
)


_IMG_EXTS = (".jpg", ".jpeg", ".exif", ".gif", ".bmp", ".png", ".webp", ".jpe", ".tiff")


class BingScrapper:
    def __init__(self, query, limit, hide_nsfw=True, filter=None):
        assert bool(query), "No query provided.."
        assert type(limit) == int, "limit must be of type Integer"
        self.query = query
        self.limit = limit
        self.page_counter = 0
        self.hide_nsfw = "on" if bool(hide_nsfw) else "off"
        self.url_args = self._filter_to_args(filter)
        self.headers = {
            "User-Agent": choice(some_random_headers),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Charset": "ISO-8859-1,utf-8;q=0.7,*;q=0.3",
            "Accept-Encoding": "none",
            "Accept-Language": "en-US,en;q=0.8",
            "Connection": "keep-alive",
        }

    def _filter_to_args(self, shorthand):
        if not shorthand:
            return ""
        shorthand = shorthand.lower()
        if shorthand in ("line", "linedrawing"):
            return "&qft=+filterui:photo-linedrawing"
        elif shorthand == "photo":
            return "&qft=+filterui:photo-photo"
        elif shorthand == "clipart":
            return "&qft=+filterui:photo-clipart"
        elif shorthand in ("gif", "animatedgif"):
            return "&qft=+filterui:photo-animatedgif"
        elif shorthand == "transparent":
            return "&qft=+filterui:photo-transparent"
        else:
            return ""

    @run_async
    def _save_to_file(self, filename, content):
        with open(filename, "wb+") as f:
            f.write(content)

    async def _handle_request(self, filename, response):
        if response.status < 207:
            image_data = await response.read()
            if imghdr.what(None, image_data):
                await self._save_to_file(filename, image_data)

    async def save_image(self, link):
        if match(r"^https?://(www.)?bing.com/th/id/OGC", link):
            if re_search := search(r"&amp;rurl=(.+)&amp;ehk=", link):
                link = unquote(re_search.group(1))
        filename = _get_filename_from_url(link, self.output_path)
        ext = Path(filename).suffix
        if not (ext and ext in _IMG_EXTS):
            filename += ".jpg"
        try:
            await async_searcher(
                link,
                raise_for_status=True,
                timeout=aiohttp.ClientTimeout(total=8),
                evaluate=partial(self._handle_request, filename),
            )
        except (asyncio.TimeoutError, aiohttp.ClientResponseError):
            pass
        except Exception as exc:
            LOGS.debug(f"Bing: Error in downloading {link}", exc_info=True)

    async def get_links(self):
        cached_urls = set()
        while len(cached_urls) < self.limit:
            extra_args = f"&first={self.page_counter}&count={self.limit}&adlt={self.hide_nsfw}{self.url_args}"
            request_url = f"https://www.bing.com/images/async?q={quote_plus(self.query)}{extra_args}"
            response = await async_searcher(request_url, headers=self.headers)
            if response == "":
                LOGS.info(
                    f"No more Image available for {self.query}. Page - {self.page_counter} | Downloaded - {len(cached_urls)}"
                )
                assert bool(cached_urls), f"Could not find any Images for {self.query}"
                return self._evaluate_links(cached_urls)

            img_links = findall("murl&quot;:&quot;(.*?)&quot;", response)
            for url in img_links:
                cached_urls.add(url)
            self.page_counter += 1

        assert bool(cached_urls), f"Could not find any Images for {self.query}"
        return self._evaluate_links(cached_urls)

    def _evaluate_links(self, links):
        links = list(links)
        shuffle(links)
        return links[: self.limit]

    async def download(self):
        self.output_path = check_filename(f"resources/downloads/bing-{self.query}")
        Path(self.output_path).mkdir(parents=True)
        url_list = await self.get_links()
        dl_list = [url_list] if len(url_list) <= 6 else split_list(url_list, 6)
        for collection in dl_list:
            await asyncio.gather(
                *[self.save_image(url) for url in collection],
                return_exceptions=True,
            )

        return self.output_path
