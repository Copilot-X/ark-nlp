# Copyright (c) 2021 DataArk Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Author: Xiang Wang, xiangking1995@163.com
# Status: Active


from tqdm import tqdm
from ark_nlp.dataset import PairWiseSentenceClassificationDataset


class UnsupervisedSimCSEDataset(PairWiseSentenceClassificationDataset):
    """
    用于无监督的SimCSE模型文本匹配任务的Dataset

    Args:
        data (DataFrame or string): 数据或者数据地址
        categories (list or None, optional): 数据类别, 默认值为: None
        do_retain_df (bool, optional): 是否将DataFrame格式的原始数据复制到属性retain_df中, 默认值为: False
        do_retain_dataset (bool, optional): 是否将处理成dataset格式的原始数据复制到属性retain_dataset中, 默认值为: False
        is_train (bool, optional): 数据集是否为训练集数据, 默认值为: True
        is_test (bool, optional): 数据集是否为测试集数据, 默认值为: False
        progress_verbose (bool, optional): 是否显示数据进度, 默认值为: True
    """  # noqa: ignore flake8"

    def _get_categories(self):
        if 'label' in self.dataset[0]:
            return sorted(list(set([data['label'] for data in self.dataset])))
        else:
            return None

    def _convert_to_transformer_ids(self, tokenizer):

        features = []
        for index, row in enumerate(
                tqdm(
                    self.dataset,
                    disable=not self.progress_verbose,
                    desc='Converting sequence to transformer ids',
                )):
            input_ids_a = tokenizer.sequence_to_ids(row['text_a'])
            input_ids_b = tokenizer.sequence_to_ids(row['text_b'])

            input_ids_a, attention_mask_a, token_type_ids_a = input_ids_a
            input_ids_b, attention_mask_b, token_type_ids_b = input_ids_b

            feature = {
                'input_ids_a': input_ids_a,
                'attention_mask_a': attention_mask_a,
                'token_type_ids_a': token_type_ids_a,
                'input_ids_b': input_ids_b,
                'attention_mask_b': attention_mask_b,
                'token_type_ids_b': token_type_ids_b
            }

            if 'label' in row:
                label_ids = self.cat2id[row['label']]
                feature['label_ids'] = label_ids

            features.append(feature)

        return features
