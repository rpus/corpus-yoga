parser grammar TypeScriptParser;

options {
	tokenVocab = TypeScriptLexer;
}

typeScriptFile: declaration* EOF;

declaration:
	constDeclaration
	| typeAliasDeclaration
	| interfaceDeclaration
	;

constDeclaration:
	Export Const Identifier (Colon typeExpression)? Equals constValue Semi;

constValue:
	StringLiteral
	| IntegerLiteral
	;

typeAliasDeclaration:
	Export Type Identifier Equals typeExpression Semi;

interfaceDeclaration:
	Export Interface Identifier extendsClause? objectType;

extendsClause:
	Extends typeReference (Comma typeReference)*;

typeExpression: unionType;

unionType:
	Pipe? intersectionType (Pipe intersectionType)*;

intersectionType:
	arrayOrPrimaryType (Ampersand arrayOrPrimaryType)*;

arrayOrPrimaryType:
	primaryType (OpenBracket CloseBracket)*;

primaryType:
	primitiveType
	| StringLiteral
	| typeQuery
	| typeReference
	| objectType
	| OpenParen typeExpression CloseParen
	;

primitiveType:
	StringType
	| NumberType
	| BooleanType
	| NullType
	| UnknownType
	| AnyType
	;

typeQuery:
	Typeof Identifier;

typeReference:
	Identifier (LessThan typeArgumentList GreaterThan)?;

typeArgumentList:
	typeArgument (Comma typeArgument)*;

typeArgument:
	typeExpression
	;

objectType:
	OpenBrace memberSignature* CloseBrace;

memberSignature:
	(indexSignature | propertySignature) (Semi | Comma)?;

indexSignature:
	OpenBracket Identifier Colon (StringType | NumberType) CloseBracket Colon typeExpression;

propertySignature:
	propertyName QuestionMark? Colon typeExpression;

propertyName:
	Identifier
	| StringLiteral
	| keywordAsIdentifier
	;

keywordAsIdentifier:
	Type
	| Const
	| Interface
	| Extends
	| Typeof
	| StringType
	| NumberType
	| BooleanType
	| NullType
	| UnknownType
	| AnyType
	;
