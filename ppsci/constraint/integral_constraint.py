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

import types

import numpy as np
import sympy
from sympy.parsing import sympy_parser as sp_parser

from ppsci import geometry
from ppsci.constraint import base
from ppsci.data import dataset
from ppsci.utils import misc


class IntegralConstraint(base.Constraint):
    """Class for integral constraint.

    Args:
        label_expr (Dict[str, sympy.Basic]): Expression of how to compute label.
        label_dict (Dict[str, Union[float, sympy.Basic]]): Value of label.
        geom (Geometry): Geometry which constraint applied on.
        dataloader_cfg (AttrDict): Config of building a dataloader.
        loss (LossBase): Loss object.
        random (str, optional): Random method for sampling points in geometry.
            Defaults to "pseudo".
        criteria (Callable, optional): Criteria for finely define subdomain in geometry.
            Defaults to None.
        evenly (bool, optional): Whether to use envely distribution in sampling.
            Defaults to False.
        weight_dict (Dict[str, Union[float, sympy.Basic]], optional): Weight for label
            if specified. Defaults to None.
        name (str, optional): Name of constraint object. Defaults to "IgC".
    """

    def __init__(
        self,
        label_expr,
        label_dict,
        geom,
        dataloader_cfg,
        loss,
        random="pseudo",
        criteria=None,
        evenly=False,
        weight_dict=None,
        name="IgC",
    ):
        self.label_expr = label_expr
        for label_name, label_expr in self.label_expr.items():
            if isinstance(label_expr, str):
                self.label_expr[label_name] = sp_parser.parse_expr(label_expr)

        self.label_dict = label_dict
        self.input_keys = geom.dim_keys
        self.output_keys = list(label_dict.keys())
        # "area" will be kept in "output_dict" for computation.
        if isinstance(geom, geometry.Mesh):
            self.output_keys += ["area"]

        if isinstance(criteria, str):
            criteria = eval(criteria)

        # integral sample
        input_list = []
        for _ in range(
            dataloader_cfg["sampler"]["batch_size"] * dataloader_cfg["iters_per_epoch"]
        ):
            input = geom.sample_boundary(
                dataloader_cfg["integral_batch_size"], random, criteria, evenly
            )
            input_list.append(input)
        # [batch_size, integral_batch_size, ndim]
        input = misc.stack_dict_list(input_list)

        # [batch_size, ndim]
        label = {}
        for key, value in label_dict.items():
            if isinstance(value, (int, float)):
                label[key] = np.full(
                    (next(iter(input.values())).shape[0], 1), float(value), "float32"
                )
            elif isinstance(value, sympy.Basic):
                func = sympy.lambdify(
                    sympy.symbols(geom.dim_keys),
                    value,
                    [{"amax": lambda xy, _: np.maximum(xy[0], xy[1])}, "numpy"],
                )
                label[key] = func(
                    **{k: v for k, v in input.items() if k in geom.dim_keys}
                )
            elif isinstance(value, types.FunctionType):
                func = value
                label[key] = func(input)
                if isinstance(label[key], (int, float)):
                    label[key] = np.full(
                        (next(iter(input.values())).shape[0], 1), float(label[key])
                    )
            else:
                raise NotImplementedError(f"type of {type(value)} is invalid yet.")

        # [batch_size, ndim]
        weight = {key: np.ones_like(next(iter(label.values()))) for key in label}
        if weight_dict is not None:
            for key, value in weight_dict.items():
                if isinstance(value, str):
                    value = sp_parser.parse_expr(value)

                if isinstance(value, (int, float)):
                    weight[key] = np.full_like(next(iter(label.values())), float(value))
                elif isinstance(value, sympy.Basic):
                    func = sympy.lambdify(
                        sympy.symbols(geom.dim_keys),
                        value,
                        [{"amax": lambda xy, _: np.maximum(xy[0], xy[1])}, "numpy"],
                    )
                    weight[key] = func(
                        **{k: v for k, v in input.items() if k in geom.dim_keys}
                    )
                elif isinstance(value, types.FunctionType):
                    func = value
                    weight[key] = func(input)
                    if isinstance(weight[key], (int, float)):
                        weight[key] = np.full_like(
                            next(iter(input.values())), float(weight[key])
                        )
                else:
                    raise NotImplementedError(f"type of {type(value)} is invalid yet.")

        _dataset = getattr(dataset, dataloader_cfg["dataset"])(input, label, weight)
        super().__init__(_dataset, dataloader_cfg, loss, name)
