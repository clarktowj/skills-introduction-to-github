class MechElecAIException(Exception):
    pass

class AppStartupError(MechElecAIException):
    pass

class ConfigError(MechElecAIException):
    pass

class FileError(MechElecAIException):
    pass

class ParseError(MechElecAIException):
    pass

class CalculationError(MechElecAIException):
    pass

class ModelingError(MechElecAIException):
    pass

class AuditError(MechElecAIException):
    pass

class ValidationError(MechElecAIException):
    pass

class RuleEngineError(MechElecAIException):
    pass