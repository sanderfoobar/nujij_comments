from nujij_comments.factory import create_app
import settings

app = create_app()
app.run(settings.WEB_BIND_HOST, settings.WEB_BIND_PORT, debug=settings.DEBUG, use_reloader=False)
