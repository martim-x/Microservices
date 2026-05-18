from fastapi import Response


def cache_dep(ttl: int = 3600):
    def wrapper(response: Response):
        response.headers["Cache-Control"] = f"max-age={ttl}"
        return response

    return wrapper
