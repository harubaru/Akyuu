import json
import re
from transformers import AutoTokenizer
tokenizer = AutoTokenizer.from_pretrained('gpt2')

TRIM_DIR_TOP=0
TRIM_DIR_BOTTOM=1
TRIM_DIR_NONE=2

TRIM_TYPE_NEWLINE=3
TRIM_TYPE_SENTENCE=4
TRIM_TYPE_TOKEN=5

INSERTION_TYPE_NEWLINE=6
INSERTION_TYPE_SENTENCE=7
INSERTION_TYPE_TOKEN=8

def split_into_sentences(str):
    # preserve line breaks too
    return re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s', str)

def trim_newlines(tokens, trim_dir, limit):
    if (trim_dir == TRIM_DIR_NONE) or (len(tokens) <= limit):
        return tokens
    
    lines = tokenizer.decode(tokens).split('\n')
    start, end, step = 0, 0, 0
    if trim_dir == TRIM_DIR_TOP:
        start = len(lines) - 1
        end = -1
        step = -1
    elif trim_dir == TRIM_DIR_BOTTOM:
        start = 0
        end = len(lines)
        step = 1
    
    acc_tokens = []

    for idx in range(start, end, step):
        line = lines[idx]
        if trim_dir == TRIM_DIR_TOP:
            line = '\n' + line
        elif trim_dir == TRIM_DIR_BOTTOM:
            line = line + '\n'
        new_tokens = tokenizer.encode(line)
        if len(new_tokens) + len(acc_tokens) > limit:
            return acc_tokens
        else:
            if trim_dir == TRIM_DIR_TOP:
                acc_tokens = new_tokens + acc_tokens
            elif trim_dir == TRIM_DIR_BOTTOM:
                acc_tokens = acc_tokens + new_tokens
    return acc_tokens

def trim_sentences(tokens, trim_dir, limit):
    if (trim_dir == TRIM_DIR_NONE) or (len(tokens) <= limit):
        return tokens
    
    text = tokenizer.decode(tokens)
    sentences = split_into_sentences(text)

    start, end, step = 0, 0, 0
    text_begin, text_end = 0, 0
    sentence_idx, last_sentence_idx = 0, 0

    if trim_dir == TRIM_DIR_TOP:
        start = len(sentences) - 1
        end = -1
        step = -1
        text_begin = 0
        text_end = len(text)
    elif trim_dir == TRIM_DIR_BOTTOM:
        start = 0
        end = len(sentences)
        step = 1
        text_begin = 0
        text_end = len(text)
    else:
        return tokens
    
    for idx in range(start, end, step):
        sentence = sentences[idx]
        if trim_dir == TRIM_DIR_TOP:
            sentence_idx = text.rindex(sentence) + text_begin
            if (sentence_idx > 0) and (sentence_idx < len(text)) and (text[sentence_idx] == ' '):
                sentence_idx -= 1
            to_tokenize = text[sentence_idx:]
            token_count = len(tokenizer.encode(to_tokenize))
            if token_count >= limit:
                to_encode = text[text_end:]
                return tokenizer.encode(to_encode)
            text_end = sentence_idx - 1
        elif trim_dir == TRIM_DIR_BOTTOM:
            sentence_idx = text.index(sentence) + text_begin
            sentence_end = sentence_idx + len(sentence)
            if (sentence_end < text_end) and (text[sentence_end:sentence_end+1] == '\n'):
                sentence_end += 1
            to_tokenize = text[0:sentence_end]
            token_count = len(tokenizer.encode(to_tokenize))
            if token_count >= limit:
                to_encode = text[0:last_sentence_idx]
                return tokenizer.encode(to_encode)
            last_sentence_idx = sentence_end
            text_begin += len(sentence)
    return tokens

def trim_tokens(tokens, trim_dir, limit):
    if (trim_dir == TRIM_DIR_NONE) or (len(tokens) <= limit):
        return tokens
    if trim_dir == TRIM_DIR_TOP:
        return tokens[len(tokens)-limit:]
    elif trim_dir == TRIM_DIR_BOTTOM:
        return tokens[:limit]

class ContextEntry:
    def __init__(self, keys=[''], text='', prefix='', suffix='\n', token_budget=2048, reserved_tokens=0, insertion_order=100, insertion_position=-1, trim_direction=TRIM_DIR_BOTTOM, trim_type=TRIM_TYPE_SENTENCE, insertion_type=INSERTION_TYPE_SENTENCE, forced_activation=False, cascading_activation=False):
        self.keys = keys # key used to activate this context entry 
        self.text = prefix + text + suffix # text associated with this context entry
        self.token_budget = token_budget # max amount of tokens that this context entry can use
        self.reserved_tokens = reserved_tokens # number of tokens that are reserved for this context entry
        self.insertion_order = insertion_order # order in which this context entry is inserted
        self.insertion_position = insertion_position # position in the text where this context entry is inserted, 0 is the beginning, -1 is the end
        self.trim_direction = trim_direction # direction in which to trim the text
        self.trim_type = trim_type # type of trimming to perform
        self.insertion_type = insertion_type # determines what units are used to insert the text
        self.forced_activation = forced_activation # if True, this context entry is activated even if it is not activated
        self.cascading_activation = cascading_activation # when activated, this context entry will search for other entries and activate them if found
        if self.text == '':
            suffix = ''
            prefix = ''
    
    # max_length is in tokens
    def trim(self, max_length, token_budget):
        target = 0
        tokens = tokenizer.encode(self.text)
        num_tokens = len(tokens)
        projected = max_length - num_tokens
        if projected > token_budget:
            target = token_budget
        elif projected >= 0:
            target = num_tokens
        else:
            target = max_length
        if self.trim_type == TRIM_TYPE_NEWLINE:
            tokens = trim_newlines(tokens, self.trim_direction, target)
        elif self.trim_type == TRIM_TYPE_SENTENCE or len(tokens) > target:
            tokens = trim_sentences(tokens, self.trim_direction, target)
        elif self.trim_type == TRIM_TYPE_TOKEN or len(tokens) > target:
            tokens = trim_tokens(tokens, self.trim_direction, target)
        return tokens
        
    def get_text(self, max_length, token_budget):
        return tokenizer.decode(self.trim(max_length, token_budget))

class ContextManager:
    def __init__(self, token_budget=1024):
        self.token_budget = token_budget
        self.entries = []
    
    def add_entry(self, entry):
        self.entries.append(entry)
    
    def del_entry(self, entry):
        self.entries.remove(entry)
    
    def add_entries(self, entries):
        self.entries.extend(entries)
    
    def del_entries(self, entries):
        for entry in entries:
            self.del_entry(entry)
    
    # return true if key is found in an entry's text. checks if entry_b's keys are found in entry_a's text
    def key_lookup(self, entry_a, entry_b):
        for i in entry_b.keys:
            if i == '':
                continue
            if i.lower() in entry_a.text.lower():
                return True
        return False
    
    # function that searches for other entries that are activated
    def cascade_lookup(self, entry):
        cascaded_entries = []
        for i in self.entries:
            if self.key_lookup(entry, i):
                cascaded_entries.append(i)
        return cascaded_entries

    # handles cases where elements are added to the end of a list using list.insert
    def ordinal_pos(self, position, length):
        if position < 0:
            return length + 1 + position
        return position
    
    def context(self, budget=1024):
        # sort self.entries by insertion_order
        self.entries.sort(key=lambda x: x.insertion_order, reverse=True)
        activated_entries = []

        # Get entries activated by default
        for i in self.entries:
            if i.forced_activation:
                if i.cascading_activation:
                    for j in self.cascade_lookup(i):
                        activated_entries.append(j)
                    activated_entries.append(i)
                else:
                    activated_entries.append(i)
            if i.insertion_position > 0 or i.insertion_position < 0:
                if i.reserved_tokens == 0:
                    i.reserved_tokens = len(tokenizer.encode(i.text))
        
        activated_entries = list(set(activated_entries))
        # sort activated_entries by insertion_order
        activated_entries.sort(key=lambda x: x.insertion_order, reverse=True)

        newctx = []
        for i in activated_entries:
            reserved = 0
            if i.reserved_tokens > 0:
                len_tokens = len(tokenizer.encode(i.text))
                if len_tokens < i.reserved_tokens:
                    budget -= len_tokens
                else:
                    budget -= i.reserved_tokens
                if len_tokens > i.reserved_tokens:
                    reserved = i.reserved_tokens
                else:
                    reserved = len_tokens
            
            text = i.get_text(budget + reserved, self.token_budget)
            ctxtext = text.splitlines(keepends=False)
            trimmed_tokenized = tokenizer.encode(text)
            budget -= len(trimmed_tokenized) - reserved
            ctxinsertion = i.insertion_position

            before = []
            after = []

            if i.insertion_position < 0:
                ctxinsertion += 1
                if len(newctx) + ctxinsertion >= 0:
                    before = newctx[0:len(newctx)+ctxinsertion]
                    after = newctx[len(newctx)+ctxinsertion:]
                else:
                    before = []
                    after = newctx[0:]
            else:
                before = newctx[0:ctxinsertion]
                after = newctx[ctxinsertion:]

            newctx = []

            for bIdx in range(len(before)):
                newctx.append(before[bIdx])
            for cIdx in range(len(ctxtext)):
                newctx.append(ctxtext[cIdx])
            for aIdx in range(len(after)):
                newctx.append(after[aIdx])
        return '\n'.join(newctx).rstrip().lstrip()

class Lorebook:
    def __init__(self, filepath) -> None:
        with open(filepath, encoding='utf-8') as fp:
            self.lorebook = json.load(fp)
    
    def get_entries(self):
        entries = []
        for entry in self.lorebook['entries']:
            trimdir = entry['contextConfig']['trimDirection']
            insertiontype = entry['contextConfig']['insertionType']
            trimtype = entry['contextConfig']['maximumTrimType']

            if trimdir ==  'trimBottom':
                trimdir = TRIM_DIR_BOTTOM
            elif trimdir == 'trimTop':
                trimdir = TRIM_DIR_TOP
            
            if insertiontype == 'newline':
                insertiontype = INSERTION_TYPE_NEWLINE
            elif insertiontype == 'sentence':
                insertiontype = INSERTION_TYPE_SENTENCE
            elif insertiontype == 'token':
                insertiontype = INSERTION_TYPE_TOKEN

            if trimtype == 'sentence':
                trimtype = TRIM_TYPE_SENTENCE
            elif trimtype == 'token':
                trimtype = TRIM_TYPE_TOKEN
            elif trimtype == 'newline':
                trimtype = TRIM_TYPE_NEWLINE

            entries.append(
                ContextEntry(
                    keys=entry['keys'],
                    text=entry['text'],
                    prefix=entry['contextConfig']['prefix'],
                    suffix=entry['contextConfig']['suffix'],
                    token_budget=entry['contextConfig']['tokenBudget'],
                    reserved_tokens=entry['contextConfig']['reservedTokens'],
                    insertion_order=entry['contextConfig']['budgetPriority'],
                    insertion_position=entry['contextConfig']['insertionPosition'],
                    trim_direction=trimdir,
                    trim_type=trimtype,
                    insertion_type=insertiontype,
                    forced_activation=entry['forceActivation'],
                    cascading_activation=entry['nonStoryActivatable']
                )
            )
        return entries
