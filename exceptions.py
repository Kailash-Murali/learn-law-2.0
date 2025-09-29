class ConstitutionalLawException(Exception):
    """Base exception for constitutional law research system"""
    pass

class DatabaseException(ConstitutionalLawException):
    """Database-related exceptions"""
    pass

class AgentException(ConstitutionalLawException):
    """Agent-related exceptions"""
    pass

class APIException(ConstitutionalLawException):
    """API-related exceptions"""
    pass

class ValidationException(ConstitutionalLawException):
    """Data validation exceptions"""
    pass
