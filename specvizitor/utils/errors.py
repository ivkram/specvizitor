def error_message(e: BaseException) -> str:
    # str() of a KeyError is the repr of its argument, i.e. the message wrapped in quotes
    if isinstance(e, KeyError) and len(e.args) == 1:
        return str(e.args[0])
    return str(e)
