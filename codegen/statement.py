from llvmlite import ir

class StatementCodegen:
    def createCondBranch(self, condition, thenBlock, elseBlock):
        cond = self.codegen(condition)
        condBool = self.builder.icmp_unsigned("!=", cond, ir.Constant(cond.type, 0), name="cond")
        self.builder.cbranch(condBool, thenBlock, elseBlock)
        
    def handleBlockBody(self, block, statements):
        self.builder.position_at_start(block)
        for stmt in statements:
            self.codegen(stmt)
            
    def If(self, node):
        thenBb = self.builder.append_basic_block("then")
        elseBb = self.builder.append_basic_block("else") if node.elseBranch else None
        mergeBb = self.builder.append_basic_block("ifcont")
        
        self.createCondBranch(node.condition, thenBb, elseBb if elseBb else mergeBb)
        
        self.handleBlockBody(thenBb, node.thenBranch)
        if not self.builder.block.terminator:
            self.builder.branch(mergeBb)
            
        if node.elseBranch:
            self.handleBlockBody(elseBb, node.elseBranch)
            if not self.builder.block.terminator:
                self.builder.branch(mergeBb)
                
        self.builder.position_at_start(mergeBb)
        return ir.Constant(ir.IntType(32), 0)

    def While(self, node):
        loopBb = self.builder.append_basic_block("loop")
        bodyBb = self.builder.append_basic_block("whilebody")
        afterBb = self.builder.append_basic_block("afterloop")
        
        self.builder.branch(loopBb)
        self.builder.position_at_start(loopBb)
        
        self.createCondBranch(node.condition, bodyBb, afterBb)
        
        self.handleBlockBody(bodyBb, node.body)
        if not self.builder.block.terminator:
            self.builder.branch(loopBb)
            
        self.builder.position_at_start(afterBb)
        return ir.Constant(ir.IntType(32), 0)

    def For(self, node):
        self.codegen(node.init)
        
        loopBb = self.builder.append_basic_block("forloop")
        bodyBb = self.builder.append_basic_block("forbody")
        afterBb = self.builder.append_basic_block("afterfor")
        
        self.builder.branch(loopBb)
        self.builder.position_at_start(loopBb)
        
        self.createCondBranch(node.condition, bodyBb, afterBb)
        
        self.handleBlockBody(bodyBb, node.body)
        self.codegen(node.increment)
        self.builder.branch(loopBb)
        
        self.builder.position_at_start(afterBb)
        return ir.Constant(ir.IntType(32), 0)

    def DoWhile(self, node):
        loopBb = self.builder.append_basic_block("dowhileloop")
        afterBb = self.builder.append_basic_block("afterdowhile")
        
        self.builder.branch(loopBb)
        self.handleBlockBody(loopBb, node.body)
        
        cond = self.codegen(node.condition)
        condBool = self.builder.icmp_unsigned("!=", cond, ir.Constant(cond.type, 0), name="dowhilecond")
        self.builder.cbranch(condBool, loopBb, afterBb)
        
        self.builder.position_at_start(afterBb)
        return ir.Constant(ir.IntType(32), 0) 