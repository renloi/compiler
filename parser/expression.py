class ExpressionParser:
    def parseExpression(self):
        return self.parseAssignment()

    def parseAssignment(self):
        node = self.parseBinaryExpression()
        if self.match("EQ"):
            self.consumeToken("EQ")
            right = self.parseAssignment()
            if node.__class__.__name__ in ("MemberAccess", "Var", "ArrayAccess"):
                return self.astClasses["Assign"](node, right)
            raise SyntaxError("Invalid left-hand side for assignment")
        return node

    def parseBinaryExpression(self, min_precedence=0):
        left = self.parseFactor()
        while True:
            token = self.currentToken()
            if not token:
                break
            token_type = token.tokenType
            if token_type not in self.op_precedences or self.op_precedences[token_type] < min_precedence:
                break
            op_prec = self.op_precedences[token_type]
            self.advance()
            right = self.parseBinaryExpression(op_prec + 1)
            op = token_type if token_type in self.language["operators"]["compMap"] else token.tokenValue
            left = self.astClasses["BinOp"](op, left, right)
        return left

    def parseFactor(self):
        token = self.currentToken()
        if token.tokenType == "NEW":
            self.consumeToken("NEW")
            classNameToken = self.consumeToken("ID")
            self.consumeToken("LPAREN")
            self.consumeToken("RPAREN")
            return self.astClasses["NewExpr"](classNameToken.tokenValue)
        if token.tokenType == "LBRACKET":
            return self.parseArrayLiteral()
        if token.tokenType in self.factorParseMap:
            return self.factorParseMap[token.tokenType]()
        raise SyntaxError(f"Unexpected token: {token}")

    def parseIdentifier(self):
        token = self.currentToken()
        if token.tokenType in ("ID", "SELF"):
            self.advance()
        else:
            raise SyntaxError(f"Expected identifier, got {token}")

        node = self.astClasses["Var"](token.tokenValue)
        return self.parseChainedAccess(node)

    def parseChainedAccess(self, node):
        while self.currentToken() and self.currentToken().tokenType in ("DOT", "LPAREN", "LBRACKET"):
            if self.match("DOT"):
                self.consumeToken("DOT")
                memberName = self.consumeToken("ID").tokenValue
                node = self.astClasses["MemberAccess"](node, memberName)
            elif self.match("LPAREN"):
                node = self.parseFunctionCallWithCallee(node)
            elif self.match("LBRACKET"):
                index = self.consumePairedTokens("LBRACKET", "RBRACKET", self.parseExpression)
                node = self.astClasses["ArrayAccess"](node, index)
        return node

    def parseFunctionCallWithCallee(self, callee):
        args = self.consumePairedTokens("LPAREN", "RPAREN", 
                                       lambda: self.parseDelimitedList("RPAREN", "COMMA", self.parseExpression))
        return self.astClasses["FunctionCall"](callee, args)

    def parseParenthesizedExpression(self):
        return self.consumePairedTokens("LPAREN", "RPAREN", self.parseExpression)
        
    def parseArrayLiteral(self):
        elements = self.consumePairedTokens("LBRACKET", "RBRACKET", 
                                          lambda: self.parseDelimitedList("RBRACKET", "COMMA", self.parseExpression))
        return self.astClasses["ArrayLiteral"](elements) 