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
"""
Code below is adapted from on https://github.com/lululxvi/deepxde
"""


import paddle


class Jacobian(object):
    """Compute Jacobian matrix J: J[i][j] = dy_i/dx_j, where i = 0, ..., dim_y-1 and
    j = 0, ..., dim_x - 1.

    It is lazy evaluation, i.e., it only computes J[i][j] when needed.

    Args:
        ys: Output Tensor of shape (batch_size, dim_y).
        xs: Input Tensor of shape (batch_size, dim_x).
    """

    def __init__(self, ys, xs):
        self.ys = ys
        self.xs = xs

        self.dim_y = ys.shape[1]
        self.dim_x = xs.shape[1]

        self.J = {}

    def __call__(self, i=0, j=None):
        """Returns J[`i`][`j`]. If `j` is ``None``, returns the gradient of y_i, i.e.,
        J[i].
        """
        if not 0 <= i < self.dim_y:
            raise ValueError(f"i={i} is not valid.")
        if j is not None and not 0 <= j < self.dim_x:
            raise ValueError(f"j={j} is not valid.")
        # Compute J[i]
        if i not in self.J:
            y = self.ys[:, i : i + 1] if self.dim_y > 1 else self.ys
            self.J[i] = paddle.grad(y, self.xs, create_graph=True)[0]

        return self.J[i] if j is None or self.dim_x == 1 else self.J[i][:, j : j + 1]


class Jacobians(object):
    """Compute multiple Jacobians.

    A new instance will be created for a new pair of (output, input). For the (output,
    input) pair that has been computed before, it will reuse the previous instance,
    rather than creating a new one.
    """

    def __init__(self):
        self.Js = {}

    def __call__(self, ys, xs, i=0, j=None):
        key = (ys, xs)
        if key not in self.Js:
            self.Js[key] = Jacobian(ys, xs)
        return self.Js[key](i, j)

    def clear(self):
        """Clear cached Jacobians."""
        self.Js = {}


class Hessian(object):
    """Compute Hessian matrix H: H[i][j] = d^2y / dx_i dx_j, where i,j = 0,..., dim_x-1.

    It is lazy evaluation, i.e., it only computes H[i][j] when needed.

    Args:
        y: Output Tensor of shape (batch_size, 1) or (batch_size, dim_y > 1).
        xs: Input Tensor of shape (batch_size, dim_x).
        component: If `y` has the shape (batch_size, dim_y > 1), then `y[:, component]`
            is used to compute the Hessian. Do not use if `y` has the shape (batch_size,
            1).
        grad_y: The gradient of `y` w.r.t. `xs`. Provide `grad_y` if known to avoid
            duplicate computation. `grad_y` can be computed from ``Jacobian``.
    """

    def __init__(self, y, xs, component=None, grad_y=None):
        dim_y = y.shape[1]

        if dim_y > 1:
            if component is None:
                raise ValueError("The component of y is missing.")
            if component >= dim_y:
                raise ValueError(
                    f"The component of y={component} cannot be larger than the "
                    f"dimension={dim_y}."
                )
        else:
            if component is not None:
                raise ValueError("Do not use component for 1D y.")
            component = 0

        if grad_y is None:
            grad_y = jacobian(y, xs, i=component, j=None)
        self.H = Jacobian(grad_y, xs)

    def __call__(self, i=0, j=0):
        """Returns H[`i`][`j`]."""
        return self.H(i, j)


class Hessians(object):
    """Compute multiple Hessians.

    A new instance will be created for a new pair of (output, input). For the (output,
    input) pair that has been computed before, it will reuse the previous instance,
    rather than creating a new one.
    """

    def __init__(self):
        self.Hs = {}

    def __call__(self, ys, xs, component=None, i=0, j=0, grad_y=None):
        key = (ys, xs, component)
        if key not in self.Hs:
            self.Hs[key] = Hessian(ys, xs, component=component, grad_y=grad_y)
        return self.Hs[key](i, j)

    def clear(self):
        """Clear cached Hessians."""
        self.Hs = {}


jacobian = Jacobians()
hessian = Hessians()


def clear():
    """Clear cached Jacobians and Hessians."""
    jacobian.clear()
    hessian.clear()
