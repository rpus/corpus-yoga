# Generated from draft04.g4 by ANTLR 4.13.2
from antlr4 import *
if "." in __name__:
    from .draft04Parser import draft04Parser
else:
    from draft04Parser import draft04Parser

# This class defines a complete listener for a parse tree produced by draft04Parser.
class draft04Listener(ParseTreeListener):

    # Enter a parse tree produced by draft04Parser#json.
    def enterJson(self, ctx:draft04Parser.JsonContext):
        pass

    # Exit a parse tree produced by draft04Parser#json.
    def exitJson(self, ctx:draft04Parser.JsonContext):
        pass


    # Enter a parse tree produced by draft04Parser#value.
    def enterValue(self, ctx:draft04Parser.ValueContext):
        pass

    # Exit a parse tree produced by draft04Parser#value.
    def exitValue(self, ctx:draft04Parser.ValueContext):
        pass


    # Enter a parse tree produced by draft04Parser#primitiveValue.
    def enterPrimitiveValue(self, ctx:draft04Parser.PrimitiveValueContext):
        pass

    # Exit a parse tree produced by draft04Parser#primitiveValue.
    def exitPrimitiveValue(self, ctx:draft04Parser.PrimitiveValueContext):
        pass


    # Enter a parse tree produced by draft04Parser#nullValue.
    def enterNullValue(self, ctx:draft04Parser.NullValueContext):
        pass

    # Exit a parse tree produced by draft04Parser#nullValue.
    def exitNullValue(self, ctx:draft04Parser.NullValueContext):
        pass


    # Enter a parse tree produced by draft04Parser#booleanValue.
    def enterBooleanValue(self, ctx:draft04Parser.BooleanValueContext):
        pass

    # Exit a parse tree produced by draft04Parser#booleanValue.
    def exitBooleanValue(self, ctx:draft04Parser.BooleanValueContext):
        pass


    # Enter a parse tree produced by draft04Parser#numberValue.
    def enterNumberValue(self, ctx:draft04Parser.NumberValueContext):
        pass

    # Exit a parse tree produced by draft04Parser#numberValue.
    def exitNumberValue(self, ctx:draft04Parser.NumberValueContext):
        pass


    # Enter a parse tree produced by draft04Parser#integer.
    def enterInteger(self, ctx:draft04Parser.IntegerContext):
        pass

    # Exit a parse tree produced by draft04Parser#integer.
    def exitInteger(self, ctx:draft04Parser.IntegerContext):
        pass


    # Enter a parse tree produced by draft04Parser#stringValue.
    def enterStringValue(self, ctx:draft04Parser.StringValueContext):
        pass

    # Exit a parse tree produced by draft04Parser#stringValue.
    def exitStringValue(self, ctx:draft04Parser.StringValueContext):
        pass


    # Enter a parse tree produced by draft04Parser#containerValue.
    def enterContainerValue(self, ctx:draft04Parser.ContainerValueContext):
        pass

    # Exit a parse tree produced by draft04Parser#containerValue.
    def exitContainerValue(self, ctx:draft04Parser.ContainerValueContext):
        pass


    # Enter a parse tree produced by draft04Parser#arrayValue.
    def enterArrayValue(self, ctx:draft04Parser.ArrayValueContext):
        pass

    # Exit a parse tree produced by draft04Parser#arrayValue.
    def exitArrayValue(self, ctx:draft04Parser.ArrayValueContext):
        pass


    # Enter a parse tree produced by draft04Parser#schemaObjectArray.
    def enterSchemaObjectArray(self, ctx:draft04Parser.SchemaObjectArrayContext):
        pass

    # Exit a parse tree produced by draft04Parser#schemaObjectArray.
    def exitSchemaObjectArray(self, ctx:draft04Parser.SchemaObjectArrayContext):
        pass


    # Enter a parse tree produced by draft04Parser#typeNameArray.
    def enterTypeNameArray(self, ctx:draft04Parser.TypeNameArrayContext):
        pass

    # Exit a parse tree produced by draft04Parser#typeNameArray.
    def exitTypeNameArray(self, ctx:draft04Parser.TypeNameArrayContext):
        pass


    # Enter a parse tree produced by draft04Parser#objectValue.
    def enterObjectValue(self, ctx:draft04Parser.ObjectValueContext):
        pass

    # Exit a parse tree produced by draft04Parser#objectValue.
    def exitObjectValue(self, ctx:draft04Parser.ObjectValueContext):
        pass


    # Enter a parse tree produced by draft04Parser#member.
    def enterMember(self, ctx:draft04Parser.MemberContext):
        pass

    # Exit a parse tree produced by draft04Parser#member.
    def exitMember(self, ctx:draft04Parser.MemberContext):
        pass


    # Enter a parse tree produced by draft04Parser#schemaObjectValue.
    def enterSchemaObjectValue(self, ctx:draft04Parser.SchemaObjectValueContext):
        pass

    # Exit a parse tree produced by draft04Parser#schemaObjectValue.
    def exitSchemaObjectValue(self, ctx:draft04Parser.SchemaObjectValueContext):
        pass


    # Enter a parse tree produced by draft04Parser#jsonReferenceSchemaObjectValue.
    def enterJsonReferenceSchemaObjectValue(self, ctx:draft04Parser.JsonReferenceSchemaObjectValueContext):
        pass

    # Exit a parse tree produced by draft04Parser#jsonReferenceSchemaObjectValue.
    def exitJsonReferenceSchemaObjectValue(self, ctx:draft04Parser.JsonReferenceSchemaObjectValueContext):
        pass


    # Enter a parse tree produced by draft04Parser#dollarReferenceProperty.
    def enterDollarReferenceProperty(self, ctx:draft04Parser.DollarReferencePropertyContext):
        pass

    # Exit a parse tree produced by draft04Parser#dollarReferenceProperty.
    def exitDollarReferenceProperty(self, ctx:draft04Parser.DollarReferencePropertyContext):
        pass


    # Enter a parse tree produced by draft04Parser#literalSchemaObjectValue.
    def enterLiteralSchemaObjectValue(self, ctx:draft04Parser.LiteralSchemaObjectValueContext):
        pass

    # Exit a parse tree produced by draft04Parser#literalSchemaObjectValue.
    def exitLiteralSchemaObjectValue(self, ctx:draft04Parser.LiteralSchemaObjectValueContext):
        pass


    # Enter a parse tree produced by draft04Parser#jsonSchemaProperty.
    def enterJsonSchemaProperty(self, ctx:draft04Parser.JsonSchemaPropertyContext):
        pass

    # Exit a parse tree produced by draft04Parser#jsonSchemaProperty.
    def exitJsonSchemaProperty(self, ctx:draft04Parser.JsonSchemaPropertyContext):
        pass


    # Enter a parse tree produced by draft04Parser#extendedSchemaObjectValue.
    def enterExtendedSchemaObjectValue(self, ctx:draft04Parser.ExtendedSchemaObjectValueContext):
        pass

    # Exit a parse tree produced by draft04Parser#extendedSchemaObjectValue.
    def exitExtendedSchemaObjectValue(self, ctx:draft04Parser.ExtendedSchemaObjectValueContext):
        pass


    # Enter a parse tree produced by draft04Parser#proprietaryProperty.
    def enterProprietaryProperty(self, ctx:draft04Parser.ProprietaryPropertyContext):
        pass

    # Exit a parse tree produced by draft04Parser#proprietaryProperty.
    def exitProprietaryProperty(self, ctx:draft04Parser.ProprietaryPropertyContext):
        pass


    # Enter a parse tree produced by draft04Parser#annotation.
    def enterAnnotation(self, ctx:draft04Parser.AnnotationContext):
        pass

    # Exit a parse tree produced by draft04Parser#annotation.
    def exitAnnotation(self, ctx:draft04Parser.AnnotationContext):
        pass


    # Enter a parse tree produced by draft04Parser#defaultProperty.
    def enterDefaultProperty(self, ctx:draft04Parser.DefaultPropertyContext):
        pass

    # Exit a parse tree produced by draft04Parser#defaultProperty.
    def exitDefaultProperty(self, ctx:draft04Parser.DefaultPropertyContext):
        pass


    # Enter a parse tree produced by draft04Parser#definitionsProperty.
    def enterDefinitionsProperty(self, ctx:draft04Parser.DefinitionsPropertyContext):
        pass

    # Exit a parse tree produced by draft04Parser#definitionsProperty.
    def exitDefinitionsProperty(self, ctx:draft04Parser.DefinitionsPropertyContext):
        pass


    # Enter a parse tree produced by draft04Parser#descriptionProperty.
    def enterDescriptionProperty(self, ctx:draft04Parser.DescriptionPropertyContext):
        pass

    # Exit a parse tree produced by draft04Parser#descriptionProperty.
    def exitDescriptionProperty(self, ctx:draft04Parser.DescriptionPropertyContext):
        pass


    # Enter a parse tree produced by draft04Parser#titleProperty.
    def enterTitleProperty(self, ctx:draft04Parser.TitlePropertyContext):
        pass

    # Exit a parse tree produced by draft04Parser#titleProperty.
    def exitTitleProperty(self, ctx:draft04Parser.TitlePropertyContext):
        pass


    # Enter a parse tree produced by draft04Parser#idProperty.
    def enterIdProperty(self, ctx:draft04Parser.IdPropertyContext):
        pass

    # Exit a parse tree produced by draft04Parser#idProperty.
    def exitIdProperty(self, ctx:draft04Parser.IdPropertyContext):
        pass


    # Enter a parse tree produced by draft04Parser#dollarIdProperty.
    def enterDollarIdProperty(self, ctx:draft04Parser.DollarIdPropertyContext):
        pass

    # Exit a parse tree produced by draft04Parser#dollarIdProperty.
    def exitDollarIdProperty(self, ctx:draft04Parser.DollarIdPropertyContext):
        pass


    # Enter a parse tree produced by draft04Parser#dollarSchemaProperty.
    def enterDollarSchemaProperty(self, ctx:draft04Parser.DollarSchemaPropertyContext):
        pass

    # Exit a parse tree produced by draft04Parser#dollarSchemaProperty.
    def exitDollarSchemaProperty(self, ctx:draft04Parser.DollarSchemaPropertyContext):
        pass


    # Enter a parse tree produced by draft04Parser#restriction.
    def enterRestriction(self, ctx:draft04Parser.RestrictionContext):
        pass

    # Exit a parse tree produced by draft04Parser#restriction.
    def exitRestriction(self, ctx:draft04Parser.RestrictionContext):
        pass


    # Enter a parse tree produced by draft04Parser#additionalItemsProperty.
    def enterAdditionalItemsProperty(self, ctx:draft04Parser.AdditionalItemsPropertyContext):
        pass

    # Exit a parse tree produced by draft04Parser#additionalItemsProperty.
    def exitAdditionalItemsProperty(self, ctx:draft04Parser.AdditionalItemsPropertyContext):
        pass


    # Enter a parse tree produced by draft04Parser#additionalPropertiesProperty.
    def enterAdditionalPropertiesProperty(self, ctx:draft04Parser.AdditionalPropertiesPropertyContext):
        pass

    # Exit a parse tree produced by draft04Parser#additionalPropertiesProperty.
    def exitAdditionalPropertiesProperty(self, ctx:draft04Parser.AdditionalPropertiesPropertyContext):
        pass


    # Enter a parse tree produced by draft04Parser#allOfProperty.
    def enterAllOfProperty(self, ctx:draft04Parser.AllOfPropertyContext):
        pass

    # Exit a parse tree produced by draft04Parser#allOfProperty.
    def exitAllOfProperty(self, ctx:draft04Parser.AllOfPropertyContext):
        pass


    # Enter a parse tree produced by draft04Parser#anyOfProperty.
    def enterAnyOfProperty(self, ctx:draft04Parser.AnyOfPropertyContext):
        pass

    # Exit a parse tree produced by draft04Parser#anyOfProperty.
    def exitAnyOfProperty(self, ctx:draft04Parser.AnyOfPropertyContext):
        pass


    # Enter a parse tree produced by draft04Parser#enumProperty.
    def enterEnumProperty(self, ctx:draft04Parser.EnumPropertyContext):
        pass

    # Exit a parse tree produced by draft04Parser#enumProperty.
    def exitEnumProperty(self, ctx:draft04Parser.EnumPropertyContext):
        pass


    # Enter a parse tree produced by draft04Parser#itemsProperty.
    def enterItemsProperty(self, ctx:draft04Parser.ItemsPropertyContext):
        pass

    # Exit a parse tree produced by draft04Parser#itemsProperty.
    def exitItemsProperty(self, ctx:draft04Parser.ItemsPropertyContext):
        pass


    # Enter a parse tree produced by draft04Parser#minItemsProperty.
    def enterMinItemsProperty(self, ctx:draft04Parser.MinItemsPropertyContext):
        pass

    # Exit a parse tree produced by draft04Parser#minItemsProperty.
    def exitMinItemsProperty(self, ctx:draft04Parser.MinItemsPropertyContext):
        pass


    # Enter a parse tree produced by draft04Parser#notProperty.
    def enterNotProperty(self, ctx:draft04Parser.NotPropertyContext):
        pass

    # Exit a parse tree produced by draft04Parser#notProperty.
    def exitNotProperty(self, ctx:draft04Parser.NotPropertyContext):
        pass


    # Enter a parse tree produced by draft04Parser#oneOfProperty.
    def enterOneOfProperty(self, ctx:draft04Parser.OneOfPropertyContext):
        pass

    # Exit a parse tree produced by draft04Parser#oneOfProperty.
    def exitOneOfProperty(self, ctx:draft04Parser.OneOfPropertyContext):
        pass


    # Enter a parse tree produced by draft04Parser#propertiesProperty.
    def enterPropertiesProperty(self, ctx:draft04Parser.PropertiesPropertyContext):
        pass

    # Exit a parse tree produced by draft04Parser#propertiesProperty.
    def exitPropertiesProperty(self, ctx:draft04Parser.PropertiesPropertyContext):
        pass


    # Enter a parse tree produced by draft04Parser#requiredProperty.
    def enterRequiredProperty(self, ctx:draft04Parser.RequiredPropertyContext):
        pass

    # Exit a parse tree produced by draft04Parser#requiredProperty.
    def exitRequiredProperty(self, ctx:draft04Parser.RequiredPropertyContext):
        pass


    # Enter a parse tree produced by draft04Parser#typeProperty.
    def enterTypeProperty(self, ctx:draft04Parser.TypePropertyContext):
        pass

    # Exit a parse tree produced by draft04Parser#typeProperty.
    def exitTypeProperty(self, ctx:draft04Parser.TypePropertyContext):
        pass


    # Enter a parse tree produced by draft04Parser#multipleOfProperty.
    def enterMultipleOfProperty(self, ctx:draft04Parser.MultipleOfPropertyContext):
        pass

    # Exit a parse tree produced by draft04Parser#multipleOfProperty.
    def exitMultipleOfProperty(self, ctx:draft04Parser.MultipleOfPropertyContext):
        pass


    # Enter a parse tree produced by draft04Parser#maximumProperty.
    def enterMaximumProperty(self, ctx:draft04Parser.MaximumPropertyContext):
        pass

    # Exit a parse tree produced by draft04Parser#maximumProperty.
    def exitMaximumProperty(self, ctx:draft04Parser.MaximumPropertyContext):
        pass


    # Enter a parse tree produced by draft04Parser#exclusiveMaximumProperty.
    def enterExclusiveMaximumProperty(self, ctx:draft04Parser.ExclusiveMaximumPropertyContext):
        pass

    # Exit a parse tree produced by draft04Parser#exclusiveMaximumProperty.
    def exitExclusiveMaximumProperty(self, ctx:draft04Parser.ExclusiveMaximumPropertyContext):
        pass


    # Enter a parse tree produced by draft04Parser#minimumProperty.
    def enterMinimumProperty(self, ctx:draft04Parser.MinimumPropertyContext):
        pass

    # Exit a parse tree produced by draft04Parser#minimumProperty.
    def exitMinimumProperty(self, ctx:draft04Parser.MinimumPropertyContext):
        pass


    # Enter a parse tree produced by draft04Parser#exclusiveMinimumProperty.
    def enterExclusiveMinimumProperty(self, ctx:draft04Parser.ExclusiveMinimumPropertyContext):
        pass

    # Exit a parse tree produced by draft04Parser#exclusiveMinimumProperty.
    def exitExclusiveMinimumProperty(self, ctx:draft04Parser.ExclusiveMinimumPropertyContext):
        pass


    # Enter a parse tree produced by draft04Parser#maxLengthProperty.
    def enterMaxLengthProperty(self, ctx:draft04Parser.MaxLengthPropertyContext):
        pass

    # Exit a parse tree produced by draft04Parser#maxLengthProperty.
    def exitMaxLengthProperty(self, ctx:draft04Parser.MaxLengthPropertyContext):
        pass


    # Enter a parse tree produced by draft04Parser#minLengthProperty.
    def enterMinLengthProperty(self, ctx:draft04Parser.MinLengthPropertyContext):
        pass

    # Exit a parse tree produced by draft04Parser#minLengthProperty.
    def exitMinLengthProperty(self, ctx:draft04Parser.MinLengthPropertyContext):
        pass


    # Enter a parse tree produced by draft04Parser#patternProperty.
    def enterPatternProperty(self, ctx:draft04Parser.PatternPropertyContext):
        pass

    # Exit a parse tree produced by draft04Parser#patternProperty.
    def exitPatternProperty(self, ctx:draft04Parser.PatternPropertyContext):
        pass


    # Enter a parse tree produced by draft04Parser#maxItemsProperty.
    def enterMaxItemsProperty(self, ctx:draft04Parser.MaxItemsPropertyContext):
        pass

    # Exit a parse tree produced by draft04Parser#maxItemsProperty.
    def exitMaxItemsProperty(self, ctx:draft04Parser.MaxItemsPropertyContext):
        pass


    # Enter a parse tree produced by draft04Parser#uniqueItemsProperty.
    def enterUniqueItemsProperty(self, ctx:draft04Parser.UniqueItemsPropertyContext):
        pass

    # Exit a parse tree produced by draft04Parser#uniqueItemsProperty.
    def exitUniqueItemsProperty(self, ctx:draft04Parser.UniqueItemsPropertyContext):
        pass


    # Enter a parse tree produced by draft04Parser#maxPropertiesProperty.
    def enterMaxPropertiesProperty(self, ctx:draft04Parser.MaxPropertiesPropertyContext):
        pass

    # Exit a parse tree produced by draft04Parser#maxPropertiesProperty.
    def exitMaxPropertiesProperty(self, ctx:draft04Parser.MaxPropertiesPropertyContext):
        pass


    # Enter a parse tree produced by draft04Parser#minPropertiesProperty.
    def enterMinPropertiesProperty(self, ctx:draft04Parser.MinPropertiesPropertyContext):
        pass

    # Exit a parse tree produced by draft04Parser#minPropertiesProperty.
    def exitMinPropertiesProperty(self, ctx:draft04Parser.MinPropertiesPropertyContext):
        pass


    # Enter a parse tree produced by draft04Parser#patternPropertiesProperty.
    def enterPatternPropertiesProperty(self, ctx:draft04Parser.PatternPropertiesPropertyContext):
        pass

    # Exit a parse tree produced by draft04Parser#patternPropertiesProperty.
    def exitPatternPropertiesProperty(self, ctx:draft04Parser.PatternPropertiesPropertyContext):
        pass


    # Enter a parse tree produced by draft04Parser#dependenciesProperty.
    def enterDependenciesProperty(self, ctx:draft04Parser.DependenciesPropertyContext):
        pass

    # Exit a parse tree produced by draft04Parser#dependenciesProperty.
    def exitDependenciesProperty(self, ctx:draft04Parser.DependenciesPropertyContext):
        pass


    # Enter a parse tree produced by draft04Parser#formatProperty.
    def enterFormatProperty(self, ctx:draft04Parser.FormatPropertyContext):
        pass

    # Exit a parse tree produced by draft04Parser#formatProperty.
    def exitFormatProperty(self, ctx:draft04Parser.FormatPropertyContext):
        pass


    # Enter a parse tree produced by draft04Parser#extension.
    def enterExtension(self, ctx:draft04Parser.ExtensionContext):
        pass

    # Exit a parse tree produced by draft04Parser#extension.
    def exitExtension(self, ctx:draft04Parser.ExtensionContext):
        pass


    # Enter a parse tree produced by draft04Parser#extendsProperty.
    def enterExtendsProperty(self, ctx:draft04Parser.ExtendsPropertyContext):
        pass

    # Exit a parse tree produced by draft04Parser#extendsProperty.
    def exitExtendsProperty(self, ctx:draft04Parser.ExtendsPropertyContext):
        pass


    # Enter a parse tree produced by draft04Parser#implementsProperty.
    def enterImplementsProperty(self, ctx:draft04Parser.ImplementsPropertyContext):
        pass

    # Exit a parse tree produced by draft04Parser#implementsProperty.
    def exitImplementsProperty(self, ctx:draft04Parser.ImplementsPropertyContext):
        pass


    # Enter a parse tree produced by draft04Parser#name.
    def enterName(self, ctx:draft04Parser.NameContext):
        pass

    # Exit a parse tree produced by draft04Parser#name.
    def exitName(self, ctx:draft04Parser.NameContext):
        pass


    # Enter a parse tree produced by draft04Parser#propertyName.
    def enterPropertyName(self, ctx:draft04Parser.PropertyNameContext):
        pass

    # Exit a parse tree produced by draft04Parser#propertyName.
    def exitPropertyName(self, ctx:draft04Parser.PropertyNameContext):
        pass


    # Enter a parse tree produced by draft04Parser#typeName.
    def enterTypeName(self, ctx:draft04Parser.TypeNameContext):
        pass

    # Exit a parse tree produced by draft04Parser#typeName.
    def exitTypeName(self, ctx:draft04Parser.TypeNameContext):
        pass


    # Enter a parse tree produced by draft04Parser#extensionKeyword.
    def enterExtensionKeyword(self, ctx:draft04Parser.ExtensionKeywordContext):
        pass

    # Exit a parse tree produced by draft04Parser#extensionKeyword.
    def exitExtensionKeyword(self, ctx:draft04Parser.ExtensionKeywordContext):
        pass



del draft04Parser