import nh3 # XSS protection
# TODO: investigate nh3 and alternatives to set cleaning options more accurately

def id2title(columnId: str):
    title = columnId.title().replace('_', ' ')
    title = title.replace('Id', 'ID').replace('Of', 'of').replace('Md5Sum', 'md5sum')
    title = title.replace('Url', 'URL').replace('Bp ', 'BP ')
    return title

def clean(html: str):
    return nh3.clean_text(html)

def convert_str2list(param: str):
    return clean(param).split(',')
