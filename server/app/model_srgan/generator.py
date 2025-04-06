import torch
import torch.nn as nn

class GenBlock(nn.Module):  #Conv -> BN? -> PReLU?
  def __init__(
      self,
      in_channels,
      out_channels,
      use_bn = True,
      use_act = True,
      **kwargs
    ):
    super().__init__()

    self.block = nn.Sequential()
    self.block.add_module(
        "Conv",
        module = nn.Conv2d(in_channels, out_channels, **kwargs, bias = not use_bn)
    )
    if (use_bn):
      self.block.add_module(
          "BatchNorm",
          module = nn.BatchNorm2d(out_channels)
      )
    if (use_act):
      self.block.add_module(
          "Act",
          module = nn.PReLU(num_parameters=out_channels)
      )

  def forward(self, x):
    return self.block(x)

class ResidualBlock(nn.Module):
  def __init__(self, in_channels):
    super().__init__()
    self.block1 = GenBlock(
        in_channels,
        in_channels,
        kernel_size=3,
        stride=1,
        padding=1
    )
    self.block2 = GenBlock(
        in_channels,
        in_channels,
        use_act=False,
        kernel_size=3,
        stride=1,
        padding=1
    )

  def forward(self, x):
    out = self.block1(x)
    out = self.block2(out)
    return out + x

class UpsamplingBlock(nn.Module):  #Conv -> PixelShuffle -> PReLU
  def __init__(self, in_channels, scale_factor):
    super().__init__()
    self.block = nn.Sequential(
        nn.Conv2d(in_channels, in_channels * scale_factor ** 2, kernel_size = 3, stride = 1, padding = 1),
        nn.PixelShuffle(scale_factor), # # in_c * scale_factor, H, W --> in_c, H*scale_factor/2, W*scale_factor/2
        nn.PReLU(num_parameters=in_channels)
    )

  def forward(self, x):
    return self.block(x)
  

class Generator(nn.Module):
  def __init__(self, in_channels=3, num_channels=64, num_blocks=16, scale = 2):
    super().__init__()
    self.initial = GenBlock(
        in_channels,
        num_channels,
        kernel_size = 9,
        stride = 1,
        padding = 4,
        use_bn= False
    )

    self.residual_blocks = nn.Sequential(*[ResidualBlock(num_channels) for _ in range(num_blocks)])

    self.conv_block = GenBlock(
        num_channels,
        num_channels,
        kernel_size = 3,
        stride = 1,
        padding = 1,
        use_act= False
    )

    self.upsampling_blocks = nn.Sequential(
        UpsamplingBlock(num_channels, scale),
        UpsamplingBlock(num_channels, scale)
    )

    self.final = nn.Conv2d(num_channels, in_channels, kernel_size=9, stride=1, padding=4)

  def forward(self, x):
    init = self.initial(x)
    x = self.residual_blocks(init)
    x = self.conv_block(x) + init
    x = self.upsampling_blocks(x)
    return torch.tanh(self.final(x))