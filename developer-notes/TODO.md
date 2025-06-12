# API TODOS

```log
http://localhost:3000/view/table?endpoint=/v1/filer/metadata/search/&keyword=brain&filter=feature_type%20eq%20histone%20modification&view=table
returning mismatched columns/fields

http://localhost:8000/v1/filer/metadata/search?keyword=brain&filter=feature_type%20eq%20histone%20modification&view=table

49 items, 50 columns
```


* fix filter queries
* self.model_fields is deprecated for Pydantic -> look into this; see [track.py](../../components/niagads/open_access_api_common/models/data/track.py) for example

