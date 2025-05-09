class DeclarationParser:
    def parseClassDeclaration(self):
        self.consumeToken("CLASS")
        className = self.consumeToken("ID").tokenValue
        fields, methods = self.parseBodyMembers("LBRACE", "RBRACE", 
                                              lambda: self.parseClassMember(className))
        return self.astClasses["ClassDecl"](className, fields, methods)

    def parseBodyMembers(self, openToken, closeToken, parseMemberFunc):
        self.consumeToken(openToken)
        fields = []
        methods = []
        
        while self.currentToken() and not self.match(closeToken):
            member = parseMemberFunc()
            if member.__class__.__name__ == "MethodDecl":
                methods.append(member)
            else:
                fields.append(member)
                
        self.consumeToken(closeToken)
        return fields, methods

    def parseClassMember(self, className):
        dataTypeToken = self.consumeDatatype()
        nameToken = self.consumeToken("ID")
        
        if self.match("LPAREN"):
            return self.parseMethodDeclaration(dataTypeToken, nameToken, className)
        else:
            self.consumeToken("SEMICOLON")
            return self.createVarDecl(nameToken.tokenValue, None, dataTypeToken.tokenValue)

    def parseMethodDeclaration(self, returnTypeToken, nameToken, className):
        methodName = nameToken.tokenValue
        params = self.consumePairedTokens("LPAREN", "RPAREN", 
                                        lambda: self.parseDelimitedList("RPAREN", "COMMA", self.parseParameter))
        body = self.parseBlock()
        return self.astClasses["MethodDecl"](methodName, params, body, className, returnTypeToken.tokenValue)

    def parseParameter(self):
        dataTypeToken = self.consumeDatatype()
        idToken = self.consumeToken("ID")
        return self.createVarDecl(idToken.tokenValue, None, dataTypeToken.tokenValue)

    def createVarDecl(self, name, init, typeName):
        return self.astClasses["VarDecl"](name, init, typeName)

    def parseDeclaration(self):
        dataTypeToken = self.consumeDatatype()
        dataTypeName = dataTypeToken.tokenValue

        if self.match("LBRACKET"):
            return self.parseArrayDeclaration(dataTypeName)
            
        return self.parseVarDeclaration(dataTypeName)
        
    def parseArrayDeclaration(self, dataTypeName):
        self.consumeToken("LBRACKET")
        size = None if self.match("RBRACKET") else self.parseExpression()
        self.consumeToken("RBRACKET")
        varName = self.consumeToken("ID").tokenValue

        if self.match("EQ"):
            return self.parseInitializedDeclaration(varName, f"{dataTypeName}[]")

        self.consumeToken("SEMICOLON")
        return self.astClasses["ArrayDecl"](varName, size, dataTypeName)
        
    def parseVarDeclaration(self, dataTypeName):
        varName = self.consumeToken("ID").tokenValue

        if self.match("EQ"):
            return self.parseInitializedDeclaration(varName, dataTypeName)

        self.consumeToken("SEMICOLON")
        return self.createVarDecl(varName, None, dataTypeName)

    def parseInitializedDeclaration(self, varName, typeName):
        self.consumeToken("EQ")
        initExpr = self.parseExpression()
        self.consumeToken("SEMICOLON")
        return self.createVarDecl(varName, initExpr, typeName)

    def parseFunction(self):
        dataTypeToken = self.consumeDatatype()
        name = self.consumeToken("ID").tokenValue
        self.consumeToken("LPAREN")
        self.consumeToken("RPAREN")
        body = self.parseBlock()
        return self.astClasses["Function"](name, dataTypeToken.tokenValue, body)
        
    def isDatatype(self, token):
        if not token:
            return False
            
        if token.tokenType in self.datatypes:
            return True
            
        if token.tokenType == "ID":
            return (token.tokenValue in self.classNames or 
                   token.tokenValue == "string" or 
                   token.tokenValue in self.language["datatypes"])
                   
        return False

    def consumeDatatype(self):
        token = self.currentToken()
        if self.isDatatype(token):
            return self.advance()
        raise SyntaxError(f"Expected datatype, got {token}") 