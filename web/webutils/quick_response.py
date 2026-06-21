from flask import make_response


def quick_response(message: str, code: int):
    response = make_response(message)
    response.status_code = code
    return response
