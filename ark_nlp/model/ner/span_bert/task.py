# Copyright (c) 2020 DataArk Authors. All Rights Reserved.
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

import torch

from ark_nlp.factory.utils import conlleval
from ark_nlp.factory.metric import SpanMetrics
from ark_nlp.factory.metric import BiaffineSpanMetrics
from ark_nlp.factory.task.base._token_classification import TokenClassificationTask


class SpanBertNERTask(TokenClassificationTask):
    """
    Span模式的命名实体识别Task
    
    Args:
        module: 深度学习模型
        optimizer (str or torch.optim.Optimizer or None, optional): 训练模型使用的优化器名或者优化器对象, 默认值为: None
        loss_function (str or object or None, optional): 训练模型使用的损失函数名或损失函数对象, 默认值为: None
        scheduler (torch.optim.lr_scheduler.LambdaLR, optional): scheduler对象, 默认值为: None
        tokenizer (object or None, optional): 分词器, 默认值为: None
        class_num (int or None, optional): 标签数目, 默认值为: None
        gpu_num (int, optional): GPU数目, 默认值为: 1
        device (torch.device, optional): torch.device对象, 当device为None时, 会自动检测是否有GPU
        cuda_device (int, optional): GPU编号, 当device为None时, 根据cuda_device设置device, 默认值为: 0
        ema_decay (int or None, optional): EMA的加权系数, 默认值为: None
        **kwargs (optional): 其他可选参数
    """  # noqa: ignore flake8"

    def get_train_loss(self, inputs, outputs, **kwargs):
        loss = self.compute_loss(inputs, outputs, **kwargs)

        return outputs, loss

    def get_evaluate_loss(self, inputs, outputs, **kwargs):
        loss = self.compute_loss(inputs, outputs, **kwargs)

        return outputs, loss

    def compute_loss(self, inputs, logits, **kwargs):
        start_logits = logits[0]
        end_logits = logits[1]

        start_logits = start_logits.view(-1, len(self.id2cat))
        end_logits = end_logits.view(-1, len(self.id2cat))

        active_loss = inputs['attention_mask'].view(-1) == 1

        active_start_logits = start_logits[active_loss]
        active_end_logits = end_logits[active_loss]

        active_start_labels = inputs['start_label_ids'].long().view(-1)[active_loss]
        active_end_labels = inputs['end_label_ids'].long().view(-1)[active_loss]

        start_loss = self.loss_function(active_start_logits, active_start_labels)
        end_loss = self.loss_function(active_end_logits, active_end_labels)

        loss = start_loss + end_loss

        return loss

    def on_evaluate_epoch_begin(self, **kwargs):

        self.metric = SpanMetrics(self.id2cat)

        return None

    def on_evaluate_step_end(self, inputs, outputs, **kwargs):

        with torch.no_grad():
            # compute loss
            logits, loss = self._get_evaluate_loss(inputs, outputs, **kwargs)

        length = inputs['attention_mask'].cpu().numpy().sum() - 2

        S = []
        start_logits = logits[0]
        end_logits = logits[1]

        start_score_list = torch.argmax(start_logits, -1).cpu().numpy()
        end_score_list = torch.argmax(end_logits, -1).cpu().numpy()

        for index, (start_score,
                    end_score) in enumerate(zip(start_score_list, end_score_list)):
            start_score = start_score[1:length + 1]
            end_score = end_score[1:length + 1]

            S = []
            for i, s_l in enumerate(start_score):
                if s_l == 0:
                    continue
                for j, e_l in enumerate(end_score[i:]):
                    if s_l == e_l:
                        S.append((s_l, i, i + j))
                        break

            self.metric.update(true_subject=inputs['label_ids'][index], pred_subject=S)

        self.evaluate_logs['example_num'] += len(inputs['label_ids'])
        self.evaluate_logs['step'] += 1
        self.evaluate_logs['loss'] += loss.item()

        return logits, loss

    def on_evaluate_epoch_end(self, evaluate_verbose=True, id2cat=None, **kwargs):

        if id2cat is None:
            id2cat = self.id2cat

        with torch.no_grad():
            evaluate_infos, entity_infos = self.metric.result()

        if evaluate_verbose:
            print("********** Evaluating Done **********")
            print('evaluation: ', evaluate_infos)
            print('entity evaluation: ', entity_infos)

        return None

    def _train_collate_fn(self, batch):
        """将InputFeatures转换为Tensor"""

        input_ids = torch.tensor([f['input_ids'] for f in batch], dtype=torch.long)
        attention_mask = torch.tensor([f['attention_mask'] for f in batch],
                                      dtype=torch.long)
        token_type_ids = torch.tensor([f['token_type_ids'] for f in batch],
                                      dtype=torch.long)
        start_label_ids = torch.cat([f['start_label_ids'] for f in batch])
        end_label_ids = torch.cat([f['end_label_ids'] for f in batch])
        label_ids = [f['label_ids'] for f in batch]

        tensors = {
            'input_ids': input_ids,
            'attention_mask': attention_mask,
            'token_type_ids': token_type_ids,
            'start_label_ids': start_label_ids,
            'end_label_ids': end_label_ids,
            'label_ids': label_ids
        }

        return tensors

    def _evaluate_collate_fn(self, batch):
        return self._train_collate_fn(batch)
