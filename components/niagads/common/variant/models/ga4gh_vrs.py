"""Simplified Pydantic models for GA4GH VRS variant representations.

This module provides streamlined data models for representing genetic variations
following GA4GH VRS (Variation Representation Specification) concepts, without
the full GA4GH library dependencies. Models include sequence expressions (literal,
reference length, and length-based) and sequence locations for representing alleles
and other molecular variations.

See https://vrs.ga4gh.org/ for more information on VRS.
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional, Union
from enum import Enum


class SequenceExpressionType(str, Enum):
    """Types of sequence expressions"""

    LITERAL = "LiteralSequenceExpression"
    REFERENCE_LENGTH = "ReferenceLengthExpression"
    LENGTH = "LengthExpression"


class SequenceExpression(BaseModel):
    """Base sequence expression"""

    type: SequenceExpressionType
    sequence: Optional[str] = None


class LiteralSequenceExpression(SequenceExpression):
    """An explicit expression of a sequence"""

    type: Literal[SequenceExpressionType.LITERAL] = SequenceExpressionType.LITERAL
    sequence: str = Field(..., description="The literal sequence")


class ReferenceLengthExpression(SequenceExpression):
    """An expression of a length from a repeating reference"""

    type: Literal[SequenceExpressionType.REFERENCE_LENGTH] = (
        SequenceExpressionType.REFERENCE_LENGTH
    )
    length: int | tuple[Optional[int], Optional[int]] = Field(
        ..., description="The number of residues in the sequence"
    )
    repeatSubunitLength: int = Field(
        ..., description="The number of residues in the repeat subunit"
    )


class LengthExpression(SequenceExpression):
    """A sequence expressed only by its length"""

    type: Literal[SequenceExpressionType.LENGTH] = SequenceExpressionType.LENGTH
    length: int | tuple[Optional[int], Optional[int]] = Field(
        ..., description="The length of the sequence"
    )


class SequenceReference(BaseModel):
    """Reference to a sequence (e.g., RefGet accession)"""

    type: Literal["SequenceReference"] = Field(
        "SequenceReference", description="GA4GH VRS type"
    )
    refgetAccession: str = Field(
        ..., description="RefGet accession for the reference sequence"
    )


class SequenceLocation(BaseModel):
    """A location defined by an interval on a sequence (GA4GH VRS-compliant)"""

    type: Literal["SequenceLocation"] = Field(
        "SequenceLocation", description="GA4GH VRS type"
    )
    id: Optional[str] = Field(
        default=None, description="Optional identifier for the location"
    )
    digest: Optional[str] = Field(default=None, description="Digest for the location")
    sequenceReference: Optional[SequenceReference] = Field(
        default=None,
        description="Reference to a sequence (GA4GH SequenceReference object)",
    )
    # reference_sequence_id: Optional[str] = Field(
    #     default=None,
    #     description="Reference to a sequence (legacy field, e.g., RefGet accession)",
    # )
    start: int | tuple[Optional[int], Optional[int]] = Field(
        ..., description="The start coordinate or range"
    )
    end: int | tuple[Optional[int], Optional[int]] = Field(
        ..., description="The end coordinate or range"
    )
    sequence: Optional[str] = Field(
        default=None, description="The literal sequence at this location"
    )


class Allele(BaseModel):
    """The state of a molecule at a location (GA4GH VRS-compliant)"""

    type: Literal["Allele"] = Field("Allele", description="GA4GH VRS type")
    id: Optional[str] = Field(
        default=None, description="Optional identifier for the allele"
    )
    digest: Optional[str] = Field(default=None, description="Digest for the allele")
    location: Union[str, SequenceLocation] = Field(
        ..., description="The location of the allele"
    )
    state: Union[
        LiteralSequenceExpression, ReferenceLengthExpression, LengthExpression
    ] = Field(..., description="An expression of the sequence state")
