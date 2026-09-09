# Generated from TypeScriptParser.g4 by ANTLR 4.13.2
# encoding: utf-8
from antlr4 import *
from io import StringIO
import sys
if sys.version_info[1] > 5:
	from typing import TextIO
else:
	from typing.io import TextIO

def serializedATN():
    return [
        4,1,33,197,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,2,13,7,13,
        2,14,7,14,2,15,7,15,2,16,7,16,2,17,7,17,2,18,7,18,2,19,7,19,2,20,
        7,20,2,21,7,21,2,22,7,22,1,0,5,0,48,8,0,10,0,12,0,51,9,0,1,0,1,0,
        1,1,1,1,1,1,3,1,58,8,1,1,2,1,2,1,2,1,2,1,2,3,2,65,8,2,1,2,1,2,1,
        2,1,2,1,3,1,3,1,4,1,4,1,4,1,4,1,4,1,4,1,4,1,5,1,5,1,5,1,5,3,5,84,
        8,5,1,5,1,5,1,6,1,6,1,6,1,6,5,6,92,8,6,10,6,12,6,95,9,6,1,7,1,7,
        1,8,3,8,100,8,8,1,8,1,8,1,8,5,8,105,8,8,10,8,12,8,108,9,8,1,9,1,
        9,1,9,5,9,113,8,9,10,9,12,9,116,9,9,1,10,1,10,1,10,5,10,121,8,10,
        10,10,12,10,124,9,10,1,11,1,11,1,11,1,11,1,11,1,11,1,11,1,11,1,11,
        3,11,135,8,11,1,12,1,12,1,13,1,13,1,13,1,14,1,14,1,14,1,14,1,14,
        3,14,147,8,14,1,15,1,15,1,15,5,15,152,8,15,10,15,12,15,155,9,15,
        1,16,1,16,1,17,1,17,5,17,161,8,17,10,17,12,17,164,9,17,1,17,1,17,
        1,18,1,18,3,18,170,8,18,1,18,3,18,173,8,18,1,19,1,19,1,19,1,19,1,
        19,1,19,1,19,1,19,1,20,1,20,3,20,185,8,20,1,20,1,20,1,20,1,21,1,
        21,1,21,3,21,193,8,21,1,22,1,22,1,22,0,0,23,0,2,4,6,8,10,12,14,16,
        18,20,22,24,26,28,30,32,34,36,38,40,42,44,0,5,1,0,13,14,1,0,7,12,
        2,0,16,16,18,18,1,0,7,8,1,0,2,12,196,0,49,1,0,0,0,2,57,1,0,0,0,4,
        59,1,0,0,0,6,70,1,0,0,0,8,72,1,0,0,0,10,79,1,0,0,0,12,87,1,0,0,0,
        14,96,1,0,0,0,16,99,1,0,0,0,18,109,1,0,0,0,20,117,1,0,0,0,22,134,
        1,0,0,0,24,136,1,0,0,0,26,138,1,0,0,0,28,141,1,0,0,0,30,148,1,0,
        0,0,32,156,1,0,0,0,34,158,1,0,0,0,36,169,1,0,0,0,38,174,1,0,0,0,
        40,182,1,0,0,0,42,192,1,0,0,0,44,194,1,0,0,0,46,48,3,2,1,0,47,46,
        1,0,0,0,48,51,1,0,0,0,49,47,1,0,0,0,49,50,1,0,0,0,50,52,1,0,0,0,
        51,49,1,0,0,0,52,53,5,0,0,1,53,1,1,0,0,0,54,58,3,4,2,0,55,58,3,8,
        4,0,56,58,3,10,5,0,57,54,1,0,0,0,57,55,1,0,0,0,57,56,1,0,0,0,58,
        3,1,0,0,0,59,60,5,1,0,0,60,61,5,2,0,0,61,64,5,15,0,0,62,63,5,17,
        0,0,63,65,3,14,7,0,64,62,1,0,0,0,64,65,1,0,0,0,65,66,1,0,0,0,66,
        67,5,22,0,0,67,68,3,6,3,0,68,69,5,16,0,0,69,5,1,0,0,0,70,71,7,0,
        0,0,71,7,1,0,0,0,72,73,5,1,0,0,73,74,5,3,0,0,74,75,5,15,0,0,75,76,
        5,22,0,0,76,77,3,14,7,0,77,78,5,16,0,0,78,9,1,0,0,0,79,80,5,1,0,
        0,80,81,5,4,0,0,81,83,5,15,0,0,82,84,3,12,6,0,83,82,1,0,0,0,83,84,
        1,0,0,0,84,85,1,0,0,0,85,86,3,34,17,0,86,11,1,0,0,0,87,88,5,5,0,
        0,88,93,3,28,14,0,89,90,5,18,0,0,90,92,3,28,14,0,91,89,1,0,0,0,92,
        95,1,0,0,0,93,91,1,0,0,0,93,94,1,0,0,0,94,13,1,0,0,0,95,93,1,0,0,
        0,96,97,3,16,8,0,97,15,1,0,0,0,98,100,5,20,0,0,99,98,1,0,0,0,99,
        100,1,0,0,0,100,101,1,0,0,0,101,106,3,18,9,0,102,103,5,20,0,0,103,
        105,3,18,9,0,104,102,1,0,0,0,105,108,1,0,0,0,106,104,1,0,0,0,106,
        107,1,0,0,0,107,17,1,0,0,0,108,106,1,0,0,0,109,114,3,20,10,0,110,
        111,5,21,0,0,111,113,3,20,10,0,112,110,1,0,0,0,113,116,1,0,0,0,114,
        112,1,0,0,0,114,115,1,0,0,0,115,19,1,0,0,0,116,114,1,0,0,0,117,122,
        3,22,11,0,118,119,5,27,0,0,119,121,5,28,0,0,120,118,1,0,0,0,121,
        124,1,0,0,0,122,120,1,0,0,0,122,123,1,0,0,0,123,21,1,0,0,0,124,122,
        1,0,0,0,125,135,3,24,12,0,126,135,5,13,0,0,127,135,3,26,13,0,128,
        135,3,28,14,0,129,135,3,34,17,0,130,131,5,29,0,0,131,132,3,14,7,
        0,132,133,5,30,0,0,133,135,1,0,0,0,134,125,1,0,0,0,134,126,1,0,0,
        0,134,127,1,0,0,0,134,128,1,0,0,0,134,129,1,0,0,0,134,130,1,0,0,
        0,135,23,1,0,0,0,136,137,7,1,0,0,137,25,1,0,0,0,138,139,5,6,0,0,
        139,140,5,15,0,0,140,27,1,0,0,0,141,146,5,15,0,0,142,143,5,23,0,
        0,143,144,3,30,15,0,144,145,5,24,0,0,145,147,1,0,0,0,146,142,1,0,
        0,0,146,147,1,0,0,0,147,29,1,0,0,0,148,153,3,32,16,0,149,150,5,18,
        0,0,150,152,3,32,16,0,151,149,1,0,0,0,152,155,1,0,0,0,153,151,1,
        0,0,0,153,154,1,0,0,0,154,31,1,0,0,0,155,153,1,0,0,0,156,157,3,14,
        7,0,157,33,1,0,0,0,158,162,5,25,0,0,159,161,3,36,18,0,160,159,1,
        0,0,0,161,164,1,0,0,0,162,160,1,0,0,0,162,163,1,0,0,0,163,165,1,
        0,0,0,164,162,1,0,0,0,165,166,5,26,0,0,166,35,1,0,0,0,167,170,3,
        38,19,0,168,170,3,40,20,0,169,167,1,0,0,0,169,168,1,0,0,0,170,172,
        1,0,0,0,171,173,7,2,0,0,172,171,1,0,0,0,172,173,1,0,0,0,173,37,1,
        0,0,0,174,175,5,27,0,0,175,176,5,15,0,0,176,177,5,17,0,0,177,178,
        7,3,0,0,178,179,5,28,0,0,179,180,5,17,0,0,180,181,3,14,7,0,181,39,
        1,0,0,0,182,184,3,42,21,0,183,185,5,19,0,0,184,183,1,0,0,0,184,185,
        1,0,0,0,185,186,1,0,0,0,186,187,5,17,0,0,187,188,3,14,7,0,188,41,
        1,0,0,0,189,193,5,15,0,0,190,193,5,13,0,0,191,193,3,44,22,0,192,
        189,1,0,0,0,192,190,1,0,0,0,192,191,1,0,0,0,193,43,1,0,0,0,194,195,
        7,4,0,0,195,45,1,0,0,0,17,49,57,64,83,93,99,106,114,122,134,146,
        153,162,169,172,184,192
    ]

class TypeScriptParser ( Parser ):

    grammarFileName = "TypeScriptParser.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [ "<INVALID>", "'export'", "'const'", "'type'", "'interface'", 
                     "'extends'", "'typeof'", "'string'", "'number'", "'boolean'", 
                     "'null'", "'unknown'", "'any'", "<INVALID>", "<INVALID>", 
                     "<INVALID>", "';'", "':'", "','", "'?'", "'|'", "'&'", 
                     "'='", "'<'", "'>'", "'{'", "'}'", "'['", "']'", "'('", 
                     "')'" ]

    symbolicNames = [ "<INVALID>", "Export", "Const", "Type", "Interface", 
                      "Extends", "Typeof", "StringType", "NumberType", "BooleanType", 
                      "NullType", "UnknownType", "AnyType", "StringLiteral", 
                      "IntegerLiteral", "Identifier", "Semi", "Colon", "Comma", 
                      "QuestionMark", "Pipe", "Ampersand", "Equals", "LessThan", 
                      "GreaterThan", "OpenBrace", "CloseBrace", "OpenBracket", 
                      "CloseBracket", "OpenParen", "CloseParen", "LineComment", 
                      "BlockComment", "WhiteSpace" ]

    RULE_typeScriptFile = 0
    RULE_declaration = 1
    RULE_constDeclaration = 2
    RULE_constValue = 3
    RULE_typeAliasDeclaration = 4
    RULE_interfaceDeclaration = 5
    RULE_extendsClause = 6
    RULE_typeExpression = 7
    RULE_unionType = 8
    RULE_intersectionType = 9
    RULE_arrayOrPrimaryType = 10
    RULE_primaryType = 11
    RULE_primitiveType = 12
    RULE_typeQuery = 13
    RULE_typeReference = 14
    RULE_typeArgumentList = 15
    RULE_typeArgument = 16
    RULE_objectType = 17
    RULE_memberSignature = 18
    RULE_indexSignature = 19
    RULE_propertySignature = 20
    RULE_propertyName = 21
    RULE_keywordAsIdentifier = 22

    ruleNames =  [ "typeScriptFile", "declaration", "constDeclaration", 
                   "constValue", "typeAliasDeclaration", "interfaceDeclaration", 
                   "extendsClause", "typeExpression", "unionType", "intersectionType", 
                   "arrayOrPrimaryType", "primaryType", "primitiveType", 
                   "typeQuery", "typeReference", "typeArgumentList", "typeArgument", 
                   "objectType", "memberSignature", "indexSignature", "propertySignature", 
                   "propertyName", "keywordAsIdentifier" ]

    EOF = Token.EOF
    Export=1
    Const=2
    Type=3
    Interface=4
    Extends=5
    Typeof=6
    StringType=7
    NumberType=8
    BooleanType=9
    NullType=10
    UnknownType=11
    AnyType=12
    StringLiteral=13
    IntegerLiteral=14
    Identifier=15
    Semi=16
    Colon=17
    Comma=18
    QuestionMark=19
    Pipe=20
    Ampersand=21
    Equals=22
    LessThan=23
    GreaterThan=24
    OpenBrace=25
    CloseBrace=26
    OpenBracket=27
    CloseBracket=28
    OpenParen=29
    CloseParen=30
    LineComment=31
    BlockComment=32
    WhiteSpace=33

    def __init__(self, input:TokenStream, output:TextIO = sys.stdout):
        super().__init__(input, output)
        self.checkVersion("4.13.2")
        self._interp = ParserATNSimulator(self, self.atn, self.decisionsToDFA, self.sharedContextCache)
        self._predicates = None




    class TypeScriptFileContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def EOF(self):
            return self.getToken(TypeScriptParser.EOF, 0)

        def declaration(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(TypeScriptParser.DeclarationContext)
            else:
                return self.getTypedRuleContext(TypeScriptParser.DeclarationContext,i)


        def getRuleIndex(self):
            return TypeScriptParser.RULE_typeScriptFile

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterTypeScriptFile" ):
                listener.enterTypeScriptFile(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitTypeScriptFile" ):
                listener.exitTypeScriptFile(self)




    def typeScriptFile(self):

        localctx = TypeScriptParser.TypeScriptFileContext(self, self._ctx, self.state)
        self.enterRule(localctx, 0, self.RULE_typeScriptFile)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 49
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==1:
                self.state = 46
                self.declaration()
                self.state = 51
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 52
            self.match(TypeScriptParser.EOF)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class DeclarationContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def constDeclaration(self):
            return self.getTypedRuleContext(TypeScriptParser.ConstDeclarationContext,0)


        def typeAliasDeclaration(self):
            return self.getTypedRuleContext(TypeScriptParser.TypeAliasDeclarationContext,0)


        def interfaceDeclaration(self):
            return self.getTypedRuleContext(TypeScriptParser.InterfaceDeclarationContext,0)


        def getRuleIndex(self):
            return TypeScriptParser.RULE_declaration

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterDeclaration" ):
                listener.enterDeclaration(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitDeclaration" ):
                listener.exitDeclaration(self)




    def declaration(self):

        localctx = TypeScriptParser.DeclarationContext(self, self._ctx, self.state)
        self.enterRule(localctx, 2, self.RULE_declaration)
        try:
            self.state = 57
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,1,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 54
                self.constDeclaration()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 55
                self.typeAliasDeclaration()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 56
                self.interfaceDeclaration()
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ConstDeclarationContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def Export(self):
            return self.getToken(TypeScriptParser.Export, 0)

        def Const(self):
            return self.getToken(TypeScriptParser.Const, 0)

        def Identifier(self):
            return self.getToken(TypeScriptParser.Identifier, 0)

        def Equals(self):
            return self.getToken(TypeScriptParser.Equals, 0)

        def constValue(self):
            return self.getTypedRuleContext(TypeScriptParser.ConstValueContext,0)


        def Semi(self):
            return self.getToken(TypeScriptParser.Semi, 0)

        def Colon(self):
            return self.getToken(TypeScriptParser.Colon, 0)

        def typeExpression(self):
            return self.getTypedRuleContext(TypeScriptParser.TypeExpressionContext,0)


        def getRuleIndex(self):
            return TypeScriptParser.RULE_constDeclaration

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterConstDeclaration" ):
                listener.enterConstDeclaration(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitConstDeclaration" ):
                listener.exitConstDeclaration(self)




    def constDeclaration(self):

        localctx = TypeScriptParser.ConstDeclarationContext(self, self._ctx, self.state)
        self.enterRule(localctx, 4, self.RULE_constDeclaration)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 59
            self.match(TypeScriptParser.Export)
            self.state = 60
            self.match(TypeScriptParser.Const)
            self.state = 61
            self.match(TypeScriptParser.Identifier)
            self.state = 64
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==17:
                self.state = 62
                self.match(TypeScriptParser.Colon)
                self.state = 63
                self.typeExpression()


            self.state = 66
            self.match(TypeScriptParser.Equals)
            self.state = 67
            self.constValue()
            self.state = 68
            self.match(TypeScriptParser.Semi)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ConstValueContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def StringLiteral(self):
            return self.getToken(TypeScriptParser.StringLiteral, 0)

        def IntegerLiteral(self):
            return self.getToken(TypeScriptParser.IntegerLiteral, 0)

        def getRuleIndex(self):
            return TypeScriptParser.RULE_constValue

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterConstValue" ):
                listener.enterConstValue(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitConstValue" ):
                listener.exitConstValue(self)




    def constValue(self):

        localctx = TypeScriptParser.ConstValueContext(self, self._ctx, self.state)
        self.enterRule(localctx, 6, self.RULE_constValue)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 70
            _la = self._input.LA(1)
            if not(_la==13 or _la==14):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class TypeAliasDeclarationContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def Export(self):
            return self.getToken(TypeScriptParser.Export, 0)

        def Type(self):
            return self.getToken(TypeScriptParser.Type, 0)

        def Identifier(self):
            return self.getToken(TypeScriptParser.Identifier, 0)

        def Equals(self):
            return self.getToken(TypeScriptParser.Equals, 0)

        def typeExpression(self):
            return self.getTypedRuleContext(TypeScriptParser.TypeExpressionContext,0)


        def Semi(self):
            return self.getToken(TypeScriptParser.Semi, 0)

        def getRuleIndex(self):
            return TypeScriptParser.RULE_typeAliasDeclaration

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterTypeAliasDeclaration" ):
                listener.enterTypeAliasDeclaration(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitTypeAliasDeclaration" ):
                listener.exitTypeAliasDeclaration(self)




    def typeAliasDeclaration(self):

        localctx = TypeScriptParser.TypeAliasDeclarationContext(self, self._ctx, self.state)
        self.enterRule(localctx, 8, self.RULE_typeAliasDeclaration)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 72
            self.match(TypeScriptParser.Export)
            self.state = 73
            self.match(TypeScriptParser.Type)
            self.state = 74
            self.match(TypeScriptParser.Identifier)
            self.state = 75
            self.match(TypeScriptParser.Equals)
            self.state = 76
            self.typeExpression()
            self.state = 77
            self.match(TypeScriptParser.Semi)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class InterfaceDeclarationContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def Export(self):
            return self.getToken(TypeScriptParser.Export, 0)

        def Interface(self):
            return self.getToken(TypeScriptParser.Interface, 0)

        def Identifier(self):
            return self.getToken(TypeScriptParser.Identifier, 0)

        def objectType(self):
            return self.getTypedRuleContext(TypeScriptParser.ObjectTypeContext,0)


        def extendsClause(self):
            return self.getTypedRuleContext(TypeScriptParser.ExtendsClauseContext,0)


        def getRuleIndex(self):
            return TypeScriptParser.RULE_interfaceDeclaration

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterInterfaceDeclaration" ):
                listener.enterInterfaceDeclaration(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitInterfaceDeclaration" ):
                listener.exitInterfaceDeclaration(self)




    def interfaceDeclaration(self):

        localctx = TypeScriptParser.InterfaceDeclarationContext(self, self._ctx, self.state)
        self.enterRule(localctx, 10, self.RULE_interfaceDeclaration)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 79
            self.match(TypeScriptParser.Export)
            self.state = 80
            self.match(TypeScriptParser.Interface)
            self.state = 81
            self.match(TypeScriptParser.Identifier)
            self.state = 83
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==5:
                self.state = 82
                self.extendsClause()


            self.state = 85
            self.objectType()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ExtendsClauseContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def Extends(self):
            return self.getToken(TypeScriptParser.Extends, 0)

        def typeReference(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(TypeScriptParser.TypeReferenceContext)
            else:
                return self.getTypedRuleContext(TypeScriptParser.TypeReferenceContext,i)


        def Comma(self, i:int=None):
            if i is None:
                return self.getTokens(TypeScriptParser.Comma)
            else:
                return self.getToken(TypeScriptParser.Comma, i)

        def getRuleIndex(self):
            return TypeScriptParser.RULE_extendsClause

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterExtendsClause" ):
                listener.enterExtendsClause(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitExtendsClause" ):
                listener.exitExtendsClause(self)




    def extendsClause(self):

        localctx = TypeScriptParser.ExtendsClauseContext(self, self._ctx, self.state)
        self.enterRule(localctx, 12, self.RULE_extendsClause)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 87
            self.match(TypeScriptParser.Extends)
            self.state = 88
            self.typeReference()
            self.state = 93
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==18:
                self.state = 89
                self.match(TypeScriptParser.Comma)
                self.state = 90
                self.typeReference()
                self.state = 95
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class TypeExpressionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def unionType(self):
            return self.getTypedRuleContext(TypeScriptParser.UnionTypeContext,0)


        def getRuleIndex(self):
            return TypeScriptParser.RULE_typeExpression

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterTypeExpression" ):
                listener.enterTypeExpression(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitTypeExpression" ):
                listener.exitTypeExpression(self)




    def typeExpression(self):

        localctx = TypeScriptParser.TypeExpressionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 14, self.RULE_typeExpression)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 96
            self.unionType()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class UnionTypeContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def intersectionType(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(TypeScriptParser.IntersectionTypeContext)
            else:
                return self.getTypedRuleContext(TypeScriptParser.IntersectionTypeContext,i)


        def Pipe(self, i:int=None):
            if i is None:
                return self.getTokens(TypeScriptParser.Pipe)
            else:
                return self.getToken(TypeScriptParser.Pipe, i)

        def getRuleIndex(self):
            return TypeScriptParser.RULE_unionType

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterUnionType" ):
                listener.enterUnionType(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitUnionType" ):
                listener.exitUnionType(self)




    def unionType(self):

        localctx = TypeScriptParser.UnionTypeContext(self, self._ctx, self.state)
        self.enterRule(localctx, 16, self.RULE_unionType)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 99
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==20:
                self.state = 98
                self.match(TypeScriptParser.Pipe)


            self.state = 101
            self.intersectionType()
            self.state = 106
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==20:
                self.state = 102
                self.match(TypeScriptParser.Pipe)
                self.state = 103
                self.intersectionType()
                self.state = 108
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class IntersectionTypeContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def arrayOrPrimaryType(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(TypeScriptParser.ArrayOrPrimaryTypeContext)
            else:
                return self.getTypedRuleContext(TypeScriptParser.ArrayOrPrimaryTypeContext,i)


        def Ampersand(self, i:int=None):
            if i is None:
                return self.getTokens(TypeScriptParser.Ampersand)
            else:
                return self.getToken(TypeScriptParser.Ampersand, i)

        def getRuleIndex(self):
            return TypeScriptParser.RULE_intersectionType

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterIntersectionType" ):
                listener.enterIntersectionType(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitIntersectionType" ):
                listener.exitIntersectionType(self)




    def intersectionType(self):

        localctx = TypeScriptParser.IntersectionTypeContext(self, self._ctx, self.state)
        self.enterRule(localctx, 18, self.RULE_intersectionType)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 109
            self.arrayOrPrimaryType()
            self.state = 114
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==21:
                self.state = 110
                self.match(TypeScriptParser.Ampersand)
                self.state = 111
                self.arrayOrPrimaryType()
                self.state = 116
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ArrayOrPrimaryTypeContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def primaryType(self):
            return self.getTypedRuleContext(TypeScriptParser.PrimaryTypeContext,0)


        def OpenBracket(self, i:int=None):
            if i is None:
                return self.getTokens(TypeScriptParser.OpenBracket)
            else:
                return self.getToken(TypeScriptParser.OpenBracket, i)

        def CloseBracket(self, i:int=None):
            if i is None:
                return self.getTokens(TypeScriptParser.CloseBracket)
            else:
                return self.getToken(TypeScriptParser.CloseBracket, i)

        def getRuleIndex(self):
            return TypeScriptParser.RULE_arrayOrPrimaryType

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterArrayOrPrimaryType" ):
                listener.enterArrayOrPrimaryType(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitArrayOrPrimaryType" ):
                listener.exitArrayOrPrimaryType(self)




    def arrayOrPrimaryType(self):

        localctx = TypeScriptParser.ArrayOrPrimaryTypeContext(self, self._ctx, self.state)
        self.enterRule(localctx, 20, self.RULE_arrayOrPrimaryType)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 117
            self.primaryType()
            self.state = 122
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,8,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 118
                    self.match(TypeScriptParser.OpenBracket)
                    self.state = 119
                    self.match(TypeScriptParser.CloseBracket) 
                self.state = 124
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,8,self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class PrimaryTypeContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def primitiveType(self):
            return self.getTypedRuleContext(TypeScriptParser.PrimitiveTypeContext,0)


        def StringLiteral(self):
            return self.getToken(TypeScriptParser.StringLiteral, 0)

        def typeQuery(self):
            return self.getTypedRuleContext(TypeScriptParser.TypeQueryContext,0)


        def typeReference(self):
            return self.getTypedRuleContext(TypeScriptParser.TypeReferenceContext,0)


        def objectType(self):
            return self.getTypedRuleContext(TypeScriptParser.ObjectTypeContext,0)


        def OpenParen(self):
            return self.getToken(TypeScriptParser.OpenParen, 0)

        def typeExpression(self):
            return self.getTypedRuleContext(TypeScriptParser.TypeExpressionContext,0)


        def CloseParen(self):
            return self.getToken(TypeScriptParser.CloseParen, 0)

        def getRuleIndex(self):
            return TypeScriptParser.RULE_primaryType

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterPrimaryType" ):
                listener.enterPrimaryType(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitPrimaryType" ):
                listener.exitPrimaryType(self)




    def primaryType(self):

        localctx = TypeScriptParser.PrimaryTypeContext(self, self._ctx, self.state)
        self.enterRule(localctx, 22, self.RULE_primaryType)
        try:
            self.state = 134
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [7, 8, 9, 10, 11, 12]:
                self.enterOuterAlt(localctx, 1)
                self.state = 125
                self.primitiveType()
                pass
            elif token in [13]:
                self.enterOuterAlt(localctx, 2)
                self.state = 126
                self.match(TypeScriptParser.StringLiteral)
                pass
            elif token in [6]:
                self.enterOuterAlt(localctx, 3)
                self.state = 127
                self.typeQuery()
                pass
            elif token in [15]:
                self.enterOuterAlt(localctx, 4)
                self.state = 128
                self.typeReference()
                pass
            elif token in [25]:
                self.enterOuterAlt(localctx, 5)
                self.state = 129
                self.objectType()
                pass
            elif token in [29]:
                self.enterOuterAlt(localctx, 6)
                self.state = 130
                self.match(TypeScriptParser.OpenParen)
                self.state = 131
                self.typeExpression()
                self.state = 132
                self.match(TypeScriptParser.CloseParen)
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class PrimitiveTypeContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def StringType(self):
            return self.getToken(TypeScriptParser.StringType, 0)

        def NumberType(self):
            return self.getToken(TypeScriptParser.NumberType, 0)

        def BooleanType(self):
            return self.getToken(TypeScriptParser.BooleanType, 0)

        def NullType(self):
            return self.getToken(TypeScriptParser.NullType, 0)

        def UnknownType(self):
            return self.getToken(TypeScriptParser.UnknownType, 0)

        def AnyType(self):
            return self.getToken(TypeScriptParser.AnyType, 0)

        def getRuleIndex(self):
            return TypeScriptParser.RULE_primitiveType

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterPrimitiveType" ):
                listener.enterPrimitiveType(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitPrimitiveType" ):
                listener.exitPrimitiveType(self)




    def primitiveType(self):

        localctx = TypeScriptParser.PrimitiveTypeContext(self, self._ctx, self.state)
        self.enterRule(localctx, 24, self.RULE_primitiveType)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 136
            _la = self._input.LA(1)
            if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 8064) != 0)):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class TypeQueryContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def Typeof(self):
            return self.getToken(TypeScriptParser.Typeof, 0)

        def Identifier(self):
            return self.getToken(TypeScriptParser.Identifier, 0)

        def getRuleIndex(self):
            return TypeScriptParser.RULE_typeQuery

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterTypeQuery" ):
                listener.enterTypeQuery(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitTypeQuery" ):
                listener.exitTypeQuery(self)




    def typeQuery(self):

        localctx = TypeScriptParser.TypeQueryContext(self, self._ctx, self.state)
        self.enterRule(localctx, 26, self.RULE_typeQuery)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 138
            self.match(TypeScriptParser.Typeof)
            self.state = 139
            self.match(TypeScriptParser.Identifier)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class TypeReferenceContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def Identifier(self):
            return self.getToken(TypeScriptParser.Identifier, 0)

        def LessThan(self):
            return self.getToken(TypeScriptParser.LessThan, 0)

        def typeArgumentList(self):
            return self.getTypedRuleContext(TypeScriptParser.TypeArgumentListContext,0)


        def GreaterThan(self):
            return self.getToken(TypeScriptParser.GreaterThan, 0)

        def getRuleIndex(self):
            return TypeScriptParser.RULE_typeReference

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterTypeReference" ):
                listener.enterTypeReference(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitTypeReference" ):
                listener.exitTypeReference(self)




    def typeReference(self):

        localctx = TypeScriptParser.TypeReferenceContext(self, self._ctx, self.state)
        self.enterRule(localctx, 28, self.RULE_typeReference)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 141
            self.match(TypeScriptParser.Identifier)
            self.state = 146
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==23:
                self.state = 142
                self.match(TypeScriptParser.LessThan)
                self.state = 143
                self.typeArgumentList()
                self.state = 144
                self.match(TypeScriptParser.GreaterThan)


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class TypeArgumentListContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def typeArgument(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(TypeScriptParser.TypeArgumentContext)
            else:
                return self.getTypedRuleContext(TypeScriptParser.TypeArgumentContext,i)


        def Comma(self, i:int=None):
            if i is None:
                return self.getTokens(TypeScriptParser.Comma)
            else:
                return self.getToken(TypeScriptParser.Comma, i)

        def getRuleIndex(self):
            return TypeScriptParser.RULE_typeArgumentList

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterTypeArgumentList" ):
                listener.enterTypeArgumentList(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitTypeArgumentList" ):
                listener.exitTypeArgumentList(self)




    def typeArgumentList(self):

        localctx = TypeScriptParser.TypeArgumentListContext(self, self._ctx, self.state)
        self.enterRule(localctx, 30, self.RULE_typeArgumentList)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 148
            self.typeArgument()
            self.state = 153
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==18:
                self.state = 149
                self.match(TypeScriptParser.Comma)
                self.state = 150
                self.typeArgument()
                self.state = 155
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class TypeArgumentContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def typeExpression(self):
            return self.getTypedRuleContext(TypeScriptParser.TypeExpressionContext,0)


        def getRuleIndex(self):
            return TypeScriptParser.RULE_typeArgument

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterTypeArgument" ):
                listener.enterTypeArgument(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitTypeArgument" ):
                listener.exitTypeArgument(self)




    def typeArgument(self):

        localctx = TypeScriptParser.TypeArgumentContext(self, self._ctx, self.state)
        self.enterRule(localctx, 32, self.RULE_typeArgument)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 156
            self.typeExpression()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ObjectTypeContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def OpenBrace(self):
            return self.getToken(TypeScriptParser.OpenBrace, 0)

        def CloseBrace(self):
            return self.getToken(TypeScriptParser.CloseBrace, 0)

        def memberSignature(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(TypeScriptParser.MemberSignatureContext)
            else:
                return self.getTypedRuleContext(TypeScriptParser.MemberSignatureContext,i)


        def getRuleIndex(self):
            return TypeScriptParser.RULE_objectType

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterObjectType" ):
                listener.enterObjectType(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitObjectType" ):
                listener.exitObjectType(self)




    def objectType(self):

        localctx = TypeScriptParser.ObjectTypeContext(self, self._ctx, self.state)
        self.enterRule(localctx, 34, self.RULE_objectType)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 158
            self.match(TypeScriptParser.OpenBrace)
            self.state = 162
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & 134266876) != 0):
                self.state = 159
                self.memberSignature()
                self.state = 164
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 165
            self.match(TypeScriptParser.CloseBrace)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class MemberSignatureContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def indexSignature(self):
            return self.getTypedRuleContext(TypeScriptParser.IndexSignatureContext,0)


        def propertySignature(self):
            return self.getTypedRuleContext(TypeScriptParser.PropertySignatureContext,0)


        def Semi(self):
            return self.getToken(TypeScriptParser.Semi, 0)

        def Comma(self):
            return self.getToken(TypeScriptParser.Comma, 0)

        def getRuleIndex(self):
            return TypeScriptParser.RULE_memberSignature

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterMemberSignature" ):
                listener.enterMemberSignature(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitMemberSignature" ):
                listener.exitMemberSignature(self)




    def memberSignature(self):

        localctx = TypeScriptParser.MemberSignatureContext(self, self._ctx, self.state)
        self.enterRule(localctx, 36, self.RULE_memberSignature)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 169
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [27]:
                self.state = 167
                self.indexSignature()
                pass
            elif token in [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15]:
                self.state = 168
                self.propertySignature()
                pass
            else:
                raise NoViableAltException(self)

            self.state = 172
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==16 or _la==18:
                self.state = 171
                _la = self._input.LA(1)
                if not(_la==16 or _la==18):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class IndexSignatureContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def OpenBracket(self):
            return self.getToken(TypeScriptParser.OpenBracket, 0)

        def Identifier(self):
            return self.getToken(TypeScriptParser.Identifier, 0)

        def Colon(self, i:int=None):
            if i is None:
                return self.getTokens(TypeScriptParser.Colon)
            else:
                return self.getToken(TypeScriptParser.Colon, i)

        def CloseBracket(self):
            return self.getToken(TypeScriptParser.CloseBracket, 0)

        def typeExpression(self):
            return self.getTypedRuleContext(TypeScriptParser.TypeExpressionContext,0)


        def StringType(self):
            return self.getToken(TypeScriptParser.StringType, 0)

        def NumberType(self):
            return self.getToken(TypeScriptParser.NumberType, 0)

        def getRuleIndex(self):
            return TypeScriptParser.RULE_indexSignature

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterIndexSignature" ):
                listener.enterIndexSignature(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitIndexSignature" ):
                listener.exitIndexSignature(self)




    def indexSignature(self):

        localctx = TypeScriptParser.IndexSignatureContext(self, self._ctx, self.state)
        self.enterRule(localctx, 38, self.RULE_indexSignature)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 174
            self.match(TypeScriptParser.OpenBracket)
            self.state = 175
            self.match(TypeScriptParser.Identifier)
            self.state = 176
            self.match(TypeScriptParser.Colon)
            self.state = 177
            _la = self._input.LA(1)
            if not(_la==7 or _la==8):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
            self.state = 178
            self.match(TypeScriptParser.CloseBracket)
            self.state = 179
            self.match(TypeScriptParser.Colon)
            self.state = 180
            self.typeExpression()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class PropertySignatureContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def propertyName(self):
            return self.getTypedRuleContext(TypeScriptParser.PropertyNameContext,0)


        def Colon(self):
            return self.getToken(TypeScriptParser.Colon, 0)

        def typeExpression(self):
            return self.getTypedRuleContext(TypeScriptParser.TypeExpressionContext,0)


        def QuestionMark(self):
            return self.getToken(TypeScriptParser.QuestionMark, 0)

        def getRuleIndex(self):
            return TypeScriptParser.RULE_propertySignature

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterPropertySignature" ):
                listener.enterPropertySignature(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitPropertySignature" ):
                listener.exitPropertySignature(self)




    def propertySignature(self):

        localctx = TypeScriptParser.PropertySignatureContext(self, self._ctx, self.state)
        self.enterRule(localctx, 40, self.RULE_propertySignature)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 182
            self.propertyName()
            self.state = 184
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==19:
                self.state = 183
                self.match(TypeScriptParser.QuestionMark)


            self.state = 186
            self.match(TypeScriptParser.Colon)
            self.state = 187
            self.typeExpression()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class PropertyNameContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def Identifier(self):
            return self.getToken(TypeScriptParser.Identifier, 0)

        def StringLiteral(self):
            return self.getToken(TypeScriptParser.StringLiteral, 0)

        def keywordAsIdentifier(self):
            return self.getTypedRuleContext(TypeScriptParser.KeywordAsIdentifierContext,0)


        def getRuleIndex(self):
            return TypeScriptParser.RULE_propertyName

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterPropertyName" ):
                listener.enterPropertyName(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitPropertyName" ):
                listener.exitPropertyName(self)




    def propertyName(self):

        localctx = TypeScriptParser.PropertyNameContext(self, self._ctx, self.state)
        self.enterRule(localctx, 42, self.RULE_propertyName)
        try:
            self.state = 192
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [15]:
                self.enterOuterAlt(localctx, 1)
                self.state = 189
                self.match(TypeScriptParser.Identifier)
                pass
            elif token in [13]:
                self.enterOuterAlt(localctx, 2)
                self.state = 190
                self.match(TypeScriptParser.StringLiteral)
                pass
            elif token in [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]:
                self.enterOuterAlt(localctx, 3)
                self.state = 191
                self.keywordAsIdentifier()
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class KeywordAsIdentifierContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def Type(self):
            return self.getToken(TypeScriptParser.Type, 0)

        def Const(self):
            return self.getToken(TypeScriptParser.Const, 0)

        def Interface(self):
            return self.getToken(TypeScriptParser.Interface, 0)

        def Extends(self):
            return self.getToken(TypeScriptParser.Extends, 0)

        def Typeof(self):
            return self.getToken(TypeScriptParser.Typeof, 0)

        def StringType(self):
            return self.getToken(TypeScriptParser.StringType, 0)

        def NumberType(self):
            return self.getToken(TypeScriptParser.NumberType, 0)

        def BooleanType(self):
            return self.getToken(TypeScriptParser.BooleanType, 0)

        def NullType(self):
            return self.getToken(TypeScriptParser.NullType, 0)

        def UnknownType(self):
            return self.getToken(TypeScriptParser.UnknownType, 0)

        def AnyType(self):
            return self.getToken(TypeScriptParser.AnyType, 0)

        def getRuleIndex(self):
            return TypeScriptParser.RULE_keywordAsIdentifier

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterKeywordAsIdentifier" ):
                listener.enterKeywordAsIdentifier(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitKeywordAsIdentifier" ):
                listener.exitKeywordAsIdentifier(self)




    def keywordAsIdentifier(self):

        localctx = TypeScriptParser.KeywordAsIdentifierContext(self, self._ctx, self.state)
        self.enterRule(localctx, 44, self.RULE_keywordAsIdentifier)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 194
            _la = self._input.LA(1)
            if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 8188) != 0)):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx





