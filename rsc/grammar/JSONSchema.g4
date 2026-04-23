grammar JSONSchema;
json: WhiteSpace* value WhiteSpace* EOF;
value: primitiveValue | containerValue;
primitiveValue:
	nullValue
	| booleanValue
	| numberValue
	| stringValue;
nullValue: Null;
booleanValue: True | False;
numberValue: integer Fraction? Exponent?;
integer: MinusSign? UnsignedInteger;
stringValue: name | String;
containerValue: arrayValue | objectValue;
arrayValue:
	open = OpenArray (
		WhiteSpace*
		| WhiteSpace* value WhiteSpace* (
			separator = ContainerItemSeparator WhiteSpace* value WhiteSpace*
		)*
	) close = CloseArray;
objectValue:
	schemaObjectValue
	| open = OpenObject (
		WhiteSpace*
		| WhiteSpace* member WhiteSpace* (
			separator = ContainerItemSeparator WhiteSpace* member WhiteSpace*
		)*
	) close = CloseObject;
member:
	key = stringValue WhiteSpace* separator = KeyValueSeparator WhiteSpace* value;
schemaObjectValue:
	jsonReferenceSchemaObjectValue
	| literalSchemaObjectValue
	| extendedSchemaObjectValue;
jsonReferenceSchemaObjectValue:
	open = OpenObject (
		WhiteSpace* dollarReferenceProperty WhiteSpace*
	) close = CloseObject;
dollarReferenceProperty:
	key = DollarRefPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* stringValue;
literalSchemaObjectValue:
	open = OpenObject (
		WhiteSpace*
		| WhiteSpace* jsonSchemaProperty WhiteSpace* (
			separator = ContainerItemSeparator WhiteSpace* jsonSchemaProperty WhiteSpace*
		)*
	) close = CloseObject;
jsonSchemaProperty: annotation | restriction;
extendedSchemaObjectValue:
	open = OpenObject (
		(
			WhiteSpace* (
				jsonSchemaProperty
				| proprietaryProperty
			) WhiteSpace* separator = ContainerItemSeparator
		)* WhiteSpace* proprietaryProperty WhiteSpace* (
			separator = ContainerItemSeparator WhiteSpace* (
				jsonSchemaProperty
				| proprietaryProperty
			) WhiteSpace*
		)*
	) close = CloseObject;
proprietaryProperty: extension;
annotation:
	defaultProperty
	| definitionsProperty
	| dollarIdProperty
	| dollarSchemaProperty;
defaultProperty:
	key = DefaultPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* value;
definitionsProperty:
	key = DefinitionsPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* objectValue;
dollarIdProperty:
	key = DollarIdPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* stringValue;
dollarSchemaProperty:
	key = DollarSchemaPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* stringValue
		;
restriction:
	additionalItemsProperty
	| additionalPropertiesProperty
	| allOfProperty
	| anyOfProperty
	| enumProperty
	| itemsProperty
	| minItemsProperty
	| notProperty
	| oneOfProperty
	| propertiesProperty
	| requiredProperty
	| typeProperty;
additionalItemsProperty:
	key = AdditionalItemsPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace*
		schemaObjectValue;
additionalPropertiesProperty:
	key = AdditionalPropertiesPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* (
		booleanValue
		| schemaObjectValue
	);
allOfProperty:
	key = AllOfPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* arrayValue;
anyOfProperty:
	key = AnyOfPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* arrayValue;
enumProperty:
	key = EnumPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* arrayValue;
itemsProperty:
	key = ItemsPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* schemaObjectValue;
minItemsProperty:
	key = MinItemsPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* UnsignedInteger
		;
notProperty:
	key = NotPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* schemaObjectValue;
oneOfProperty:
	key = OneOfPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* arrayValue;
propertiesProperty:
	key = PropertiesPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* objectValue;
requiredProperty:
	key = RequiredPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* arrayValue;
typeProperty:
	key = TypePropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* typeName;
extension: extendsProperty | implementsProperty;
extendsProperty:
	key = ExtendsPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace*
		jsonReferenceSchemaObjectValue;
implementsProperty:
	key = ImplementsPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* arrayValue;
name: propertyName | typeName | extensionKeyword;
propertyName:
	DollarRefPropertyName
	| DefaultPropertyName
	| DefinitionsPropertyName
	| DollarIdPropertyName
	| DollarSchemaPropertyName
	| AdditionalItemsPropertyName
	| AdditionalPropertiesPropertyName
	| AllOfPropertyName
	| AnyOfPropertyName
	| EnumPropertyName
	| ItemsPropertyName
	| MinItemsPropertyName
	| NotPropertyName
	| OneOfPropertyName
	| PropertiesPropertyName
	| RequiredPropertyName
	| TypePropertyName;
typeName:
	ArrayTypeName
	| ObjectTypeName
	| StringTypeName
	| NumberTypeName
	| IntegerTypeName
	| BooleanTypeName
	| NullTypeName;
extensionKeyword: ExtendsPropertyName | ImplementsPropertyName;
DollarRefPropertyName: '"$ref"';
DefaultPropertyName: '"default"';
DefinitionsPropertyName: '"definitions"';
DollarIdPropertyName: '"$id"';
DollarSchemaPropertyName: '"$schema"';
AdditionalItemsPropertyName: '"additionalItems"';
AdditionalPropertiesPropertyName: '"additionalProperties"';
AllOfPropertyName: '"allOf"';
AnyOfPropertyName: '"anyOf"';
EnumPropertyName: '"enum"';
ItemsPropertyName: '"items"';
MinItemsPropertyName: '"minItems"';
NotPropertyName: '"not"';
OneOfPropertyName: '"oneOf"';
PropertiesPropertyName: '"properties"';
RequiredPropertyName: '"required"';
TypePropertyName: '"type"';
ArrayTypeName: '"array"';
ObjectTypeName: '"object"';
StringTypeName: '"string"';
NumberTypeName: '"number"';
IntegerTypeName: '"integer"';
BooleanTypeName: '"boolean"';
NullTypeName: '"null"';
ExtendsPropertyName: '"extends"';
ImplementsPropertyName: '"implements"';
Null: 'null';
True: 'true';
False: 'false';
UnsignedInteger: ('0' | [1-9] DecimalDigit*);
Fraction: DecimalSeparator DecimalDigit+;
Exponent: [Ee] (PlusSign | MinusSign)? DecimalDigit+;
String: DoubleQuote (EscapedChar | NonEscapedChar)* DoubleQuote;
DoubleQuote: '"';
OpenArray: '[';
CloseArray: ']';
OpenObject: '{';
CloseObject: '}';
ContainerItemSeparator: ',';
KeyValueSeparator: ':';
DecimalSeparator: '.';
PlusSign: '+';
MinusSign: '-';
WhiteSpace: [ \t\n\r]+ -> channel(HIDDEN);
EscapedChar:
	'\\' ["\\/bfnrt]
	| '\\' 'u' HexadecimalDigit HexadecimalDigit HexadecimalDigit HexadecimalDigit;
NonEscapedChar: ~["\\\u0000-\u001F];
DecimalDigit: [0-9];
HexadecimalDigit: DecimalDigit | [A-Fa-f];
