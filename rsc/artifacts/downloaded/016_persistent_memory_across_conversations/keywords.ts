// single source of truth for all Draft 4 keyword classifications
// and canonical ordering. both the extension and the server import from here.
// when the ANTLR4 grammar is integrated, this file will be generated from it.

export type KeywordClass = 'restriction' | 'structural' | 'annotation' | 'unknown';

export const RESTRICTION_KEYWORDS: ReadonlySet<string> = new Set([
    // type and enumeration
    'type', 'enum',
    // logical combinators
    'allOf', 'anyOf', 'oneOf', 'not',
    // object constraints
    'properties', 'additionalProperties', 'patternProperties', 'required', 'dependencies',
    // array constraints
    'items', 'additionalItems', 'uniqueItems', 'minItems', 'maxItems',
    // object size constraints
    'minProperties', 'maxProperties',
    // numeric constraints
    'minimum', 'maximum', 'exclusiveMinimum', 'exclusiveMaximum', 'multipleOf',
    // string constraints
    'minLength', 'maxLength', 'pattern', 'format'
]);

export const STRUCTURAL_KEYWORDS: ReadonlySet<string> = new Set([
    'id', 'definitions', '$ref'
]);

export const ANNOTATION_KEYWORDS: ReadonlySet<string> = new Set([
    '$schema', 'title', 'description', 'default'
]);

export const DRAFT4_KEYWORDS: ReadonlySet<string> = new Set([
    ...RESTRICTION_KEYWORDS,
    ...STRUCTURAL_KEYWORDS,
    ...ANNOTATION_KEYWORDS
]);

// default canonical evaluation order for restrictions.
// ordered from most-general/cheapest to most-specific/costly.
// user-configurable per domain via schemaJson.restrictionOrder setting.
export const DEFAULT_RESTRICTION_ORDER: readonly string[] = [
    'type', 'enum',
    'allOf', 'anyOf', 'oneOf', 'not',
    'properties', 'additionalProperties', 'patternProperties', 'required', 'dependencies',
    'items', 'additionalItems', 'uniqueItems', 'minItems', 'maxItems',
    'minProperties', 'maxProperties',
    'minimum', 'maximum', 'exclusiveMinimum', 'exclusiveMaximum', 'multipleOf',
    'minLength', 'maxLength', 'pattern', 'format'
];

export const DEFAULT_STRUCTURAL_ORDER: readonly string[] = [
    'id', 'definitions', '$ref'
];

export const DEFAULT_ANNOTATION_ORDER: readonly string[] = [
    '$schema', 'title', 'description', 'default'
];

export function classify(keyword: string): KeywordClass {
    if (RESTRICTION_KEYWORDS.has(keyword)) { return 'restriction'; }
    if (STRUCTURAL_KEYWORDS.has(keyword))  { return 'structural'; }
    if (ANNOTATION_KEYWORDS.has(keyword))  { return 'annotation'; }
    return 'unknown';
}

export function isDraft4(keyword: string): boolean {
    return DRAFT4_KEYWORDS.has(keyword);
}

export function canonicalPosition(keyword: string, order: readonly string[]): number {
    return order.indexOf(keyword);
}
