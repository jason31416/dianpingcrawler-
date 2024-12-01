import os, sys, csv, json, time
from utils import cache, cities
from function import detail, search

s = search.Search()
d = detail.Detail()

meta = {"pagecount": 34, "current_task": [], "cookie": "", "progress": {}}
if os.path.exists("data/meta.json"):
    with open("data/meta.json", "r") as fl:
        dct = json.load(fl)
        for i in dct:
            meta[i] = dct[i]
if not os.path.exists("data"):
    os.mkdir("data")

cache.cookie = meta["cookie"]

def get_or_default(dc, key, default):
    if key in dc:
        return dc[key]
    else:
        return default

current_step = ""

def print_bar():
    print("\r\033[32m"+"-\\|/"[int(time.time()*4)%4]+" "+current_step+" "+cache.current_substep, end="")

cache.print_bar = print_bar

def get_search_url(cur_page, city_id, keyword='冰淇淋'):
    base_url = 'http://www.dianping.com/search/keyword/' + city_id + '/0_' + keyword + '/p'

    if cur_page == 1:
        return base_url + "1", 'proxy, cookie'
    else:
        return base_url + str(cur_page), 'proxy, cookie'

def crawl(city):
    global current_step, substep
    city_code = cities.cities[city]

    for page in range(meta["pagecount"]):
        if city in meta["progress"] and meta["progress"][city] > page:
            continue
        else:
            meta["progress"][city] = page
        with open("data/meta.json", "w") as fl:
            json.dump(meta, fl)
        current_step = "Crawling "+city+", Page "+str(page+1)+"/"+str(meta["pagecount"])
        cache.current_substep = ""
        print_bar()

        try:
            cache.current_substep = "(Pulling shop list)"
            search_url, request_type = get_search_url(page, str(city_code), "冰淇淋")
            search_res = s.search(search_url, request_type)
            if not search_res:
                break
            for each_search_res in search_res:

                need_header = not os.path.exists("data/"+city+".csv")
                with open("data/"+city+".csv", "a") as fl:
                    writer = csv.DictWriter(fl, each_search_res)
                    if need_header:
                        writer.writeheader()
                    writer.writerow(each_search_res)
            if len(search_res) == 0:
                break
        except Exception as e:
            raise e
            print("\r\033[31m", e, "\033[0m")

print("\033[36m欢迎使用Dianping Crawler ++ \033[34mBy Jason31416 forked from sniper970119/dianping_spider")

print("\033[37m仅供学习用途!\033[0m")

while True:
    if input("Confirm start crawling (y/n): ") == "y":
        while meta["current_task"]:
            crawl(meta["current_task"][0])
            meta["current_task"].pop(0)
    print("\nAdd city to the queue (press enter to start crawling):")
    while True:
        c = input(">> ")
        if c == "":
            break
        if c in cities.cities.keys():
            meta["current_task"].append(c)
        elif c.split(" ")[0] == "setcookie":
            meta["cookie"] = input("Please enter cookie for authorization: ")
        elif c.split(" ")[0] == "setcookie":
            meta["pagecount"] = int(input("How many pages do we crawl: "))
        elif c.split(" ")[0] == "help":
            print("- Directly enter chinese name of a city to add it to the queue")
            print("- setcookie <cookie>")
            print("- setpages <pagecount>")
            print("- help")
        else:
            print("\033[31mUnknown city!\033[0m")
    if meta["cookie"] == "":
        meta["cookie"] = input("Please enter cookie for authorization: ")
    with open("data/meta.json", "w") as fl:
        json.dump(meta, fl)