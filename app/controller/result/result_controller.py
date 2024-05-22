from flask_smorest import Blueprint

from app.model.split_implementation_response import (
    SplitImplementationResponseSchema
)


blp = Blueprint(
    "Results",
    __name__,
    description="",
)


@blp.route("/qc-script-splitter/api/v1.0/results/<id>", methods=["GET"])
@blp.response(200, SplitImplementationResponseSchema)
def encoding(json):
    if json:
        return
