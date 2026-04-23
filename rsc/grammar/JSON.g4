grammar JSON;
jSON: WhiteSpace* jSONValue WhiteSpace* EOF;
jSONValue: jSONPrimitiveValue | jSONContainerValue;
jSONPrimitiveValue:
	jSONNullValue
	| jSONBooleanValue
	| jSONNumberValue
	| jSONStringValue;
jSONNullValue: Null;
jSONBooleanValue: True | False;
jSONNumberValue: jSONInteger DecimalFraction? DecimalExponent?;
jSONInteger: MinusSign? DecimalUnsignedInteger;
jSONStringValue: String;
jSONContainerValue: jSONArrayValue | jSONObjectValue;
jSONArrayValue:
	open = OpenArray (
		WhiteSpace*
		| WhiteSpace* jSONValue WhiteSpace* (
			separator = ContainerItemSeparator WhiteSpace* jSONValue WhiteSpace*
		)*
	) close = CloseArray;
jSONObjectValue:
	open = OpenObject (
		WhiteSpace*
		| WhiteSpace* jSONMember WhiteSpace* (
			separator = ContainerItemSeparator WhiteSpace* jSONMember WhiteSpace*
		)*
	) close = CloseObject;
jSONMember:
	key = jSONStringValue WhiteSpace* separator = KeyValueSeparator WhiteSpace* jSONValue;
Null: 'null';
True: 'true';
False: 'false';
DecimalUnsignedInteger: ('0' | [1-9] DecimalDigit*);
DecimalFraction: IntegerFractionSeparator DecimalDigit+;
DecimalExponent: [Ee] (PlusSign | MinusSign)? DecimalDigit+;
String: OpenString (EscapedChar | NonEscapedChar)* CloseString;
OpenString: DoubleQuote;
CloseString: DoubleQuote;
fragment DoubleQuote: '"';
OpenArray: OpenSquareBracket;
fragment OpenSquareBracket: '[';
CloseArray: CloseSquareBracket;
fragment CloseSquareBracket: ']';
OpenObject: OpenCurlyBracket;
fragment OpenCurlyBracket: '{';
CloseObject: CloseCurlyBracket;
fragment CloseCurlyBracket: '}';
ContainerItemSeparator: Comma;
fragment Comma: ',';
KeyValueSeparator: Colon;
fragment Colon: ':';
IntegerFractionSeparator: Period;
fragment Period: '.';
Escape: Backslash;
fragment Backslash: '\\';
PlusSign: '+';
MinusSign: '-';
WhiteSpace: ([ ] | [\t\n\r])+ -> channel(HIDDEN);
EscapedChar:
	Escape DoubleQuote
	| Escape Escape
	| Escape [tnr]
	| Escape [/bf]
	| Escape 'u' HexadecimalDigit HexadecimalDigit HexadecimalDigit HexadecimalDigit;
NonEscapedChar: ~(["] | [\\] | [\u0000-\u001F]);
DecimalDigit: [0-9];
HexadecimalDigit: DecimalDigit | [A-Fa-f];
