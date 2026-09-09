# Generated from TypeScriptParser.g4 by ANTLR 4.13.2
from antlr4 import *
if "." in __name__:
    from .TypeScriptParser import TypeScriptParser
else:
    from TypeScriptParser import TypeScriptParser

# This class defines a complete listener for a parse tree produced by TypeScriptParser.
class TypeScriptParserListener(ParseTreeListener):

    # Enter a parse tree produced by TypeScriptParser#typeScriptFile.
    def enterTypeScriptFile(self, ctx:TypeScriptParser.TypeScriptFileContext):
        pass

    # Exit a parse tree produced by TypeScriptParser#typeScriptFile.
    def exitTypeScriptFile(self, ctx:TypeScriptParser.TypeScriptFileContext):
        pass


    # Enter a parse tree produced by TypeScriptParser#declaration.
    def enterDeclaration(self, ctx:TypeScriptParser.DeclarationContext):
        pass

    # Exit a parse tree produced by TypeScriptParser#declaration.
    def exitDeclaration(self, ctx:TypeScriptParser.DeclarationContext):
        pass


    # Enter a parse tree produced by TypeScriptParser#constDeclaration.
    def enterConstDeclaration(self, ctx:TypeScriptParser.ConstDeclarationContext):
        pass

    # Exit a parse tree produced by TypeScriptParser#constDeclaration.
    def exitConstDeclaration(self, ctx:TypeScriptParser.ConstDeclarationContext):
        pass


    # Enter a parse tree produced by TypeScriptParser#constValue.
    def enterConstValue(self, ctx:TypeScriptParser.ConstValueContext):
        pass

    # Exit a parse tree produced by TypeScriptParser#constValue.
    def exitConstValue(self, ctx:TypeScriptParser.ConstValueContext):
        pass


    # Enter a parse tree produced by TypeScriptParser#typeAliasDeclaration.
    def enterTypeAliasDeclaration(self, ctx:TypeScriptParser.TypeAliasDeclarationContext):
        pass

    # Exit a parse tree produced by TypeScriptParser#typeAliasDeclaration.
    def exitTypeAliasDeclaration(self, ctx:TypeScriptParser.TypeAliasDeclarationContext):
        pass


    # Enter a parse tree produced by TypeScriptParser#interfaceDeclaration.
    def enterInterfaceDeclaration(self, ctx:TypeScriptParser.InterfaceDeclarationContext):
        pass

    # Exit a parse tree produced by TypeScriptParser#interfaceDeclaration.
    def exitInterfaceDeclaration(self, ctx:TypeScriptParser.InterfaceDeclarationContext):
        pass


    # Enter a parse tree produced by TypeScriptParser#extendsClause.
    def enterExtendsClause(self, ctx:TypeScriptParser.ExtendsClauseContext):
        pass

    # Exit a parse tree produced by TypeScriptParser#extendsClause.
    def exitExtendsClause(self, ctx:TypeScriptParser.ExtendsClauseContext):
        pass


    # Enter a parse tree produced by TypeScriptParser#typeExpression.
    def enterTypeExpression(self, ctx:TypeScriptParser.TypeExpressionContext):
        pass

    # Exit a parse tree produced by TypeScriptParser#typeExpression.
    def exitTypeExpression(self, ctx:TypeScriptParser.TypeExpressionContext):
        pass


    # Enter a parse tree produced by TypeScriptParser#unionType.
    def enterUnionType(self, ctx:TypeScriptParser.UnionTypeContext):
        pass

    # Exit a parse tree produced by TypeScriptParser#unionType.
    def exitUnionType(self, ctx:TypeScriptParser.UnionTypeContext):
        pass


    # Enter a parse tree produced by TypeScriptParser#intersectionType.
    def enterIntersectionType(self, ctx:TypeScriptParser.IntersectionTypeContext):
        pass

    # Exit a parse tree produced by TypeScriptParser#intersectionType.
    def exitIntersectionType(self, ctx:TypeScriptParser.IntersectionTypeContext):
        pass


    # Enter a parse tree produced by TypeScriptParser#arrayOrPrimaryType.
    def enterArrayOrPrimaryType(self, ctx:TypeScriptParser.ArrayOrPrimaryTypeContext):
        pass

    # Exit a parse tree produced by TypeScriptParser#arrayOrPrimaryType.
    def exitArrayOrPrimaryType(self, ctx:TypeScriptParser.ArrayOrPrimaryTypeContext):
        pass


    # Enter a parse tree produced by TypeScriptParser#primaryType.
    def enterPrimaryType(self, ctx:TypeScriptParser.PrimaryTypeContext):
        pass

    # Exit a parse tree produced by TypeScriptParser#primaryType.
    def exitPrimaryType(self, ctx:TypeScriptParser.PrimaryTypeContext):
        pass


    # Enter a parse tree produced by TypeScriptParser#primitiveType.
    def enterPrimitiveType(self, ctx:TypeScriptParser.PrimitiveTypeContext):
        pass

    # Exit a parse tree produced by TypeScriptParser#primitiveType.
    def exitPrimitiveType(self, ctx:TypeScriptParser.PrimitiveTypeContext):
        pass


    # Enter a parse tree produced by TypeScriptParser#typeQuery.
    def enterTypeQuery(self, ctx:TypeScriptParser.TypeQueryContext):
        pass

    # Exit a parse tree produced by TypeScriptParser#typeQuery.
    def exitTypeQuery(self, ctx:TypeScriptParser.TypeQueryContext):
        pass


    # Enter a parse tree produced by TypeScriptParser#typeReference.
    def enterTypeReference(self, ctx:TypeScriptParser.TypeReferenceContext):
        pass

    # Exit a parse tree produced by TypeScriptParser#typeReference.
    def exitTypeReference(self, ctx:TypeScriptParser.TypeReferenceContext):
        pass


    # Enter a parse tree produced by TypeScriptParser#typeArgumentList.
    def enterTypeArgumentList(self, ctx:TypeScriptParser.TypeArgumentListContext):
        pass

    # Exit a parse tree produced by TypeScriptParser#typeArgumentList.
    def exitTypeArgumentList(self, ctx:TypeScriptParser.TypeArgumentListContext):
        pass


    # Enter a parse tree produced by TypeScriptParser#typeArgument.
    def enterTypeArgument(self, ctx:TypeScriptParser.TypeArgumentContext):
        pass

    # Exit a parse tree produced by TypeScriptParser#typeArgument.
    def exitTypeArgument(self, ctx:TypeScriptParser.TypeArgumentContext):
        pass


    # Enter a parse tree produced by TypeScriptParser#objectType.
    def enterObjectType(self, ctx:TypeScriptParser.ObjectTypeContext):
        pass

    # Exit a parse tree produced by TypeScriptParser#objectType.
    def exitObjectType(self, ctx:TypeScriptParser.ObjectTypeContext):
        pass


    # Enter a parse tree produced by TypeScriptParser#memberSignature.
    def enterMemberSignature(self, ctx:TypeScriptParser.MemberSignatureContext):
        pass

    # Exit a parse tree produced by TypeScriptParser#memberSignature.
    def exitMemberSignature(self, ctx:TypeScriptParser.MemberSignatureContext):
        pass


    # Enter a parse tree produced by TypeScriptParser#indexSignature.
    def enterIndexSignature(self, ctx:TypeScriptParser.IndexSignatureContext):
        pass

    # Exit a parse tree produced by TypeScriptParser#indexSignature.
    def exitIndexSignature(self, ctx:TypeScriptParser.IndexSignatureContext):
        pass


    # Enter a parse tree produced by TypeScriptParser#propertySignature.
    def enterPropertySignature(self, ctx:TypeScriptParser.PropertySignatureContext):
        pass

    # Exit a parse tree produced by TypeScriptParser#propertySignature.
    def exitPropertySignature(self, ctx:TypeScriptParser.PropertySignatureContext):
        pass


    # Enter a parse tree produced by TypeScriptParser#propertyName.
    def enterPropertyName(self, ctx:TypeScriptParser.PropertyNameContext):
        pass

    # Exit a parse tree produced by TypeScriptParser#propertyName.
    def exitPropertyName(self, ctx:TypeScriptParser.PropertyNameContext):
        pass


    # Enter a parse tree produced by TypeScriptParser#keywordAsIdentifier.
    def enterKeywordAsIdentifier(self, ctx:TypeScriptParser.KeywordAsIdentifierContext):
        pass

    # Exit a parse tree produced by TypeScriptParser#keywordAsIdentifier.
    def exitKeywordAsIdentifier(self, ctx:TypeScriptParser.KeywordAsIdentifierContext):
        pass



del TypeScriptParser