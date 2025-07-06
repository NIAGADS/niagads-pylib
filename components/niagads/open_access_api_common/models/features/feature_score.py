from niagads.common.models.views.table import TableColumn
from niagads.database.schemas.variant.composite_attributes import PredictedConsequence
from niagads.genome.core import Human
from niagads.open_access_api_common.models.core import RowModel
from niagads.open_access_api_common.models.features.gene import GeneFeature
from niagads.open_access_api_common.models.features.variant import (
    Variant,
    VariantFeature,
)
from niagads.open_access_api_common.models.response.core import RecordResponse

from niagads.open_access_api_common.parameters.response import ResponseView
from pydantic import Field, field_serializer
from typing import List, Optional, TypeVar, Union

# TODO: NHGRI GWAS Catalog/ADVP data -> maybe just make VariantScore a `DynamicRowModel`


class VariantScore(RowModel):
    variant: Variant = Field(title="Variant")
    test_allele: str = Field(title="Test Allele")
    track_id: str = Field(title="Track")
    chromosome: Human = Field(title="Chromosome")
    position: int = Field(title="Position")

    @field_serializer("chromosome")
    def serialize_chromosome(self, chromosome: Human, _info):
        return str(chromosome)


T_VariantScore = TypeVar("T_VariantScore", bound=VariantScore)


class VariantPValueScore(VariantScore):
    p_value: Union[float, str] = Field(title="p-Value")
    neg_log10_pvalue: float = Field(title="-log10pValue")
    trait: str

    def get_field_names(self):
        """get list of valid fields"""

        fields = list(self.__class__.model_fields.keys())
        fields.remove("track_id")
        fields.remove("neg_log10_pvalue")

        variantFields = list(VariantFeature.model_fields.keys())
        variantFields.remove("variant_id")
        variantFields.remove("most_severe_consequence")

        fields += variantFields + list(PredictedConsequence.model_fields.keys())

        # del fields['most_severe_consequence']
        # TODO: promote variant etc
        return fields

    def to_view_data(self, view: ResponseView, **kwargs):
        match view:
            case view.TABLE:
                data = self.model_dump()

                # FIXME: promote objs
                """
                del data["track_id"]

                if data["is_adsp_variant"] == True:
                    data["is_adsp_variant"] = BooleanTableCell(
                        value=data["is_adsp_variant"],
                        displayText="ADSP",
                        color="red",
                    )

                data["p_value"] = PValueTableCell(
                    value=data["p_value"], neg_log10_pvalue=data["neg_log10_pvalue"]
                )
                del data["neg_log10_pvalue"]

                data["variant"] = LinkTableCell(
                    value=data["variant_id"], url=f"/variant/{data['variant_id']}"
                )
                del data["variant_id"]

                if data["most_severe_consequence"] is not None:

                    data.update(data["most_severe_consequence"])
                    del data["most_severe_consequence"]

                    if data["impact"] is not None:
                        data["impact"] = TextTableCell(
                            value=data["impact"],
                            color=PredictedConsequence.get_impact_color(data["impact"]),
                        )

                    if data["is_coding"] is not None:
                        if data["is_coding"] == True:
                            data["is_coding"] = BooleanTableCell(
                                value=data["is_coding"],
                                displayText="Coding",
                                color="green",
                            )

                    if data["impacted_gene"] is not None:
                        data["impacted_gene"] = LinkTableCell(
                            value=data["impacted_gene"]["gene_symbol"],
                            url=f"/gene/{data['impacted_gene']['ensembl_id']}",
                        )
                """
                return data
            case _:
                raise NotImplementedError(
                    f"View `{view.value}` not yet supported for this response type"
                )

    def get_view_config(self, view: ResponseView, **kwargs):
        """get configuration object required by the view"""
        match view:
            case view.TABLE:
                return self._build_table_config()
            # case view.IGV_BROWSER:
            #    return {} # config needs request parameters (span)
            case _:
                raise NotImplementedError(
                    f"View `{view.value}` not yet supported for this response type"
                )

    def _build_table_config(self):
        """Return a column and options object for niagads-viz-js/Table"""

        fields = self.get_field_names()
        columns: List[TableColumn] = [
            TableColumn(id=f, header=id2title(f)) for f in fields
        ]
        for c in columns:
            if c.id == "type":
                c.header = "Variant Type"
            if c.id == "variant":
                c.required = True
                c.type = "link"
            if c.id == "p_value":
                # c.type = 'p_value'
                c.type = "float"
                c.required = True
            if c.id.startswith("is_"):
                c.type = "boolean"
            if "gene" in c.id:
                c.type = "link"
            if (
                "target" in c.id
            ):  # FIXME find way to handle in child w/out iterative over all fields again
                c.required = True
                c.type = "link"
            if "z_score" in c.id:
                c.type = "float"

        defaultColumns = [
            "variant",
            "p_value",
            "test_allele",
            "ref_snp_id",
            "is_adsp_variant",
            "consequence",
            "impact",
            "is_coding",
            "impacted_gene",
        ]

        return {"columns": columns, "options": {"defaultColumns": defaultColumns}}


class QTL(VariantPValueScore):
    z_score: Optional[float] = None
    dist_to_target: Optional[float] = None
    target: GeneFeature
    target_ensembl_id: str

    def to_view_data(self, view: ResponseView, **kwargs):
        data = super().to_view_data(view, **kwargs)
        """
        data["target"] = LinkTableCell(
            value=data["gene_symbol"], url=f"/gene/{data['ensembl_id']}"
        )
        """
        # data['z_score'] = FloatDataCell(value=data['z_score'], precision=2)
        del data["ensembl_id"]
        del data["gene_symbol"]
        return data

    def get_view_config(self, view: ResponseView, **kwargs):
        """get configuration object required by the view"""
        match view:
            case view.TABLE:
                return self.__build_table_config()
            # case view.IGV_BROWSER:
            #    return {} # config needs request parameters (span)
            case _:
                raise NotImplementedError(
                    f"View `{view.value}` not yet supported for this response type"
                )

    def __build_table_config(self):
        """Return a column and options object for niagads-viz-js/Table"""
        config = super()._build_table_config()
        defaultColumns = [
            "variant",
            "ref_snp_id",
            "p_value",
            "is_adsp_variant",
            "target",
            "dist_to_target",
            "z_score",
            "consequence",
        ]

        config["options"]["defaultColumns"] = defaultColumns
        return config


class GWASSumStatResponse(RecordResponse):
    data: List[VariantPValueScore]


class QTLResponse(RecordResponse):
    data: List[QTL]
