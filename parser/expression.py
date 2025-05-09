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

    def parseBinaryExpression(self, minPrecedence=0):
        left = self.parseFactor()
        
        while True:
            token = self.currentToken()
            if not token:
                break
                
            tokenType = token.tokenType
            if tokenType not in self.opPrecedences or self.opPrecedences[tokenType] < minPrecedence:
                break
                
            opPrec = self.opPrecedences[tokenType]
            self.advance()
            right = self.parseBinaryExpression(opPrec + 1)
            op = tokenType if tokenType in self.language["operators"]["compMap"] else token.tokenValue
            left = self.astClasses["BinOp"](op, left, right)
            
        return left

    def parseFactor(self):
        token = self.currentToken()
        
        if token.tokenType == "NEW":
            return self.parseNewExpression()
        if token.tokenType == "LBRACKET":
            return self.parseArrayLiteral()
        if token.tokenType in self.factorParseMap:
            return self.factorParseMap[token.tokenType]()
            
        raise SyntaxError(f"Unexpected token: {token}")
        
    def parseNewExpression(self):
        self.consumeToken("NEW")
        classNameToken = self.consumeToken("ID")
        self.consumeToken("LPAREN")
        self.consumeToken("RPAREN")
        return self.astClasses["NewExpr"](classNameToken.tokenValue)

    def parseIdentifier(self):
        token = self.currentToken()
        if token.tokenType in ("ID", "SELF"):
            self.advance()
        else:
            raise SyntaxError(f"Expected identifier, got {token}")

        node = self.astClasses["Var"](token.tokenValue)
        return self.parseChainedAccess(node)

    def parseChainedAccess(self, node):
        accessTokens = {
            "DOT": self.parseMemberAccess,
            "LPAREN": self.parseFunctionCall,
            "LBRACKET": self.parseArrayAccess
        }
        
        while self.currentToken() and self.currentToken().tokenType in accessTokens:
            tokenType = self.currentToken().tokenType
            node = accessTokens[tokenType](node)
            
        return node
        
    def parseMemberAccess(self, node):
        self.consumeToken("DOT")
        memberName = self.consumeToken("ID").tokenValue
        return self.astClasses["MemberAccess"](node, memberName)
        
    def parseFunctionCall(self, callee):
        return self.parseFunctionCallWithCallee(callee)
        
    def parseArrayAccess(self, array):
        index = self.consumePairedTokens("LBRACKET", "RBRACKET", self.parseExpression)
        return self.astClasses["ArrayAccess"](array, index)

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