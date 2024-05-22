from flask_smorest import Blueprint

from app import routes
from app.model.split_implementation_response import (
    SplitImplementationResponseSchema
)
from app.model.split_implementation_request import (
    SplitImplementationRequest,
    SplitImplementationRequestSchema
)

blp = Blueprint(
    "Split implementation",
    __name__,
    description="Send implementation and spliiting threshold to the API and get the result location.",
)


@blp.route("/qc-script-splitter/api/v1.0/split-implementation", methods=["POST"])
@blp.doc(description="*Note*: \"splitting-threshold\" is optional.")
@blp.arguments(
    SplitImplementationRequestSchema,
    example={
        "implementation-url": "https://raw.githubusercontent.com/UST-QuAntiL/nisq-analyzer-content/master/example-implementations"
                    "/Grover-SAT/grover-fix-sat-qiskit.py",
        "splitting-threshold": 5
    }
)

@blp.response(200, SplitImplementationResponseSchema, description="Returns a content location for the result. Access it via GET")
def encoding(json: SplitImplementationRequest):
    if json:
        return routes.execute_circuit()
