lexer grammar TypeScriptLexer;

channels {
	COMMENT
}

Export: 'export';
Const: 'const';
Type: 'type';
Interface: 'interface';
Extends: 'extends';
Typeof: 'typeof';

StringType: 'string';
NumberType: 'number';
BooleanType: 'boolean';
NullType: 'null';
UnknownType: 'unknown';
AnyType: 'any';

StringLiteral: DoubleQuote (EscapedChar | NonEscapedChar)* DoubleQuote;
IntegerLiteral: MinusSign? UnsignedInteger;

Identifier: [a-zA-Z_$] [a-zA-Z0-9_$]*;

Semi: ';';
Colon: ':';
Comma: ',';
QuestionMark: '?';
Pipe: '|';
Ampersand: '&';
Equals: '=';
LessThan: '<';
GreaterThan: '>';
OpenBrace: '{';
CloseBrace: '}';
OpenBracket: '[';
CloseBracket: ']';
OpenParen: '(';
CloseParen: ')';

LineComment: '//' ~[\r\n]* -> channel(COMMENT);
BlockComment: '/*' .*? '*/' -> channel(COMMENT);
WhiteSpace: [ \t\r\n]+ -> channel(HIDDEN);

fragment DoubleQuote: '"';
fragment MinusSign: '-';
fragment UnsignedInteger: '0' | [1-9] [0-9]*;
fragment EscapedChar: '\\' .;
fragment NonEscapedChar: ~["\\\r\n];
