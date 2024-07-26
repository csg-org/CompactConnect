

class CCBaseException(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class CCInvalidRequestException(CCBaseException):
    pass


class CCInternalException(CCBaseException):
    pass


class CCNotFoundException(CCBaseException):
    pass
