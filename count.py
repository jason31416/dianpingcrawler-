import csv, os

cnt=0
for i in os.listdir("data"):
    if i.split(".")[1] == "csv":
        with open("data/"+i, "r") as fl:
            dct = [i for i in csv.DictReader(fl)]
            cnt+=len(dct)

print("已经爬取了", cnt, "条数据")
