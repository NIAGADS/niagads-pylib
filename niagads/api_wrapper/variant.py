class Variant:
    def __init__(self, requestUrl, queryVariants=None):
        self.__requestUrl = requestUrl
        self.__queryVariants = self.set_query_variants(queryVariants)

    def set_request_url(self, url):
        self.__requestUrl = url
        
    def get_request_url(self):
        return self.__requestUrl
    
    def set_query_variants(self, queryVariants):
        self.__queryVariants = self.__parse_variants(queryVariants)
    
    def get_query_variants(self, returnStr=False):
        return self.__queryVariants if not returnStr else ','.join(self.__queryVariants)
    
    def get_query_size(self):
        return 0 if self.__queryVariants is None else len(self.__queryVariants)