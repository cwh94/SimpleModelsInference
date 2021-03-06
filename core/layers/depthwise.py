import math

import numpy as np

# https://stackoverflow.com/questions/37674306/what-is-the-difference-between-same-and-valid-padding-in-tf-nn-max-pool-of-t
from core.layers import pad_inputs


def padding(X, pad):
    print("====== pad .....: ", (int(pad[0] // 2), pad[0] - int(pad[0] // 2)),
          (int(pad[1] // 2), pad[1] - int(pad[1] // 2)))
    return np.pad(X, ((0, 0), (int(pad[0] // 2), pad[0] - int(pad[0] // 2)),
                      (int(pad[1] // 2), pad[1] - int(pad[1] // 2)), (0, 0)), mode='constant', constant_values=0)


class DepthwiseConv2dNative1:
    def __init__(self, name, layers_dict):

        self.params = layers_dict[name]
        self.name = name
        self.type = self.params["op"]
        self.strides = self.params["strides"]

        assert self.strides[0] == 1 and self.strides[3] == 1, "Must have strides[0] = strides[3] = 1"
        # shape为4维tensor，各参数含义：[width, height, channels, kernel_nums]
        self.w = layers_dict[self.params["input"][1][:-5]]["tensor_content"]

    def forward(self, X):
        #  shape为4维tensor，各参数含义：[width, height, channels, kernel_nums]
        kernel_h, kernel_w, channel, n_filters = self.w.shape
        batch_size, h, w, in_channel = X.shape

        if self.params['padding'].lower() == 'same':
            out_height = math.ceil(h * 1.0 / self.strides[1])
            out_width = math.ceil(w * 1.0 / self.strides[2])
            # pad_needed_height = (new_height – 1) × S + F - W

            pad_h = (out_height - 1) * self.strides[1] + kernel_h - h
            pad_w = (out_width - 1) * self.strides[2] + kernel_w - w


        elif self.params['padding'].lower() == 'valid':
            pad_h = 0
            pad_w = 0
            out_height = math.ceil((h * 1.0 - kernel_h + 1) / self.strides[1])
            out_width = math.ceil((w * 1.0 - kernel_w + 1) / self.strides[2])
        else:
            raise Exception("Not support {} yet!".format(self.params['padding']))

        res = np.zeros(shape=(batch_size, out_height, out_width, channel))
        inputs_padding = padding(X, (pad_h, pad_w))

        for i in range(batch_size):
            feature_map = inputs_padding[i]
            for n_ in range(n_filters):
                for h in range(out_height):
                    for w in range(out_width):
                        vert_start = self.strides[1] * h
                        vert_end = vert_start + kernel_h
                        horiz_start = self.strides[2] * w
                        horiz_end = horiz_start + kernel_w

                        for c in range(channel):
                            x_slice = feature_map[vert_start: vert_end, horiz_start: horiz_end, c]
                            p_w = self.w[:, :, c, n_]
                            res[i, h, w, c] = np.sum(np.multiply(x_slice, p_w))

        return res


class DepthwiseConv2dNative:
    def __init__(self, name, layers_dict):

        self.params = layers_dict[name]
        self.name = name
        self.type = self.params["op"]
        self.strides = self.params["strides"]
        # shape为4维tensor，各参数含义：[width, height, channels, kernel_nums]
        self.w = layers_dict[self.params["input"][1][:-5]]["tensor_content"]

    def forward(self, X):
        #  shape为4维tensor，各参数含义：[width, height, channels, kernel_nums]
        kernel_h, kernel_w, channel, n_filters = self.w.shape
        # n_filters =1
        batch_size, h, w, in_channel = X.shape
        assert in_channel == channel, "weights and feature map channel must be equal!"

        if self.params['padding'].lower() == 'same':
            out_height = math.ceil(h * 1.0 / self.strides[1])
            out_width = math.ceil(w * 1.0 / self.strides[2])
            # pad_needed_height = (new_height – 1) × S + F - W

            pad_h = (out_height - 1) * self.strides[1] + kernel_h - h
            pad_w = (out_width - 1) * self.strides[2] + kernel_w - w

        elif self.params['padding'].lower() == 'valid':
            pad_h = 0
            pad_w = 0
            out_height = math.ceil((h * 1.0 - kernel_h + 1) / self.strides[1])
            out_width = math.ceil((w * 1.0 - kernel_w + 1) / self.strides[2])
        else:
            raise Exception("Not support {} yet!".format(self.params['padding']))

        res = np.zeros(shape=(batch_size, out_height, out_width, channel))

        inputs_padding = pad_inputs(X, (pad_h, pad_w))
        print("ori col_weights.shape: ", self.w.shape)

        col_w = self.w.swapaxes(2, 3)
        col_w = col_w.reshape([-1, col_w.shape[-1]])

        col_image = self.im2col(inputs_padding, self.w.shape[1], self.strides[1])

        for i in range(channel):
            res[:, :, :, i] = np.dot(col_image[:, :, i], col_w[:, i]).reshape((res.shape[0], res.shape[1],
                                                                               res.shape[2]))

        return res

    def im2col(self, image, k_size, stride):
        image_col = []
        # N H W C

        for i in range(0, image.shape[1] - k_size + 1, stride):
            for j in range(0, image.shape[2] - k_size + 1, stride):
                col = image[:, i:i + k_size, j:j + k_size, :].reshape([-1, image.shape[3]])
                image_col.append(col)

        image_col = np.array(image_col)

        return image_col
