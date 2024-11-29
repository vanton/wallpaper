def print_color(text, r, g, b, desc=""):
    """Prints colored text using RGB values."""
    print(f"\033[38;2;{r};{g};{b}m{text}\033[0m {desc}")


def hsl2rgb(h: float, s: float, l: float) -> tuple[int, ...]:
    # 当饱和度大于0时，进行颜色转换
    if s > 0:
        # 定义常数
        v_1_3 = 1.0 / 3
        v_1_6 = 1.0 / 6
        v_2_3 = 2.0 / 3
        q = l * (1 + s) if l < 0.5 else l + s - (l * s)
        p = l * 2 - q
        # 将 h 转换到 [0, 1] 范围内
        hk = h % 1  # 处理色相
        # 计算 RGB 的临时值
        tr = hk + v_1_3  # 红色的临时值
        tg = hk  # 绿色的临时值
        tb = hk - v_1_3  # 蓝色的临时值
        # 处理 RGB 临时值，使其在 [0, 1] 范围内
        rgb = [
            tc + 1.0 if tc < 0 else tc - 1.0 if tc > 1 else tc for tc in (tr, tg, tb)
        ]
        # 根据临时值计算最终的 RGB 值
        rgb = [
            (
                p + ((q - p) * 6 * tc)
                if tc < v_1_6
                else (
                    q
                    if v_1_6 <= tc < 0.5
                    else p + ((q - p) * 6 * (v_2_3 - tc)) if 0.5 <= tc < v_2_3 else p
                )
            )
            for tc in rgb
        ]
        # 将 RGB 值转换为 0-255 范围的整数
        rgb = tuple(int(i * 255) for i in rgb)
    else:
        # 当饱和度为0时，返回灰色
        rgb = (int(l * 255),) * 3
    return rgb


def generate_colors(num_colors: int) -> list[tuple[int, ...]]:
    colors: list[tuple[int, ...]] = []
    for i in range(num_colors):
        # 通过HSL模型生成颜色，H(色相)在0-1之间，S(饱和度)和L(明度)设置为0.5
        h = i / num_colors  # 计算色相
        s = 0.5  # 饱和度
        l = 0.5  # 明度
        rgb = hsl2rgb(h, s, l)
        colors.append(rgb)
    return colors


colors = generate_colors(20)

for i in colors:
    red = i[0]
    green = i[1]
    blue = i[2]
    print_color("████████████████", red, green, blue, f"({red}, {green}, {blue})")
