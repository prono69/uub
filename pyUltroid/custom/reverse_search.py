# written by @moiusrname (dot arc)

import json
import time
from random import choice
from re import search as re_search, sub as re_sub

import requests
from bs4 import BeautifulSoup

from pyUltroid import LOGS
from pyUltroid.fns.helper import run_async
from pyUltroid.fns.misc import some_random_headers, string_is_url


class GoogleReverseSearch:
    __slots__ = ("url",)

    def __init__(self):
        self.url = "https://lens.google.com"

    @classmethod
    async def init(cls, to_search, similar_results=True):
        # similar_results doesn't do anything rn
        self = cls()
        if string_is_url(to_search):
            raw_data = await self.search_by_url(to_search)
        else:
            raw_data = await self.search_by_file(to_search)

        parsed_data = self.data_parser(raw_data)
        del raw_data
        return self.generate_output(parsed_data, similar_results)

    def data_parser(self, response):
        souped_data = GoogleReverseSearch._script_parser(response)
        return self.cleanup_response(souped_data)

    @staticmethod
    def _script_parser(response):
        soup = BeautifulSoup(response, "html.parser")

        _data = list(
            filter(
                lambda s: (
                    "AF_initDataCallback(" in s.text
                    and re_search(r"key: 'ds:(\d+)'", s.text).group(1) == "0"
                ),
                soup.find_all("script"),
            )
        )[0].text

        _data = _data.replace("AF_initDataCallback(", "").replace(");", "")
        hash = re_search(r"hash: '(\d+)'", _data).group(1)
        _data = _data.replace(
            f"key: 'ds:0', hash: '{hash}', data:",
            f'"key": "ds:0", "hash": "{hash}", "data":',
        ).replace("sideChannel:", '"sideChannel":')

        try:
            _data = json.loads(_data)
            return _data["data"][1]
        except Exception:
            LOGS.exception("Error in reverse_search, '_script_parser':")

    def generate_output(self, parsed_data, extra):
        data = {"match": {}, "similar": []}
        base_index0 = (
            parsed_data[0][0][0][3]
            if type(parsed_data[0][0][0]) == list
            else parsed_data[0]
        )
        base_index1 = (
            parsed_data[0][2][0]
            if type(parsed_data[0][2]) == list
            else parsed_data[0][2]
        )
        tmp_dict = {
            "title": (0, (0, 0)),
            "info": (0, (0, 1)),
            "search_url": (0, (1, 1)),
            "thumbnail": (1, (0,)),
            "page_url": (1, (4,)),
        }

        if len(parsed_data) == 1:
            if "No results for" in base_index0[0][0]:
                return data
            elif base_index0[0][0] == "Visual matches":
                # no search results, only similar images..
                pass
        else:
            for k, v in tmp_dict.items():
                index, v = v
                try:
                    tmp_data = base_index0 if index == 0 else base_index1
                    for i in v:
                        tmp_data = tmp_data[i]
                except (IndexError, TypeError):
                    continue
                else:
                    data["match"][k] = tmp_data

        return data

        # todo: add similar images thingy
        """
        if not extra:
            return data

        try:
            if data.get("match"):
                visual_matches = parsed_data[8][0][12]
            else:
                visual_matches = parsed_data[8][0][12]

            for match in visual_matches:
                data["similar"].append(
                    {
                        "title": match[3],
                        "thumbnail": match[0][0],
                        "pageURL": match[5],
                        "sourceWebsite": match[14],
                    }
                )
        except (IndexError, TypeError):
            pass

        return data
        """

    # todo: find a better way to do this ;-;
    @staticmethod
    def _fixup_list(sub_list):
        del_count = 0
        for index, i in enumerate(sub_list.copy()):
            _index = index - del_count
            if not i:
                del sub_list[_index]
                del_count += 1
            elif type(i) == list:
                if new := GoogleReverseSearch._fixup_list(i):
                    sub_list[_index] = new
                else:
                    del sub_list[_index]
                    del_count += 1

        if not sub_list:
            return None
        elif len(sub_list) == 1 and type(sub_list[0]) == list:
            return sub_list[0]
        else:
            return sub_list

    def cleanup_response(self, data):
        out_dict = {}
        for index, i in enumerate(filter(bool, data.copy())):
            if type(i) != list:
                out_dict[index] = i
            else:
                if new_data := GoogleReverseSearch._fixup_list(i):
                    out_dict[index] = new_data

        return out_dict

    @run_async
    def search_by_file(self, file_path):
        headers = {"User-agent": choice(some_random_headers)}
        with open(file_path, "rb") as f:
            response = requests.post(
                self.url + "/upload",
                headers=headers,
                files={"encoded_image": (file_path, f), "image_content": ""},
                allow_redirects=False,
            )
        search_url = (
            BeautifulSoup(response.text, "html.parser")
            .find("meta", {"http-equiv": "refresh"})
            .get("content")
        )
        search_url = re_sub("^.*URL='", "", search_url).replace("0; URL=", "")

        time.sleep(1)
        response = requests.get(search_url, headers=headers)
        return response.text

    @run_async
    def search_by_url(self, url):
        headers = {"User-agent": choice(some_random_headers)}
        response = requests.get(
            self.url + "/uploadbyurl",
            params={"url": url},
            headers=headers,
            allow_redirects=True,
        )
        return response.text
