from pydantic import field_serializer
from typing import List, Optional, TypeVar, Union

from niagads.reference.chromosomes import Human
from niagads.utils.list import find

from api.common.enums.response_properties import ResponseView
from api.common.formatters import id2title
from api.models.base_response_models import PagedResponseModel
from api.models.base_row_models import RowModel
from api.models.genome import Gene, GenomicRegion
from api.models.view_models import BadgeIcon, BooleanDataCell, FloatDataCell, LinkDataCell, PValueDataCell, TableColumn, TextDataCell
from api.routes.genomics.models.variant import PredictedConsequence, Variant

# TODO: NHGRI GWAS Catalog/ADVP data -> maybe just make VariantScore a `GenericDataModel`

class VariantScore(RowModel):
    variant: Variant
    test_allele: str
    track_id: str
    chromosome: Human
    position: int
    
    @field_serializer("chromosome")
    def serialize_group(self, chromosome: Human, _info):
        return str(chromosome)


T_VariantScore = TypeVar('T_VariantScore', bound=VariantScore)


class VariantPValueScore(VariantScore):
    p_value: Union[float, str]
    neg_log10_pvalue: float
    
    def get_field_names(self):
        """ get list of valid fields """
        
        fields = list(self.model_fields.keys())
        fields.remove('track_id')
        fields.remove('neg_log10_pvalue')
        
        variantFields = list(Variant.model_fields.keys())
        variantFields.remove('variant_id')
        variantFields.remove('most_severe_consequence')
        
        fields += variantFields + list(PredictedConsequence.model_fields.keys())
        
        # del fields['most_severe_consequence']
        # TODO: promote variant etc
        return fields
        
    def to_view_data(self, view: ResponseView, **kwargs):
        match view:
            case view.TABLE:
                data = self.serialize(promoteObjs=True)

                del data['track_id']

                if data['is_adsp_variant'] == True:
                    data['is_adsp_variant'] = BooleanDataCell(value=data['is_adsp_variant'], 
                        icon=BadgeIcon.SOLID_CHECK, displayText="ADSP", color="red")

                data['p_value'] = PValueDataCell(value=data['p_value'],
                    neg_log10_pvalue=data['neg_log10_pvalue'])
                del data['neg_log10_pvalue']
                
                data['variant'] = LinkDataCell(value=data['variant_id'], 
                    url=f'/variant/{data['variant_id']}')
                del data['variant_id']
                
                if data['most_severe_consequence'] is not None:
                    
                    data.update(data['most_severe_consequence'])
                    del data['most_severe_consequence']
                    
                    if data['impact'] is not None:
                        data['impact'] = TextDataCell(value=data['impact'],
                            color=PredictedConsequence.get_impact_color(data['impact']))
                    
                    if data['is_coding'] is not None:
                        if data['is_coding'] == True: 
                            data['is_coding'] = BooleanDataCell(value=data['is_coding'], 
                                icon=BadgeIcon.SOLID_CHECK, displayText="Coding", color="green")
                
                    if data['impacted_gene'] is not None:
                        data['impacted_gene'] = LinkDataCell(
                            value=data['impacted_gene']['gene_symbol'], 
                            url=f'/gene/{data['impacted_gene']['ensembl_id']}'
                    )
                
                return data
            case _:
                raise NotImplementedError(f'View `{view.value}` not yet supported for this response type')


    def get_view_config(self, view: ResponseView, **kwargs):
        """ get configuration object required by the view """
        match view:
            case view.TABLE:
                return self._build_table_config()
            #case view.IGV_BROWSER:
            #    return {} # config needs request parameters (span)
            case _:
                raise NotImplementedError(f'View `{view.value}` not yet supported for this response type')
        
        
    def _build_table_config(self):
        """ Return a column and options object for niagads-viz-js/Table """
        
        fields = self.get_field_names()       
        columns: List[TableColumn] = [ TableColumn(id= f, header=id2title(f)) for f in fields]
        for c in columns:
            if c.id == 'type':
                c.header = 'Variant Type'
            if c.id == 'variant':
                c.required = True
                c.type = 'link'
            if c.id == 'p_value':
                # c.type = 'p_value'
                c.type = 'float'
                c.required = True
            if c.id.startswith('is_'):
                c.type = 'boolean'
            if 'gene' in c.id:
                c.type = 'link'
            if 'target' in c.id: # FIXME find way to handle in child w/out iterative over all fields again
                c.required = True
                c.type = 'link'
            if 'z_score' in c.id:
                c.type = 'float'
        
        defaultColumns = ['variant', 'p_value', 'test_allele', 'ref_snp_id', 
            'is_adsp_variant', 'consequence', 'impact', 'is_coding',
            'impacted_gene'
        ]

        return {'columns': columns, 
            'options': { 'defaultColumns': defaultColumns }}
    
    
class QTL(VariantPValueScore):
    z_score: Optional[float] = None
    dist_to_target: Optional[float] = None
    target: Gene
    target_ensembl_id: str
    
    def to_view_data(self, view: ResponseView, **kwargs):
        data = super().to_view_data(view, **kwargs)
        data['target'] = LinkDataCell(value=data['gene_symbol'], 
            url=f'/gene/{data['ensembl_id']}')
        # data['z_score'] = FloatDataCell(value=data['z_score'], precision=2)
        del data['ensembl_id']
        del data['gene_symbol']
        return data
    
    def get_view_config(self, view: ResponseView, **kwargs):
        """ get configuration object required by the view """
        match view:
            case view.TABLE:
                return self.__build_table_config()
            #case view.IGV_BROWSER:
            #    return {} # config needs request parameters (span)
            case _:
                raise NotImplementedError(f'View `{view.value}` not yet supported for this response type')
        
        
    def __build_table_config(self):
        """ Return a column and options object for niagads-viz-js/Table """
        config = super()._build_table_config()
        defaultColumns = ['variant', 'ref_snp_id',  'p_value', 
            'is_adsp_variant', 'target', 'dist_to_target', 'z_score', 'consequence', 
        ]
        
        config['options']['defaultColumns'] = defaultColumns
        return config

class GWASSumStatResponse(PagedResponseModel):
    data: List[VariantPValueScore]
    
class QTLResponse(PagedResponseModel):
    data: List[QTL]
    
