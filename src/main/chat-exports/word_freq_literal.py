#!/usr/bin/env python
"""
Literal word frequency extraction from conversations.json.
Run locally: python word_freq_literal.py conversations.json > literal_freq.json

Produces JSON with three arrays: human, assistant, both.
Each array: [{"word": "...", "count": N}, ...] sorted by count descending, top 120.
"""
import sys
import json
import re
from collections import Counter

STOPS = {
    'the','and','with','that','for','this','from','they','their','than','rather',
    'through','both','across','between','one','into','about','all','are','not',
    'then','which','but','what','how','them','also','each','several','more',
    'its','only','where','these','any','being','via','would','two','three','four',
    'his','her','was','were','had','has','have','been','will','can','may','could',
    'should','did','does','within','without','before','after','over','under','very',
    'when','while','here','there','thus','such','some','most','other','same',
    'just','like','even','well','use','used','using','you','your','our','we',
    'it','at','an','or','so','do','be','by','up','out','on','in','of','to',
    'a','i','is','as','am','get','got','let','see','now','too','yes','no',
    'ok','yeah','sure','think','know','want','need','make','made','take','takes',
    'give','gives','look','looks','come','goes','say','says','said','tell','told',
    'ask','asked','try','tried','work','works','something','anything','everything',
    'nothing','someone','anyone','everyone','actually','really','quite','already',
    'always','never','often','still','might','much','many','few','lot','bit',
    'way','thing','things','time','times',
    # meta / UI
    'redacted','claude','message','conversation','chat','response','user','assistant',
}

def words_from(text):
    return re.findall(r"[a-z][a-z''\-]{2,}", text.lower())

def filtered(words):
    return [w for w in words if w not in STOPS and len(w) > 2]

def top_n(counter, n=120):
    return [{'word': w, 'count': c} for w, c in counter.most_common(n)]

def tables(human_words, assistant_words):
    """The three sub-tables from raw word lists — shared with present_corpus.py,
    whose word lists come from projected markdown rather than conversations.json."""
    hf = Counter(human_words)
    af = Counter(assistant_words)
    return {
        'human':     top_n(hf),
        'assistant': top_n(af),
        'both':      top_n(hf + af),
    }


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else 'conversations.json'
    data = json.load(open(path))

    human_words, assistant_words = [], []

    for conv in data:
        for msg in conv['chat_messages']:
            text = ' '.join(
                b['text'] for b in msg['content']
                if b.get('type') == 'text' and b.get('text')
            )
            ws = filtered(words_from(text))
            if msg['sender'] == 'human':
                human_words += ws
            else:
                assistant_words += ws

    print(json.dumps(tables(human_words, assistant_words), indent=2))


if __name__ == '__main__':
    main()
