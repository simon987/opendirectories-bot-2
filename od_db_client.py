import requests
import json
import re
import humanfriendly
import time

from od_database.od_util import truncate_path


class OdDatabase:

    def __init__(self, url, token):

        self.url = url
        self.token = token

    @staticmethod
    def perform_request(url, method="GET", data=None, json_data=None):

        try:
            if json_data:
                return requests.request("POST", url, data=json_data, headers={"Content-Type": "application/json"})
            else:
                return requests.request(method, url, data=data)
        except Exception as e:
            print(e)
            return None

    def website_by_url(self, url):

        r = self.perform_request(self.url + "website/by_url?token=" + self.token + "&url=" + url)
        if not r or r.status_code != 200:
            return None

        return int(r.text)

    def website_is_blacklisted(self, url):

        r = self.perform_request(self.url + "website/blacklisted?token=" + self.token + "&url=" + url)
        if not r or r.status_code != 200:
            return False
        return r.text == "True"

    def add_website(self, url):

        r = self.perform_request(self.url + "website/add?token=" + self.token + "&url=" + url)
        if not r or r.status_code != 200:
            return None
        return int(r.text)

    def enqueue(self, website_id=None, url=None, priority=1, callback_type="", callback_args=""):

        data = json.dumps({
            "token": self.token,
            "website_id": website_id,
            "url": url,
            "priority": priority,
            "callback_type": callback_type,
            "callback_args": callback_args
        })
        r = self.perform_request(self.url + "task/force_enqueue", json_data=data)

        if not r or r.status_code != 200:
            return False
        return True

    def search(self, q, p, per_page, sort_order, extensions, size_min, size_max, match_all, fields, date_min, date_max):

        data = json.dumps({
            "token": self.token,
            "query": q,
            "page": p,
            "per_page": per_page,
            "sort_order": sort_order,
            "extensions": extensions,
            "size_min": size_min,
            "size_max": size_max,
            "match_all": match_all,
            "fields": fields,
            "date_min": date_min,
            "date_max": date_max
        })

        r = self.perform_request(self.url + "search", json_data=data)

        if not r or r.status_code != 200:
            return None
        return json.loads(r.text)

    @staticmethod
    def format_search_hits(hits, query):

        message = str(hits["hits"]["total"]) + " matches found in " + str(hits["took"]) + "ms for query `" + query + "`"
        if hits["hits"]["total"] > 0:
            message += ":    \n\n"
            message += "File | Size | Date     \n"
            message += ":-- | :-- | --:    \n"

            for hit in hits["hits"]["hits"]:
                src = hit["_source"]

                # File name highlight
                if "name" in hit["highlight"]:
                    hl_name = format_highlight(hit["highlight"]["name"][0])
                elif "name.nGram" in hit["highlight"]:
                    hl_name = format_highlight(hit["highlight"]["name.nGram"][0])
                else:
                    hl_name = src["name"]

                message += "[" + src["website_url"] + "](https://od-db.the-eye.eu/website/" + str(src["website_id"]) + "/).../"
                message += hl_name + ("." if src["ext"] else "") + src["ext"] + " | "
                message += humanfriendly.format_size(src["size"]) + "    \n"
        else:
            message += "\n"

        message += "\n[More results for this query](https://od-db.the-eye.eu/search?q=" + query + ") |" \
                   " [OD-Database](https://od-db.the-eye.eu/)"

        return message

    def get_stats(self, website_id):
        r = self.perform_request(self.url + "../website/" + str(website_id) + "/json_chart")
        return json.loads(r.text)


def format_highlight(text):

    text = re.sub("(<mark>)", "**", text)
    text = re.sub("(<mark>)\s+", " **", text)
    text = re.sub("(</mark>)", "**", text)
    text = re.sub("\s+(</mark>)", "** ", text)

    return text





