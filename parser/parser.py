from lexer import AstFactory
from .expression import ExpressionParser
from .statement import StatementParser
from .declaration import DeclarationParser

class Parser(ExpressionParser, StatementParser, DeclarationParser):
    def __init__(self, language, tokens):
        self.language = language
        self.tokens = tokens
        self.pos = 0
        self.astClasses = AstFactory(language).astClasses
        self.classNames = set()
        self.statementParseMap = {}
        for key, funcName in language["statementParseMap"].items():
            self.statementParseMap[key] = getattr(self, funcName)
        self.factorParseMap = {}
        for key, value in language["factorParseMap"].items():
            if isinstance(value, dict):
                method = getattr(self, value["method"])
                args = value["args"]
                self.factorParseMap[key] = (lambda m=method, a=args: m(*a))
            else:
                self.factorParseMap[key] = getattr(self, value)
        self.op_precedences = language["operators"]["precedences"]
        self.datatypes = ("INT", "FLOAT", "CHAR")

    def currentToken(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def match(self, tokenType):
        token = self.currentToken()
        return token and token.tokenType == tokenType

    def peek(self, offset=1):
        pos = self.pos + offset
        return self.tokens[pos] if pos < len(self.tokens) else None

    def advance(self):
        token = self.currentToken()
        self.pos += 1
        return token

    def consumeToken(self, tokenType):
        if self.match(tokenType):
            return self.advance()
        raise SyntaxError(f"Expected token {tokenType}, got {self.currentToken()}")

    def consumePairedTokens(self, openToken, closeToken, parseFunc):
        self.consumeToken(openToken)
        result = parseFunc()
        self.consumeToken(closeToken)
        return result

    def parseLiteral(self, tokenType, astName):
        token = self.consumeToken(tokenType)
        return self.astClasses[astName](token.tokenValue)

    def parseProgram(self):
        functions = []
        classes = []
        while self.currentToken() is not None:
            if self.match("CLASS"):
                classDecl = self.parseClassDeclaration()
                classes.append(classDecl)
                self.classNames.add(classDecl.name)
            elif self.isDatatype(self.currentToken()):
                functions.append(self.parseFunction())
            else:
                self.advance()
        return self.astClasses["Program"](functions, classes)

    def parseDelimitedList(self, endToken, delimiterToken, parseFunc):
        result = []
        if not self.match(endToken):
            result.append(parseFunc())
            while self.match(delimiterToken):
                self.consumeToken(delimiterToken)
                result.append(parseFunc())
        return result 