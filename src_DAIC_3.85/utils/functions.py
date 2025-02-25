from torch.autograd import Function
import torch.nn as nn
import torch

"""
Adapted from https://github.com/fungtion/DSN/blob/master/functions.py
"""

class ReverseLayerF(Function):

    @staticmethod
    def forward(ctx, x, p):
        ctx.p = p

        return x.view_as(x)

    @staticmethod
    def backward(ctx, grad_output):
        output = grad_output.neg() * ctx.p

        return output, None


class MSE(nn.Module):
    def __init__(self):
        super(MSE, self).__init__()

    def forward(self, pred, real):
        diffs = torch.add(real, -pred)
        n = torch.numel(diffs.data)
        mse = torch.sum(diffs.pow(2)) / n

        return mse


class SIMSE(nn.Module):

    def __init__(self):
        super(SIMSE, self).__init__()

    def forward(self, pred, real):
        diffs = torch.add(real, - pred)
        n = torch.numel(diffs.data)
        simse = torch.sum(diffs).pow(2) / (n ** 2)

        return simse


class DiffLoss(nn.Module):

    def __init__(self):
        super(DiffLoss, self).__init__()

    def forward(self, input1, input2):

        batch_size = input1.size(0)
        input1 = input1.view(batch_size, -1)
        input2 = input2.view(batch_size, -1)

        # Zero mean
        input1_mean = torch.mean(input1, dim=0, keepdims=True)
        input2_mean = torch.mean(input2, dim=0, keepdims=True)
        input1 = input1 - input1_mean
        input2 = input2 - input2_mean

        input1_l2_norm = torch.norm(input1, p=2, dim=1, keepdim=True).detach()
        input1_l2 = input1.div(input1_l2_norm.expand_as(input1) + 1e-6)
        

        input2_l2_norm = torch.norm(input2, p=2, dim=1, keepdim=True).detach()
        input2_l2 = input2.div(input2_l2_norm.expand_as(input2) + 1e-6)

        diff_loss = torch.mean((input1_l2.t().mm(input2_l2)).pow(2))

        return diff_loss

class CMD(nn.Module):
    """
    Adapted from https://github.com/wzell/cmd/blob/master/models/domain_regularizer.py
    """

    def __init__(self):
        super(CMD, self).__init__()

    def forward(self, x1, x2, n_moments):
        mx1 = torch.mean(x1, 0)
        mx2 = torch.mean(x2, 0)
        sx1 = x1-mx1
        sx2 = x2-mx2
        if torch.isnan(mx1).any() or torch.isinf(mx1).any() or torch.isnan(mx2).any() or torch.isinf(mx2).any():
            raise ValueError("Mean contains NaN or Inf values")

        dm = self.matchnorm(mx1, mx2)
        scms = dm
        for i in range(n_moments - 1):
            scms += self.scm(sx1, sx2, i + 2)
        return scms

    def matchnorm(self, x1, x2):
        # x1 = torch.clamp(x1, min=-1.0, max=1.0)
        # x2 = torch.clamp(x2, min=-1.0, max=1.0)
        power = torch.pow(x1-x2,2)
        summed = torch.sum(power)
        sqrt = torch.sqrt(summed + 1e-6).clone() # 添加一个小值以避免 sqrt(0)
        return sqrt
        # return ((x1-x2)**2).sum().sqrt()

    # def scm(self, sx1, sx2, k):
    #     ss1 = torch.mean(torch.pow(sx1, k), 0)
    #     ss2 = torch.mean(torch.pow(sx2, k), 0)
    #     return self.matchnorm(ss1, ss2)
    def scm(self, sx1, sx2, k):
        # 确保 sx1 和 sx2 是非负的，以避免 pow 操作导致数值不稳定
        eps = 1e-6  # 可以根据需要调整这个值
        sx1 = torch.clamp(sx1, min=eps)
        sx2 = torch.clamp(sx2, min=eps)

        ss1 = torch.mean(torch.pow(sx1, k), 0)
        ss2 = torch.mean(torch.pow(sx2, k), 0)

        if torch.isnan(ss1).any() or torch.isinf(ss1).any() or torch.isnan(ss2).any() or torch.isinf(ss2).any():
            raise ValueError("SCM contains NaN or Inf values")

        return self.matchnorm(ss1, ss2)