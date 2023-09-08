import logging
from sys import stdout
from niagads.api_wrapper.records import Record

class Variant(Record):
    def __init__(self, requestUrl, database, variantIds=None):
        super().__init__(self, 'variant', requestUrl, variantIds)
        self.__full = False # retrieve full annotation?
        self.__query_variants = None 
        self.set_ids(self._ids) # initializes query_variants
        
    def retrieve_full_annotation(self, flag=True):
        """
        retrieve full annotation? if set to false (default for variant lookups)
        only basic annotation: identifiers, most severe predicted consequence
        will be retrieved
        
        full annotation includes: ADSP QC, allele frequencies, CADD scores, 
        all predicted consequences

        Args:
            flag (bool, optional): flag indicating whether to retrieve full annotation. Defaults to True.
        """
        self.__full = flag
        
    def set_ids(self, ids):
        """
        overloads parent `set_ids` to clean variant ids 
        and create the user -> cleaned id mapping
        """
        self._ids = ids
        self.__query_variants = self.__parse_variant_ids(ids)

    def __clean_variant_id(self, id):
        """
        clean variant ids
            -- remove 'chr'
            -- replace 'MT' with 'M'
            -- replace 'RS' with 'rs'
            -- replace '/' with ':' (e.g., chr:pos:ref/alt)
            -- replace '_' with ':' (e.g., chr:pos:ref_alt)

        Args:
            id (string): variant identifier (expects rsId or chr:pos:ref:alt)

        Returns:
            _type_: _description_
        """
        return id.replace('chr', '').replace('MT','M') \
            .replace('RS', 'rs').replace('/', ':').replace('_', ':')
 
    def __parse_variant_ids(self, variantIds):
        """
        create mapping of user supplied variant id : cleaned id for lookups

        Args:
            queryVariants (string list): list of variants

        Returns:
            dict : cleaned id -> id mapping
        """
        return { self.__clean_variant_id(id): id for id in variantIds }
    
    def run(self):
        params = {} if self._params is None else self._params
        if self.__full is not None:
            self.set_params(params | {"full": self.__full})
        super().run()
        
    def __write_tabular_response(self, file):
        raise NotImplementedError("Not yet implemented")
        
    def write_response(self, file=stdout, format=None):
        if format is None:
            format = self._response_format
        if format == 'json':
            return super().write_response(file, format)
        else:
            return self.__write_tabular_response(file)