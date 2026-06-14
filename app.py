from waterleaf.runtime import build_application
from waterleaf.web import create_web_app

application = build_application()
app = create_web_app(application)

