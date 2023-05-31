import argparse
import collections
import os
import sys
import time
import requests as requests

API_VERSION = "5.131"
IMG_PREFIX = "img"


class VKApi:
    def __init__(self, user_id, access_token):
        self.user_id = user_id
        self.access_token = access_token

    """FOR NEWS"""

    def get_news(self, start_time, end_time, count):
        request = f"https://api.vk.com/method/newsfeed.get?v={API_VERSION}" + \
                  f"&q=news" + \
                  f"&start_time={start_time}" + \
                  f"&end_time={end_time}" + \
                  f"&count={count}" + \
                  f"&owner_id={self.user_id}" + \
                  f"&access_token={self.access_token}"
        response = requests.get(request).json()
        if "error" in response:
            print("Error getting news: ", response["error"]["error_msg"])
            return []
        news_items = response["response"]["items"]
        news_items.sort(key=lambda x: x.get("likes", {}).get("count", 0), reverse=True)

        i = 1
        for news_item in news_items:
            photos = news_item.get("attachments")
            photo_urls = []
            if photos:
                for photo in photos:
                    if photo["type"] == "photo":
                        photo_url = photo["photo"]["sizes"][-1]["url"]
                        photo_urls.append(photo_url)
            text = news_item.get("text")
            if text:
                print(f"{i}. {text}")
                if photo_urls:
                    for photo_url in photo_urls:
                        print(photo_url)
            i += 1

    """FOR PHOTOS"""

    def get_photos_from_album(self, target_id, album_id):
        photos = []
        request = f"https://api.vk.com/method/photos.get?v={API_VERSION}" + \
                  f"&owner_id={target_id}" + \
                  f"&album_id={album_id}" + \
                  f"&access_token={self.access_token}"
        response = requests.get(request).json()
        if "error" not in response:
            response = response["response"]
            photos = response["items"]
        else:
            print("This album does not exist or is private")
        return photos

    @staticmethod
    def save_photos(photos, directory):
        if len(photos) == 0:
            print("Album does not have photo")
            return
        urls = []
        for photo in photos:
            max_quality = 0
            cur_url = ""
            for size in photo["sizes"]:
                cur_quality = size["height"] * size["width"]
                if cur_quality > max_quality:
                    max_quality = cur_quality
                    cur_url = size["url"]
            urls.append(cur_url)

        if not os.path.exists(f"{directory}"):
            os.mkdir(f"{directory}")

        for counter, url in enumerate(urls, start=1):
            p = requests.get(url)
            out = open(f"{directory}/{IMG_PREFIX}{counter}.jpg", "wb")
            out.write(p.content)
            out.close()

    def download_images(self):
        print("Enter the ID target you want to download pictures from: ")
        target_id = input()
        if not is_valid_user_id(target_id):
            print("Invalid id")
            exit()
        print("Enter album ID: ")
        album_id = input()
        if not is_valid_user_id(album_id):
            print("Invalid album id")
            exit()
        self.save_photos(api.get_photos_from_album(target_id, album_id), album_id)

    """FOR FRIENDS"""

    def get_friends(self, user_id):
        request = f"https://api.vk.com/method/friends.get?v={API_VERSION}" + \
                  f"&user_id={user_id}" + \
                  f"&fields=city" + \
                  f"&count=6" + \
                  f"&access_token={self.access_token}"
        response = requests.get(request).json()
        response = response["response"]["items"]

        return response

    def sort_friends(self, friends):
        rating = {}
        for friend in friends:
            request = f"https://api.vk.com/method/friends.get?v={API_VERSION}" + \
                      f"&user_id={friend['id']}" + \
                      f"&access_token={self.access_token}"
            response = requests.get(request).json()
            if "error" in response:
                continue
            time.sleep(0.4)  # не больше 3 запросов в секунду...
            count = response["response"]["count"]
            likes = 0
            request = f"https://api.vk.com/method/photos.get?v={API_VERSION}" + \
                      f"&owner_id={friend['id']}" + \
                      f"&album_id=profile" + \
                      f"&extended=1" + \
                      f"&access_token={self.access_token}"
            response = requests.get(request).json()
            if "error" in response:
                continue
            photos = response["response"]["items"]
            for photo in photos:
                likes += photo["likes"]["count"]
            rating[friend["id"]] = {"rate": count + likes, "name": f"{friend['first_name']} {friend['last_name']}"}
        sys.stderr.write("\r\n")
        return dict(sorted(rating.items(), key=lambda item: item[1]["rate"], reverse=True))

    """FOR AUDIO"""

    def get_audio(self, user_id):
        request = f"https://api.vk.com/method/audio.get?v={API_VERSION}" + \
                  f"&owner_id={user_id}" + \
                  f"&access_token={self.access_token}"
        response = requests.get(request).json()
        if "error" in response:
            print("Error getting audio: ", response["error"]["error_msg"])
            return []
        return response["response"]["items"]

    def audio_genres_statistics(self, user_id):
        audio_list = self.get_audio(user_id)
        genres_count = collections.defaultdict(int)
        for audio in audio_list:
            genres_count[audio["genre_id"]] += 1
        return dict(sorted(genres_count.items(), key=lambda x: x[1], reverse=True))


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--photos", action="store_true", help="download images from album")
    parser.add_argument("--friends", action="store_true", help="get top of friends")
    parser.add_argument("--audio", action="store_true", help="statistics on the genres of music")
    parser.add_argument("--news", action="store_true", help="get news within a specified time frame")
    return parser.parse_args()


def is_valid_user_id(param):
    return param.isdigit()


def print_top_of_friend(friends):
    i = 1
    for key, value in friends.items():
        print(f"{i}. {value['name']}: rating {value['rate']}")
        i += 1


if __name__ == "__main__":
    args = get_args()
    try:
        print("Enter your VK ID: ")
        u_id = input()
        if not is_valid_user_id(u_id):
            print("Invalid user id")
            exit()
        u_id = int(u_id)

        print("Enter your access token: ")
        a_token = str(input())
        api = VKApi(u_id, a_token)

        if args.friends:
            print_top_of_friend(api.sort_friends(api.get_friends(u_id)))
        if args.photos:
            api.download_images()
        if args.audio:
            genre_stats = api.audio_genres_statistics(u_id)
            for genre_id, count in genre_stats.items():
                print(f"Genre {genre_id}: {count} tracks")
        if args.news:
            print("Enter start time (Unix timestamp)")
            start_time = input()
            if not is_valid_user_id(start_time):
                print("Invalid start time")
                exit()
            print("Enter end time (Unix timestamp)")
            end_time = input()
            if not is_valid_user_id(end_time):
                print("Invalid end time")
                exit()
            print("Enter count of news")
            count = input()
            if not is_valid_user_id(count):
                print("Invalid count")
                exit()
            news_items = api.get_news(start_time, end_time, int(count))

    except KeyboardInterrupt:
        exit()

# time1 1684084835
# time2 1684088000
