# for Heroku ;_;

Heroku = {}


def herokuapp(Var):
    try:
        import heroku3
    except ImportError:
        Heroku["err"] = "'heroku3' module not installed"
        return

    api_key, app_name = Var.HEROKU_API, Var.HEROKU_APP_NAME
    try:
        if api_key and app_name:
            _heroku = heroku3.from_key(api_key)
            _myapp = _heroku.app(app_name)
            Heroku.update(
                {
                    "api": _heroku,
                    "app": _myapp,
                    "api_key": api_key,
                    "app_name": app_name,
                }
            )
            return
        else:
            Heroku["err"] = "`HEROKU_API` or `HEROKU_APP_NAME` var is missing."
            return

    except BaseException as err:
        from . import LOGS

        Heroku["err"] = "Your Heroku 'Data' is Wrong!"
        return LOGS.exception(err)
