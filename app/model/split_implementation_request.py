import marshmallow as ma

class SplitImplementationRequest:
    def __init__(self, implementation_url, splitting_threshold):
        self.implementation_url = implementation_url
        self.splitting_threshold = splitting_threshold


class SplitImplementationRequestSchema(ma.Schema):
    implementation_url = ma.fields.String()
    splitting_threshold = ma.fields.String(required=False)
