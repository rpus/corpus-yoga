grammar draft04;
json: WhiteSpace* value WhiteSpace* EOF;
value: primitiveValue | containerValue;
primitiveValue:
	nullValue
	| booleanValue
	| numberValue
	| stringValue
	;
nullValue: NullValue;
booleanValue: TrueValue | FalseValue;
numberValue: integer Fraction? Exponent?;
integer: MinusSign? UnsignedInteger;
stringValue: name | String;
containerValue: arrayValue | objectValue;
arrayValue:
	schemaObjectArray
	| typeNameArray
	| open = OpenArray (
		WhiteSpace*
		| WhiteSpace* value WhiteSpace* (
			separator = ContainerItemSeparator WhiteSpace* value WhiteSpace*
		)*
	) close = CloseArray;
schemaObjectArray:
	open = OpenArray (
		WhiteSpace*
		| WhiteSpace* schemaObjectValue WhiteSpace* (
			separator = ContainerItemSeparator WhiteSpace* schemaObjectValue WhiteSpace*
		)*
	) close = CloseArray;
typeNameArray:
	open = OpenArray (
		WhiteSpace*
		| WhiteSpace* typeName WhiteSpace* (
			separator = ContainerItemSeparator WhiteSpace* typeName WhiteSpace*
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
		(
			WhiteSpace* (
				jsonSchemaProperty
				| proprietaryProperty
			) WhiteSpace* separator = ContainerItemSeparator
		)* WhiteSpace* dollarReferenceProperty WhiteSpace* (
			separator = ContainerItemSeparator WhiteSpace* (
				jsonSchemaProperty
				| proprietaryProperty
			) WhiteSpace*
		)*
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
	| descriptionProperty
	| titleProperty
	| idProperty
	| dollarIdProperty
	| dollarSchemaProperty
	;
defaultProperty:
	key = DefaultPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* value;
definitionsProperty:
	key = DefinitionsPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* objectValue;
descriptionProperty:
	key = DescriptionPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* stringValue;
titleProperty:
	key = TitlePropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* stringValue;
idProperty:
	key = IdPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* stringValue;
dollarIdProperty:
	key = DollarIdPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* stringValue;
dollarSchemaProperty:
	key = DollarSchemaPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* stringValue;
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
	| typeProperty
	| multipleOfProperty
	| maximumProperty
	| exclusiveMaximumProperty
	| minimumProperty
	| exclusiveMinimumProperty
	| maxLengthProperty
	| minLengthProperty
	| patternProperty
	| maxItemsProperty
	| uniqueItemsProperty
	| maxPropertiesProperty
	| minPropertiesProperty
	| patternPropertiesProperty
	| dependenciesProperty
	| formatProperty
	;
additionalItemsProperty:
	key = AdditionalItemsPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* (
		booleanValue
		| schemaObjectValue
	);
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
	key = ItemsPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* (
		schemaObjectValue
		| schemaObjectArray
	);
minItemsProperty:
	key = MinItemsPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* UnsignedInteger;
notProperty:
	key = NotPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* schemaObjectValue;
oneOfProperty:
	key = OneOfPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* arrayValue;
propertiesProperty:
	key = PropertiesPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* objectValue;
requiredProperty:
	key = RequiredPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* arrayValue;
typeProperty:
	key = TypePropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* (
		typeName
		| typeNameArray
	);
multipleOfProperty:
	key = MultipleOfPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* numberValue;
maximumProperty:
	key = MaximumPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* numberValue;
exclusiveMaximumProperty:
	key = ExclusiveMaximumPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* booleanValue;
minimumProperty:
	key = MinimumPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* numberValue;
exclusiveMinimumProperty:
	key = ExclusiveMinimumPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* booleanValue;
maxLengthProperty:
	key = MaxLengthPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* UnsignedInteger;
minLengthProperty:
	key = MinLengthPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* UnsignedInteger;
patternProperty:
	key = PatternPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* stringValue;
maxItemsProperty:
	key = MaxItemsPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* UnsignedInteger;
uniqueItemsProperty:
	key = UniqueItemsPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* booleanValue;
maxPropertiesProperty:
	key = MaxPropertiesPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* UnsignedInteger;
minPropertiesProperty:
	key = MinPropertiesPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* UnsignedInteger;
patternPropertiesProperty:
	key = PatternPropertiesPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* objectValue;
dependenciesProperty:
	key = DependenciesPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* objectValue;
formatProperty:
	key = FormatPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* stringValue;
extension: extendsProperty | implementsProperty;
extendsProperty:
	key = ExtendsPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* jsonReferenceSchemaObjectValue;
implementsProperty:
	key = ImplementsPropertyName WhiteSpace* separator = KeyValueSeparator WhiteSpace* arrayValue;
name: propertyName | typeName | extensionKeyword;
propertyName:
	DollarRefPropertyName
	| DefaultPropertyName
	| DefinitionsPropertyName
	| DescriptionPropertyName
	| TitlePropertyName
	| IdPropertyName
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
	| TypePropertyName
	| MultipleOfPropertyName
	| MaximumPropertyName
	| ExclusiveMaximumPropertyName
	| MinimumPropertyName
	| ExclusiveMinimumPropertyName
	| MaxLengthPropertyName
	| MinLengthPropertyName
	| PatternPropertyName
	| MaxItemsPropertyName
	| UniqueItemsPropertyName
	| MaxPropertiesPropertyName
	| MinPropertiesPropertyName
	| PatternPropertiesPropertyName
	| DependenciesPropertyName
	| FormatPropertyName
	;
typeName:
	ArrayTypeName
	| ObjectTypeName
	| StringTypeName
	| NumberTypeName
	| IntegerTypeName
	| BooleanTypeName
	| NullTypeName
	;
extensionKeyword: ExtendsPropertyName | ImplementsPropertyName;
DollarRefPropertyName: '"$ref"';
DefaultPropertyName: '"default"';
DefinitionsPropertyName: '"definitions"';
DescriptionPropertyName: '"description"';
TitlePropertyName: '"title"';
IdPropertyName: '"id"';
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
MultipleOfPropertyName: '"multipleOf"';
MaximumPropertyName: '"maximum"';
ExclusiveMaximumPropertyName: '"exclusiveMaximum"';
MinimumPropertyName: '"minimum"';
ExclusiveMinimumPropertyName: '"exclusiveMinimum"';
MaxLengthPropertyName: '"maxLength"';
MinLengthPropertyName: '"minLength"';
PatternPropertyName: '"pattern"';
MaxItemsPropertyName: '"maxItems"';
UniqueItemsPropertyName: '"uniqueItems"';
MaxPropertiesPropertyName: '"maxProperties"';
MinPropertiesPropertyName: '"minProperties"';
PatternPropertiesPropertyName: '"patternProperties"';
DependenciesPropertyName: '"dependencies"';
FormatPropertyName: '"format"';
ArrayTypeName: '"array"';
ObjectTypeName: '"object"';
StringTypeName: '"string"';
NumberTypeName: '"number"';
IntegerTypeName: '"integer"';
BooleanTypeName: '"boolean"';
NullTypeName: '"null"';
ExtendsPropertyName: '"extends"';
ImplementsPropertyName: '"implements"';
NullValue: 'null';
TrueValue: 'true';
FalseValue: 'false';
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
