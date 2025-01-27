"""Copyright (c) 2023 PaddlePaddle Authors. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import paddle.nn as nn

from ppsci.arch import activation as act_mod
from ppsci.arch import base


class MLP(base.NetBase):
    """Multi layer perceptron network.

    Args:
        input_keys (List[str]): Input keys, such as ["x", "y", "z"].
        output_keys (List[str]): Output keys, such as ["u", "v", "w"].
        num_layers (Optional[int]): Number of hidden layers.
        hidden_size (Union[int, List[int]]): Number of hidden size.
        activation (str, optional): Name of activation function. Defaults to "tanh".
        skip_connection (bool, optional): Whether to use skip connection.
            Defaults to False.
        weight_norm (bool, optional): Whether to apply weight norm on parameter(s).
            Defaults to False.
    """

    def __init__(
        self,
        input_keys,
        output_keys,
        num_layers,
        hidden_size,
        activation="tanh",
        skip_connection=False,
        weight_norm=False,
    ):
        super().__init__()
        self.input_keys = input_keys
        self.output_keys = output_keys
        self.linears = []
        if isinstance(hidden_size, (tuple, list)):
            if num_layers is not None:
                raise ValueError(
                    f"num_layers should be None when hidden_size is specified"
                )
        elif isinstance(hidden_size, int):
            if not isinstance(num_layers, int):
                raise ValueError(
                    f"num_layers should be an int when hidden_size is an int"
                )
            hidden_size = [hidden_size] * num_layers
        else:
            raise ValueError(
                f"hidden_size should be list of int or int"
                f"but got {type(hidden_size)}"
            )

        # initialize FC layer(s)
        cur_size = len(self.input_keys)
        for _size in hidden_size:
            self.linears.append(nn.Linear(cur_size, _size))
            if weight_norm:
                self.linears[-1] = nn.utils.weight_norm(self.linears[-1], dim=1)
            cur_size = _size
        self.linears = nn.LayerList(self.linears)

        self.last_fc = nn.Linear(cur_size, len(self.output_keys))

        # initialize activation function
        self.act = act_mod.get_activation(activation)

        self.skip_connection = skip_connection

    def forward_tensor(self, x):
        y = x
        skip = None
        for i, linear in enumerate(self.linears):
            y = linear(y)
            if self.skip_connection and i % 2 == 0:
                if skip is not None:
                    skip = y
                    y = y + skip
                else:
                    skip = y
            y = self.act(y)

        y = self.last_fc(y)

        return y

    def forward(self, x):
        if self._input_transform is not None:
            x = self._input_transform(x)

        y = self.concat_to_tensor(x, self.input_keys, axis=-1)
        y = self.forward_tensor(y)
        y = self.split_to_dict(y, self.output_keys, axis=-1)

        if self._output_transform is not None:
            y = self._output_transform(y)
        return y
