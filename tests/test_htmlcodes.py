# -*- coding: utf-8 -*-

from utilities.htmlcodes import (
    HTTP_CONTINUE,
    HTTP_SWITCHING_PROTOCOLS,
    HTTP_OK_BASIC,
    HTTP_OK_CREATED,
    HTTP_OK_ACCEPTED,
    HTTP_OK_NORESPONSE,
    HTTP_PARTIAL_CONTENT,
    HTTP_TRESHOLD,
    HTTP_MULTIPLE_CHOICES,
    HTTP_FOUND,
    HTTP_NOT_MODIFIED,
    HTTP_TEMPORARY_REDIRECT,
    HTTP_BAD_REQUEST,
    HTTP_BAD_UNAUTHORIZED,
    HTTP_BAD_FORBIDDEN,
    HTTP_BAD_NOTFOUND,
    HTTP_BAD_METHOD_NOT_ALLOWED,
    HTTP_BAD_CONFLICT,
    HTTP_BAD_RESOURCE,
    HTTP_SERVER_ERROR,
    HTTP_NOT_IMPLEMENTED,
    HTTP_SERVICE_UNAVAILABLE,
    HTTP_INTERNAL_TIMEOUT,
)


def test_codes():

    assert HTTP_CONTINUE == 100
    assert HTTP_SWITCHING_PROTOCOLS == 101
    assert HTTP_OK_BASIC == 200
    assert HTTP_OK_CREATED == 201
    assert HTTP_OK_ACCEPTED == 202
    assert HTTP_OK_NORESPONSE == 204
    assert HTTP_PARTIAL_CONTENT == 206
    assert HTTP_PARTIAL_CONTENT == 206
    assert HTTP_TRESHOLD == 299
    assert HTTP_MULTIPLE_CHOICES == 300
    assert HTTP_FOUND == 302
    assert HTTP_NOT_MODIFIED == 304
    assert HTTP_TEMPORARY_REDIRECT == 307
    assert HTTP_BAD_REQUEST == 400
    assert HTTP_BAD_UNAUTHORIZED == 401
    assert HTTP_BAD_FORBIDDEN == 403
    assert HTTP_BAD_NOTFOUND == 404
    assert HTTP_BAD_METHOD_NOT_ALLOWED == 405
    assert HTTP_BAD_CONFLICT == 409
    assert HTTP_BAD_RESOURCE == 410
    assert HTTP_SERVER_ERROR == 500
    assert HTTP_NOT_IMPLEMENTED == 501
    assert HTTP_SERVICE_UNAVAILABLE == 503
    assert HTTP_INTERNAL_TIMEOUT == 504
