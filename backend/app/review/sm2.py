def sm2_next(ease: float, interval_days: int, repetitions: int, quality: int) -> tuple[float, int, int]:
    """SM-2 间隔复习核心算法。

    quality 0-5(0=完全陌生,5=完美掌握);返回 (ease, interval_days, repetitions)。
    quality < 3 视为未掌握:回到 1 天后重学,重复次数清零(ease 保持不变,与开发文档 8.4 一致)。
    """
    if quality < 3:
        return ease, 1, 0
    repetitions += 1
    if repetitions == 1:
        interval = 1
    elif repetitions == 2:
        interval = 6
    else:
        interval = round(interval_days * ease)
    new_ease = ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    return round(max(1.3, new_ease), 4), interval, repetitions
