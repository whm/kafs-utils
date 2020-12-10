class AFSException(Exception):
    """Base class for all AFS Toolkit exceptions."""
    pass

class AFSArgumentError(AFSException):
    """An argument parsing error was encountered"""
    pass

class AFSNetAddressError(AFSException):
    """A network address parsing error was encountered"""
    pass

class AFSHelpFlag(AFSException):
    """The -help flag was specified to a command."""
    pass

