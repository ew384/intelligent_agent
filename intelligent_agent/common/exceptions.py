class ServiceException(Exception):
    def __init__(self, service: str, code: str, message: str):
        self.service = service
        self.code = code
        self.message = message
        super().__init__(f"{service}:{code} - {message}")

class ValidationException(ServiceException):
    pass

class AuthenticationException(ServiceException):
    pass

class NotFoundException(ServiceException):
    pass