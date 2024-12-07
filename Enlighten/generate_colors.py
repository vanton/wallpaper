import colorsys


def print_color(text, r, g, b, desc=""):
    """Prints colored text using RGB values."""
    print(f"\033[38;2;{r};{g};{b}m{text}\033[0m {desc}")


def hls2rgb(h: float, l: float, s: float) -> tuple[int, ...]:
    # 当饱和度大于0时，进行颜色转换
    if s > 0:
        colors = colorsys.hls_to_rgb(h, l, s)
        red, blue, green = [int(x * 255) for x in colors]
        rgb = (red, blue, green)
    else:
        # 当饱和度为0时，返回灰色
        rgb = (int(l * 255),) * 3
    return rgb


def generate_colors(num_colors: int) -> list[tuple[int, ...]]:
    colors: list[tuple[int, ...]] = []
    for i in range(num_colors):
        # 通过HLS模型生成颜色，H(色相)在0-1之间，L(明度)和S(饱和度)设置为0.5
        h = i / num_colors  # 计算色相
        l = 0.5  # 明度
        s = 0.5  # 饱和度
        rgb = hls2rgb(h, l, s)
        colors.append(rgb)
    return colors


if __name__ == "__main__":
    # 生成20种颜色
    colors = generate_colors(20)

    # 打印颜色
    for i in colors:
        red = i[0]
        green = i[1]
        blue = i[2]
        print_color("████████████████", red, green, blue, f"({red}, {green}, {blue})")
