class StatementParser:
    def parseStatement(self):
        token = self.currentToken()
        if token.tokenType in self.statementParseMap:
            return self.statementParseMap[token.tokenType]()
        elif self.isDatatype(token):
            return self.parseDeclaration()
        else:
            expr = self.parseExpression()
            self.consumeToken("SEMICOLON")
            return self.astClasses["ExpressionStatement"](expr)
    
    def parseReturn(self):
        self.consumeToken("RETURN")
        expr = self.parseExpression()
        self.consumeToken("SEMICOLON")
        return self.astClasses["Return"](expr)
    
    def parseControlFlow(self, keyword, nodeType, hasElse=False):
        self.consumeToken(keyword)
        condition = self.parseCondition()
        thenBody = self.parseBlock()
        elseBody = None

        if hasElse and self.match("ELSE"):
            self.consumeToken("ELSE")
            if nodeType == "If" and self.match("IF"):
                elseBody = [self.parseIf()]
            else:
                elseBody = self.parseBlock()

        return self.astClasses[nodeType](condition, thenBody, elseBody) if hasElse else self.astClasses[nodeType](condition, thenBody)

    def parseIf(self):
        return self.parseControlFlow("IF", "If", True)

    def parseWhile(self):
        return self.parseControlFlow("WHILE", "While")

    def parseFor(self):
        self.consumeToken("FOR")
        self.consumeToken("LPAREN")
        init = self.parseStatement()
        condition = self.parseExpression()
        self.consumeToken("SEMICOLON")
        increment = self.parseExpression()
        self.consumeToken("RPAREN")
        body = self.parseBlock()
        return self.astClasses["For"](init, condition, increment, body)

    def parseDoWhile(self):
        self.consumeToken("DO")
        body = self.parseBlock()
        self.consumeToken("WHILE")
        condition = self.parseCondition()
        self.consumeToken("SEMICOLON")
        return self.astClasses["DoWhile"](body, condition)

    def parseBlock(self):
        return self.consumePairedTokens("LBRACE", "RBRACE", self.parseBlockBody)

    def parseBlockBody(self):
        stmts = []
        while self.currentToken() and not self.match("RBRACE"):
            stmts.append(self.parseStatement())
        return stmts
        
    def parseCondition(self):
        if self.match("LPAREN"):
            return self.consumePairedTokens("LPAREN", "RPAREN", self.parseExpression)
        return self.parseExpression() 