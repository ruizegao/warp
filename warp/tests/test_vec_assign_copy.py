# SPDX-FileCopyrightText: Copyright (c) 2022 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest

import numpy as np

import warp as wp
from warp.tests.unittest_utils import *


def setUpModule():
    wp.config.enable_vector_component_overwrites = True


def tearDownModule():
    wp.config.enable_vector_component_overwrites = False


@wp.kernel
def vec_assign_subscript(x: wp.array(dtype=float), y: wp.array(dtype=wp.vec3)):
    i = wp.tid()

    a = wp.vec3()
    a[0] = 1.0 * x[i]
    a[1] = 2.0 * x[i]
    a[2] = 3.0 * x[i]
    y[i] = a


@wp.kernel
def vec_assign_attribute(x: wp.array(dtype=float), y: wp.array(dtype=wp.vec3)):
    i = wp.tid()

    a = wp.vec3()
    a.x = 1.0 * x[i]
    a.y = 2.0 * x[i]
    a.z = 3.0 * x[i]
    y[i] = a


def test_vec_assign(test, device):
    def run(kernel):
        x = wp.ones(1, dtype=float, requires_grad=True, device=device)
        y = wp.zeros(1, dtype=wp.vec3, requires_grad=True, device=device)

        tape = wp.Tape()
        with tape:
            wp.launch(kernel, 1, inputs=[x], outputs=[y], device=device)

        y.grad = wp.ones_like(y)
        tape.backward()

        assert_np_equal(y.numpy(), np.array([[1.0, 2.0, 3.0]], dtype=float))
        assert_np_equal(x.grad.numpy(), np.array([6.0], dtype=float))

    run(vec_assign_subscript)
    run(vec_assign_attribute)


def test_vec_assign_copy(test, device):
    @wp.kernel(module="unique")
    def vec_assign_overwrite(x: wp.array(dtype=wp.vec3), y: wp.array(dtype=wp.vec3)):
        tid = wp.tid()

        a = wp.vec3()
        b = x[tid]
        a = b
        a[1] = 3.0

        y[tid] = a

    x = wp.ones(1, dtype=wp.vec3, device=device, requires_grad=True)
    y = wp.zeros(1, dtype=wp.vec3, device=device, requires_grad=True)

    tape = wp.Tape()
    with tape:
        wp.launch(vec_assign_overwrite, dim=1, inputs=[x, y], device=device)

    y.grad = wp.ones_like(y, requires_grad=False)
    tape.backward()

    assert_np_equal(y.numpy(), np.array([[1.0, 3.0, 1.0]], dtype=float))
    assert_np_equal(x.grad.numpy(), np.array([[1.0, 0.0, 1.0]], dtype=float))


def test_vec_slicing_assign_backward(test, device):
    @wp.kernel(module="unique")
    def kernel(arr_x: wp.array(dtype=wp.vec2), arr_y: wp.array(dtype=wp.vec4)):
        i = wp.tid()

        x = arr_x[i]
        y = arr_y[i]

        y[:2] = x
        y[1:-1] += x[:2]
        y[3:1:-1] -= x[0:]

        arr_y[i] = y

    x = wp.ones(1, dtype=wp.vec2, requires_grad=True, device=device)
    y = wp.zeros(1, dtype=wp.vec4, requires_grad=True, device=device)

    tape = wp.Tape()
    with tape:
        wp.launch(kernel, 1, inputs=(x,), outputs=(y,), device=device)

    y.grad = wp.ones_like(y)
    tape.backward()

    assert_np_equal(y.numpy(), np.array(((1.0, 2.0, 0.0, -1.0),), dtype=float))
    assert_np_equal(x.grad.numpy(), np.array(((1.0, 1.0),), dtype=float))


devices = get_test_devices()


class TestVecAssignCopy(unittest.TestCase):
    pass


add_function_test(TestVecAssignCopy, "test_vec_assign", test_vec_assign, devices=devices)
add_function_test(TestVecAssignCopy, "test_vec_assign_copy", test_vec_assign_copy, devices=devices)
add_function_test(
    TestVecAssignCopy, "test_vec_slicing_assign_backward", test_vec_slicing_assign_backward, devices=devices
)


if __name__ == "__main__":
    wp.clear_kernel_cache()
    unittest.main(verbosity=2, failfast=True)
