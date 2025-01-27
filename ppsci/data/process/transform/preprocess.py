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


class Translate(object):
    """Translate class, a transform mainly for mesh.

    Args:
        offset (Dict[str, Union[int, float]]]): A 3D vector to transform the geometry.
    """

    def __init__(self, offset):
        self.offset = offset

    def __call__(self, data_dict):
        for key in self.offset:
            data_dict[key] += self.offset[key]
        return data_dict


class Scale(object):
    """Scale class, a transform mainly for mesh.

    Args:
        scale (Dict[str, List[Union[int, float]]]): The scale parameter that is multiplied to the points/vertices of the geometry.
    """

    def __init__(self, scale):
        self.scale = scale

    def __call__(self, data_dict):
        for key in self.scale:
            data_dict[key] *= self.scale[key]
        return data_dict
