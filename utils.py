import json

import os
import random

import requests
import time
import re
from bs4 import BeautifulSoup
from pytube import YouTube
from tqdm import tqdm

import subprocess

SIROBUTTON_BASE = "https://sirobutton.herokuapp.com"

cmd2dir = {
    "いーね": "iine",
    "おほほい": "ohohoi",
    "🐬": "kyui",
    "ぱいーん": "pain",
    "シロ組さん": "sirogumisan",
    "救済": "kyuusai",
    "なんて日だ": "nantehida",
    "ズンドコ": "zundoko"
}

M3U8_FORMAT = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-MEDIA-SEQUENCE:0
#EXT-X-ALLOW-CACHE:YES
#EXT-X-TARGETDURATION:5

{parts}

#EXT-X-ENDLIST
"""

M3U8_PARTS_FORMAT = """
#EXTINF:-1, {name}
{file_path}
"""


class SiroButton:
    def __init__(self):
        self.data = {}
        self.__soup = {}

    @classmethod
    def __search(cls, word):
        return cls.__get(SIROBUTTON_BASE + "/sirobutton/?search=%s" % word)

    @staticmethod
    def __get(url):
        return BeautifulSoup(requests.get(url).text, 'html.parser')

    def __data_safe(self, word):
        if word not in self.data:
            self.data[word] = {}

    def set_soup(self, word):
        self.__data_safe(word)
        if not self.__is_souped(word):
            self.__soup[word] = self.__search(word)

    def set_button_list(self, word):
        self.__data_safe(word)
        if not self.__is_listed(word):
            self.set_soup(word)
            soup = self.__soup[word].find(id="main-buttons")
            self.data[word]["button_list"] = [self.__parser(s) for s in soup.find_all('li')]

    def set_complete_button_list(self, word):
        self.__data_safe(word)
        if not self.__is_listed(word):
            self.set_button_list(word)
        for item in self.data[word]["button_list"]:
            if "url" in item:
                continue
            bs = self.__get(item["detail_url"])
            item["url"] = "https://www.youtube.com/watch?v=" + self.__get_video_id(bs)
            item["t"] = {k: v for k, v in zip(("start", "end"), bs.find_all('dd')[-2].string.split("〜"))}
            item["use"] = False

    def get_json(self):
        return self.data

    def set_kyui(self):
        word = "🐬"
        self.__data_safe(word)
        self.set_button_list(word)
        self.data[word]["button_list"] = [i for i in self.data[word]["button_list"] if i["text"] == word]
        self.set_complete_button_list(word)

    @staticmethod
    def __parser(soup_li):
        a1, a2 = soup_li.find_all('a')
        return {"text": a1.string[2:-7], "detail_url": SIROBUTTON_BASE + a2["href"]}

    def __is_souped(self, word):
        return word in self.__soup

    def __is_listed(self, word):
        return "button_list" in self.data[word]

    @staticmethod
    def __get_video_id(bs):
        return bs.find('div', class_="video").iframe["src"].split("?")[0].split("/")[-1]

    def save_to_json(self, filename="button_data"):
        with open(filename+".json", "w") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2, sort_keys=True, separators=(',', ': '))


class SiroPlus:
    def __init__(self):
        self.command = None
        self.program = None
        self.__setup_cmd()

    def set_program(self, text):
        ptn = "(" + "|".join(list(self.command.keys())) + ")"
        self.program = re.findall(ptn, text)

    def generate(self, _random=True):
        parts = "".join([
            M3U8_PARTS_FORMAT.format(
                name=cmd,
                file_path=self.command[cmd]["path"]+random.choice(self.command[cmd]["list"])
            )
            for cmd in self.program
        ])
        return M3U8_FORMAT.format(parts=parts)

    def __setup_cmd(self):
        self.command = {
            "いーねっ！": {"text": "いーね"},
            "おほほい": {"text": "おほほい"},
            "ｷｭｰｲ": {"text": "🐬"},
            "ぱいーん": {"text": "ぱいーん"},
            "白組さん": {"text": "シロ組さん"},
            "救済": {"text": "救済"},
            "なんて日だ！": {"text": "なんて日だ"},
            "ズンドコズンドコ♪": {"text": "ズンドコ"}
        }
        for item in self.command.values():
            item["path"] = "resource/" + cmd2dir[item["text"]] + "/"
            item["list"] = os.listdir(item["path"])


def create_json_data():
    sb = SiroButton()
    sb.set_complete_button_list("いーね")
    sb.set_complete_button_list("おほほい")
    sb.set_kyui()
    sb.set_complete_button_list("ぱいーん")
    sb.set_complete_button_list("シロ組さん")
    sb.set_complete_button_list("救済")
    sb.set_complete_button_list("なんて日だ")
    sb.set_complete_button_list("ズンドコ")
    sb.save_to_json()


def youtube_dl(url: str, name: str = None):
    dir_path = "./tmp/videos"
    if not os.path.isdir(dir_path):
        os.makedirs(dir_path)

    # rename the value of v of query
    name = url.split("?v=")[-1] if name is None else name

    # youtubeから動画をdl
    yt = YouTube(url)
    yt.streams.filter(subtype='mp4').first().download(dir_path, filename=name)


def download_button_videos(button):
    if not button["use"]:
        return
    if not os.path.exists("./tmp/videos/" + button["url"].split("?v=")[-1] + ".mp4"):
        youtube_dl(button["url"])
        time.sleep(7)


def set_resource():
    if not os.path.exists("button_data.json"):
        raise FileNotFoundError("create_json_data()関数実行してからやってね")

    with open("button_data.json", 'r') as f:
        data = json.load(f)

    for key, val in data.items():
        for button in tqdm(val['button_list']):
            download_button_videos(button)
            button["full_video"] = "./tmp/videos/" + button["url"].split("?v=")[-1] + ".mp4"

    with open("button_data.json", "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True, separators=(',', ': '))


def slice_video(video_path: str, out_path: str, start: float, end: float):
    t = str(end - start)
    subprocess.call(["ffmpeg", "-ss", str(start), "-i", video_path, "-t", t, out_path])


def create_cmd_rdir():
    os.makedirs('./resource/' + cmd2dir["いーね"])
    os.makedirs('./resource/' + cmd2dir["おほほい"])
    os.makedirs('./resource/' + cmd2dir["🐬"])
    os.makedirs('./resource/' + cmd2dir["ぱいーん"])
    os.makedirs('./resource/' + cmd2dir["シロ組さん"])
    os.makedirs('./resource/' + cmd2dir["救済"])
    os.makedirs('./resource/' + cmd2dir["なんて日だ"])
    os.makedirs('./resource/' + cmd2dir["ズンドコ"])


def coordinate_time(t: str):
    h, m, s = list(map(float, t.split(':')))
    return 60*60*h + 60*m + s


def create_command(button, filename):
    if not button["use"]:
        return
    start, end = list(map(coordinate_time, (button["t"]["start"], button["t"]["end"])))
    slice_video(button["full_video"], filename, start, end)


def set_command_resource():
    create_cmd_rdir()

    with open("button_data.json", 'r') as f:
        data = json.load(f)

    for cmd, val in data.items():
        for i, button in enumerate(tqdm(val['button_list'])):
            create_command(button, "./resource/"+cmd2dir[cmd]+"/cmd"+str(i)+".mp4")


def siropp_parser(text):
    spp = SiroPlus()
    spp.set_program(text)
    return spp.generate()


if __name__ == '__main__':
    # create_json_data()
    # set_resource()
    # set_command_resource()
    print(siropp_parser("いーねっ！おほほいおほほいおほほいおほほいおほほいおほほいおほほいおほほいおほほい白組さんｷｭｰｲおほほいおほほい"))
