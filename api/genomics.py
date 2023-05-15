# pagination
from flask import Flask, Blueprint
from flask_apispec import use_kwargs, marshal_with

from marshmallow import fields, Schema

blueprint = Blueprint("genomics_api", "genomics")

@blueprint.route('/genomics/variant')
@use_kwargs({'id': fields.Str(), 'size': fields.Str()})
@marshal_with(VariantSchema(many=True))
def get_pets(**kwargs):
    return [{"name": "Scooby", "category": "dog", "size": "large"}]