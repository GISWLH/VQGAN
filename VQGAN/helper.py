import torch
import torch.nn as nn
import torch.nn.functional as F
from .conv import Conv4d, ConvTranspose4d


class GroupNorm(nn.Module):
    def __init__(self, channels):
        super(GroupNorm, self).__init__()
        self.gn = nn.GroupNorm(num_groups=32, num_channels=channels, eps=1e-6, affine=True)

    def forward(self, x):
        return self.gn(x)


class Swish(nn.Module):
    def forward(self, x):
        return x * torch.sigmoid(x)


class ResidualBlock(nn.Module):
    def __init__(self, in_channels, out_channels):
        super(ResidualBlock, self).__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels

        self.block = nn.Sequential(
            GroupNorm(in_channels),
            Swish(),
            nn.Conv3d(in_channels, out_channels, 3, 1, 1),
            GroupNorm(out_channels),
            Swish(),
            nn.Conv3d(out_channels, out_channels, 3, 1, 1)
        )

        if in_channels != out_channels:
            self.channel_up = nn.Conv3d(in_channels, out_channels, 1, 1, 0)

    def forward(self, x):
        
        if self.in_channels != self.out_channels:
            x1 = self.channel_up(x)

            return self.channel_up(x)# + self.block(x)
        else:
            return x + self.block(x)
        
class ResidualBlock4D(nn.Module):
    def __init__(self, in_channels, out_channels):
        super(ResidualBlock4D, self).__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels

        self.block = nn.Sequential(
            GroupNorm(in_channels),
            Swish(),
            Conv4d(in_channels, out_channels, 3, 1, 1),
            GroupNorm(out_channels),
            Swish(),
            Conv4d(out_channels, out_channels, 3, 1, 1)
        )

        if in_channels != out_channels:
            self.channel_up = Conv4d(in_channels, out_channels, 1, 1, 0)

    def forward(self, x):
        
        if self.in_channels != self.out_channels:
            x1 = self.channel_up(x)

            return self.channel_up(x)# + self.block(x)
        else:
            return x + self.block(x)


class UpSampleBlock(nn.Module):
    def __init__(self, channels):
        super(UpSampleBlock, self).__init__()
        self.conv = nn.Conv3d(channels, channels, kernel_size=(1, 3, 3), stride=1,padding=(0, 1, 1))
        
    def forward(self, x):
        x = ConvTranspose4d(x, scale_factor=(1, 2, 2))
        return self.conv(x)
    
class UpSampleBlock4D(nn.Module):
    def __init__(self, channels):
        super(UpSampleBlock4D, self).__init__()
        self.conv = Conv4d(channels, channels, kernel_size=(1, 1, 3, 3), stride=(1, 1, 2, 2),padding=(0, 0, 1, 1))
        self.convTrans = ConvTranspose4d(channels, channels, kernel_size=(2, 1, 2, 2), stride=(2, 1, 2, 2),padding=(0, 0, 1, 1))
    def forward(self, x):
        #x = F.interpolate(x, scale_factor=(1, 1, 2, 2))
        return self.convTrans(x)


class DownSampleBlock(nn.Module):
    def __init__(self, channels):
        super(DownSampleBlock, self).__init__()
        self.conv = nn.Conv3d(channels, channels, kernel_size=(1, 3, 3), stride=(1, 2, 2), padding=(0, 1, 1))

    def forward(self, x):
        pad = (0, 1, 0, 1)
        x = F.pad(x, pad, mode="constant", value=0)
        print(x.shape, 'after pad')
        return self.conv(x)
    
class DownSampleBlock4D(nn.Module):
    def __init__(self, channels):
        super(DownSampleBlock4D, self).__init__()
        self.conv = Conv4d(channels, channels, kernel_size=(1, 1, 3, 3), stride=(1, 1, 2, 2), padding=(0, 0, 1, 1))

    def forward(self, x):
        pad = (0, 1, 0, 1)
        x = F.pad(x, pad, mode="constant", value=0)
        print(x.shape, 'after pad')
        return self.conv(x)


class NonLocalBlock(nn.Module):
    def __init__(self, channels):
        super(NonLocalBlock, self).__init__()
        self.in_channels = channels

        self.gn = GroupNorm(channels)
        self.q = nn.Conv2d(channels, channels, 1, 1, 0)
        self.k = nn.Conv2d(channels, channels, 1, 1, 0)
        self.v = nn.Conv2d(channels, channels, 1, 1, 0)
        self.proj_out = nn.Conv2d(channels, channels, 1, 1, 0)

    def forward(self, x):
        h_ = self.gn(x)
        q = self.q(h_)
        k = self.k(h_)
        v = self.v(h_)

        b, c, h, w = q.shape

        q = q.reshape(b, c, h*w)
        q = q.permute(0, 2, 1)
        k = k.reshape(b, c, h*w)
        v = v.reshape(b, c, h*w)

        attn = torch.bmm(q, k)
        attn = attn * (int(c)**(-0.5))
        attn = F.softmax(attn, dim=2)
        attn = attn.permute(0, 2, 1)

        A = torch.bmm(v, attn)
        A = A.reshape(b, c, h, w)

        return x + A












