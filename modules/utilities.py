import re

def parse_text_for_imdb_ids(text):
    return re.findall(r'imdb.com/[\w\/]*title/(tt[\d]{7})/?',text)