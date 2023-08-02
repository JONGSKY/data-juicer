# Some code here has been modified from:
# https://huggingface.co/spaces/huggingface/text-data-filtering
# --------------------------------------------------------

from jsonargparse.typing import ClosedUnitInterval, List

from data_juicer.utils.model_utils import MODEL_ZOO, prepare_model

from ...utils.asset_utils import ASSET_DIR, load_words_asset
from ..base_op import OPERATORS, Filter
from ..common import SPECIAL_CHARACTERS, get_words_from_document


@OPERATORS.register_module('flagged_words_filter')
class FlaggedWordFilter(Filter):
    """Filter to keep samples with flagged-word ratio less than a specific max
    value."""

    def __init__(self,
                 lang: str = 'en',
                 tokenization: bool = False,
                 max_ratio: ClosedUnitInterval = 0.045,
                 flagged_words_dir: str = ASSET_DIR,
                 use_words_aug: bool = False,
                 words_aug_group_sizes: List = [2],
                 words_aug_join_char: str = '',
                 *args,
                 **kwargs):
        """
        Initialization method.

        :param lang: Consider flagged words in what language. If lang ==
            "all", we will adopt the one merged from all the available
            languages
        :param tokenization: Whether to use model to tokenize documents
        :param max_ratio: The max filter ratio in this op.
        :param flagged_words_dir: The directory storing the
            flagged_words file(s) whose name includes "flagged_words"
            and in json format
        :param use_words_aug: Whether to augment words, especially for
            Chinese and Vietnamese
        :param words_aug_group_sizes: The group size of words to augment
        :param words_aug_join_char: The join char between words to
            augment
        :param args: extra args
        :param kwargs: extra args
        """
        super().__init__(*args, **kwargs)
        self.lang = lang
        self.max_ratio = max_ratio
        self.use_words_aug = use_words_aug
        self.words_aug_group_sizes = words_aug_group_sizes
        self.words_aug_join_char = words_aug_join_char
        self.model_key = None

        self.FLAGGED_WORDS = load_words_asset(words_dir=flagged_words_dir,
                                              words_type='flagged_words')

        if 'all' not in self.FLAGGED_WORDS:
            self.FLAGGED_WORDS['all'] = [
                val for vals in self.FLAGGED_WORDS.values() for val in vals
            ]
        if tokenization:
            self.model_key = prepare_model(lang=lang,
                                           model_type='sentencepiece')

    def compute_stats(self, sample):
        # check if it's computed already
        if 'flagged_words_ratio' in sample['stats']:
            return sample

        tokenizer = MODEL_ZOO.get(self.model_key, None)
        words = get_words_from_document(
            sample[self.text_key],
            token_func=tokenizer.encode_as_pieces if tokenizer else None,
            strip_chars=SPECIAL_CHARACTERS,
            use_words_aug=self.use_words_aug,
            words_aug_group_sizes=self.words_aug_group_sizes,
            words_aug_join_char=self.words_aug_join_char)

        flagged_words_ratio = (len(
            [word
             for word in words if word in self.FLAGGED_WORDS[self.lang]]) /
                               len(words)) if len(words) != 0 else 0.0

        if flagged_words_ratio > 1.0:
            flagged_words_ratio = 1.0

        sample['stats']['flagged_words_ratio'] = flagged_words_ratio
        return sample

    def process(self, sample):
        return sample['stats']['flagged_words_ratio'] <= self.max_ratio