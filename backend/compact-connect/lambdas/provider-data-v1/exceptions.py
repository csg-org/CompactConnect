

class CCBaseException(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class CCInvalidRequestException(CCBaseException):
    """
    Client error in the request, corresponds to a 400 response
    """
    pass


class CCUnauthorizedException(CCInvalidRequestException):
    """
    Client is not authorized, corresponds to a 401 response
    """
    pass


class CCAccessDeniedException(CCInvalidRequestException):
    """
    Client is forbidden, corresponds to a 403 response
    """
    pass


class CCNotFoundException(CCInvalidRequestException):
    """
    Requested resource is not found, corresponds to a 404 response
    """
    pass


class CCInternalException(CCBaseException):
    """
    Internal error in the request, corresponds to a 500 response
    """
    pass
