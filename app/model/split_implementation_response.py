import marshmallow as ma

class SplitImplementationResponseSchema(ma.Schema):
    location = ma.fields.String()

    @property
    def input(self):
        raise NotImplementedError

class SplitImplementationResponseSchema(ma.Schema):
    result = ma.fields.List(ma.fields.String())
