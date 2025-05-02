class CCBaseException(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class CCInvalidRequestException(CCBaseException):
    """Client error in the request, corresponds to a 400 response"""


class CCUnauthorizedException(CCInvalidRequestException):
    """Client is not authorized, corresponds to a 401 response"""


class CCAccessDeniedException(CCInvalidRequestException):
    """Client is forbidden, corresponds to a 403 response"""


class CCNotFoundException(CCInvalidRequestException):
    """Requested resource is not found, corresponds to a 404 response"""


class CCUnsupportedMediaTypeException(CCInvalidRequestException):
    """Unsupported media type, corresponds to a 415 response"""


class CCRateLimitingException(CCInvalidRequestException):
    """Client is rate limited, corresponds to a 429 response"""


class CCInternalException(CCBaseException):
    """Internal error in the request, corresponds to a 500 response"""


class CCFailedTransactionException(CCBaseException):
    """Authorize.Net transaction failed due to user input, corresponds to a 400 response"""


class CCAwsServiceException(CCBaseException):
    """This is raised when an AWS service fails, corresponds to a 500 response"""


class CCConflictException(CCBaseException):
    """Client error in the request, corresponds to a 409 response"""
