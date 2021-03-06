# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/01_data.ipynb (unless otherwise specified).

__all__ = ['HF_BaseInput', 'HF_Tokenizer', 'HF_BatchTransform', 'HF_TextBlock', 'HF_TokenTensorCategory',
           'HF_TokenCategorize', 'HF_TokenCategoryBlock']

# Cell
import ast
from functools import reduce

from .utils import *

import torch
from transformers import *
from fastai2.text.all import *

# Cell
class HF_BaseInput(list): pass

# Cell
class HF_Tokenizer():
    """huggingface friendly tokenization function."""
    def __init__(self, hf_arch, hf_tokenizer, mode='str', list_split_func=str.split, **kwargs):
        store_attr(self, 'hf_arch, hf_tokenizer, mode, list_split_func')

    def __call__(self, items):
        for txt in items: yield self._tokenize(txt)

    def _tokenize(self, txt):
        if (self.mode == 'str'):
            return self.hf_tokenizer.tokenize(txt)

        if (self.mode == 'list'):
            try: tokens = ast.literal_eval(txt)
            except:
                tokens = self.list_split_func(txt)
            finally:
                return [sub_toks for entity in tokens for sub_toks in self.hf_tokenizer.tokenize(entity)]

# Cell
@typedispatch
def build_hf_input(task, tokenizer, a_tok_ids, b_tok_ids=None, targets=None,
                   max_length=512, pad_to_max_length=True, truncation_strategy='longest_first'):

    res = tokenizer.prepare_for_model(a_tok_ids, b_tok_ids,
                                       max_length=max_length, pad_to_max_length=pad_to_max_length,
                                       truncation_strategy=truncation_strategy, return_tensors='pt')

    input_ids = res['input_ids'][0]
    token_type_ids = res['token_type_ids'][0] if ('token_type_ids' in res) else torch.tensor([-9999])
    attention_mask = res['attention_mask'][0] if ('attention_mask' in res) else torch.tensor([-9999])

    return HF_BaseInput([input_ids, token_type_ids, attention_mask]), targets


# Cell
class HF_BatchTransform(Transform):
    """Handles everything you need to assemble a mini-batch of inputs and targets"""
    def __init__(self, hf_arch, hf_tokenizer, max_seq_len=512, truncation_strategy='longest_first', task=None):

        self.hf_arch = hf_arch
        self.hf_tokenizer = hf_tokenizer
        store_attr(self, 'max_seq_len, truncation_strategy, task')

    def encodes(self, samples):

        encoded_samples = []
        for idx, sample in enumerate(samples):

            if (isinstance(sample[0], tuple)):
                a_tok_ids = sample[0][0].tolist()
                b_tok_ids = sample[0][1].tolist()
            else:
                a_tok_ids = sample[0].tolist()
                b_tok_ids = None

            hf_base_input, targets = build_hf_input(self.task, self.hf_tokenizer,
                                                    a_tok_ids, b_tok_ids, sample[1:],
                                                    self.max_seq_len, True, self.truncation_strategy)

            encoded_samples.append((hf_base_input, *targets))

        return encoded_samples


# Cell
class HF_TextBlock(TransformBlock):

    @delegates(Numericalize.__init__)
    def __init__(self, tok_tfms, hf_arch, hf_tokenizer, hf_batch_tfm=None, vocab=None, task=None,
                 max_seq_len=512, **kwargs):

        if hf_batch_tfm is None:
            hf_batch_tfm = HF_BatchTransform(hf_arch, hf_tokenizer, max_seq_len=max_seq_len,
                                             truncation_strategy='longest_first', task=task)

        return super().__init__(type_tfms=[*tok_tfms, Numericalize(vocab, **kwargs)],
                                dl_type=SortedDL,
                                dls_kwargs={ 'before_batch': hf_batch_tfm })

    @classmethod
    @delegates(Tokenizer.from_df, keep=True)
    def from_df(cls, text_cols_lists, hf_arch, hf_tokenizer, hf_batch_tfm=None, vocab=None, task=None,
                tok_func_mode='str', res_col_names=None, max_seq_len=512, **kwargs):
        """Creates a HF_TextBlock via a pandas DataFrame"""

        # grab hf tokenizer class to do the actual tokenization (via tok_func) and its vocab
        tokenizer_cls = partial(HF_Tokenizer, hf_arch=hf_arch, hf_tokenizer=hf_tokenizer, mode=tok_func_mode)
        if (vocab is None): vocab = list(hf_tokenizer.get_vocab())

        # build the column name(s) returned after tokenization
        if (res_col_names is None): res_col_names = [ f'text{i}' for i in range(len(text_cols_lists)) ]

        tok_tfms = [ Tokenizer.from_df(text_cols,
                                       res_col_name=res_col_name,
                                       tok_func=tokenizer_cls,
                                       rules=[], **kwargs)
                    for text_cols, res_col_name in zip(text_cols_lists, res_col_names) ]

        return cls(tok_tfms, hf_arch=hf_arch, hf_tokenizer=hf_tokenizer, hf_batch_tfm=hf_batch_tfm,
                   vocab=vocab, task=task, max_seq_len=max_seq_len)

# Cell
@typedispatch
def show_batch(x:HF_BaseInput, y, samples, hf_tokenizer, skip_special_tokens=True, ctxs=None, max_n=6, **kwargs):
    if ctxs is None: ctxs = get_empty_df(min(len(samples), max_n))

    samples = L((TitledStr(hf_tokenizer.decode(inp, skip_special_tokens=skip_special_tokens).replace(hf_tokenizer.pad_token, '')),*s[1:])
                for inp, s in zip(x[0], samples))

    ctxs = show_batch[object](x, y, samples, max_n=max_n, ctxs=ctxs, **kwargs)

    display_df(pd.DataFrame(ctxs))
    return ctxs

# Cell
@typedispatch
def build_hf_input(task:ForQuestionAnsweringTask, tokenizer,
                   a_tok_ids, b_tok_ids=None, targets=None,
                   max_length=512, pad_to_max_length=True, truncation_strategy=None):

    if (truncation_strategy is None):
        truncation_strategy = "only_second" if tokenizer.padding_side == "right" else "only_first"

    res = tokenizer.prepare_for_model(a_tok_ids if tokenizer.padding_side == "right" else b_tok_ids,
                                      b_tok_ids if tokenizer.padding_side == "right" else a_tok_ids,
                                      max_length=max_length,
                                      pad_to_max_length=pad_to_max_length,
                                      truncation_strategy=truncation_strategy,
                                      return_tensors='pt')

    input_ids = res['input_ids'][0]
    token_type_ids = res['token_type_ids'][0] if ('token_type_ids' in res) else torch.tensor([-9999])
    attention_mask = res['attention_mask'][0] if ('attention_mask' in res) else torch.tensor([-9999])

    return HF_BaseInput([input_ids, token_type_ids, attention_mask]), targets


# Cell
class HF_TokenTensorCategory(TensorBase): pass

# Cell
class HF_TokenCategorize(Transform):
    "Reversible transform of a list of category string to `vocab` id"

    def __init__(self, vocab=None, ignore_token=None, ignore_token_id=None):
        self.vocab = None if vocab is None else CategoryMap(vocab)
        self.ignore_token = '[xIGNx]' if ignore_token is None else ignore_token
        self.ignore_token_id = CrossEntropyLossFlat().ignore_index if ignore_token_id is None else ignore_token_id

        self.loss_func, self.order = CrossEntropyLossFlat(ignore_index=self.ignore_token_id), 1

    def setups(self, dsets):
        if self.vocab is None and dsets is not None: self.vocab = CategoryMap(dsets)
        self.c = len(self.vocab)

    def encodes(self, labels):
        ids = [[self.vocab.o2i[lbl]] + [self.ignore_token_id]*(n_subtoks-1) for lbl, n_subtoks in labels]
        return HF_TokenTensorCategory(reduce(operator.concat, ids))

    def decodes(self, encoded_labels):
        return Category([(self.vocab[lbl_id]) for lbl_id in encoded_labels if lbl_id != self.ignore_token_id ])

# Cell
def HF_TokenCategoryBlock(vocab=None, ignore_token=None, ignore_token_id=None):
    "`TransformBlock` for single-label categorical targets"

    return TransformBlock(type_tfms=HF_TokenCategorize(vocab=vocab,
                                                       ignore_token=ignore_token,
                                                       ignore_token_id=ignore_token_id))

# Cell
@typedispatch
def build_hf_input(task:ForTokenClassificationTask, tokenizer, a_tok_ids, b_tok_ids=None, targets=None,
                   max_length=512, pad_to_max_length=True, truncation_strategy='longest_first'):

    res = tokenizer.prepare_for_model(a_tok_ids, b_tok_ids,
                                      max_length=max_length,
                                      pad_to_max_length=pad_to_max_length,
                                      truncation_strategy=truncation_strategy,
                                      return_special_tokens_mask=True,
                                      return_tensors='pt')

    input_ids = res['input_ids'][0]
    token_type_ids = res['token_type_ids'][0] if ('token_type_ids' in res) else torch.tensor([-9999])
    attention_mask = res['attention_mask'][0] if ('attention_mask' in res) else torch.tensor([-9999])

    # we assume that first target = the categories we want to predict for each token
    if (len(targets) > 0):
        target_cls = type(targets[0])
        idx_first_input_id = res['special_tokens_mask'].index(0)
        targ_ids = target_cls([ el*-100 if (el == 1) else targets[0][idx-idx_first_input_id].item()
                    for idx, el in enumerate(res['special_tokens_mask']) ])

        # just in case there are other targets, we modify the first with the padded targ_ids
        updated_targets = list(targets)
        updated_targets[0] = targ_ids
    else:
        updated_targets= list(targets)

    return HF_BaseInput([input_ids, token_type_ids, attention_mask]), tuple(updated_targets)