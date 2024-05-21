from app.controller import split_implementation, result

MODULES = (split_implementation, result)

def register_blueprints(api):
    """Initialize application with all modules"""
    for module in MODULES:
        api.register_blueprint(module.blp)
