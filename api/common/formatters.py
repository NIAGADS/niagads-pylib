import nh3 # XSS protection
# TODO: investigate nh3 and alternatives to set cleaning options more accurately

def id2title(columnId: str):
    title = columnId.title().replace('_', ' ')
    title = title.replace('Id', 'ID').replace('Of', 'of').replace('Md5Sum', 'md5sum')
    title = title.replace('Url', 'URL').replace('Bp ', 'BP ')
    if title.startswith('Is '):
        title = title + '?'
    return title

def clean(html: str):
    return nh3.clean_text(html)

def print_enum_values(enumClass):
    return ','.join([f'`{m.value}`' for m in enumClass])