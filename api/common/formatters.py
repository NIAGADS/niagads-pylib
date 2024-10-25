
def id2title(columnId: str):
    title = columnId.title().replace('_', ' ')
    title = title.replace('Id', 'ID').replace('Of', 'of').replace('Md5Sum', 'md5sum')
    title = title.replace('Url', 'URL').replace('Bp ', 'BP ')
    return title