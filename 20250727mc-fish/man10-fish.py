#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minecraft 釣り時給 計算スクリプト
--------------------------------
宝釣りIII +（ゴミ0%想定）環境を前提に、
入力パラメータ（釣り回数/時、各確率、単価、XP換金レートなど）から
期待時給（円/時）を算出します。

使い方（例）:
    python mc_fishing_income.py \
        --catches-per-hour 500 \
        --treasure-rate 0.113 \
        --fish-price-cod 20 --fish-price-salmon 80 --fish-price-puffer 180 --fish-price-tropical 400 \
        --book-mending-rate 0.0377 --book-mending-single-rate 0.409 --book-mending-multi-rate 0.591 \
        --book-smite-only-rate 0.0074 --book-bane-only-rate 0.0049 --book-unb3-only-rate 0.0143 \
        --avg-enchants-per-book 2.11 --avg-xp-per-enchant 25 \
        --avg-xp-per-catch 3.5 --xp-cash-numer 40 --xp-cash-denom 12 \
        --avg-enchants-per-tool 3

デフォルト値は、あなたが提示したデータや一般的なWikiの数値（例：500回/時、
宝釣りIIIでの宝物率11.3%、本に付く修繕率3.77%等）を初期設定として持たせています。
"""

from dataclasses import dataclass, asdict
import argparse
from typing import Dict


@dataclass
class Config:
    # 釣り回数/時
    catches_per_hour: float = 500.0

    # 宝物率（宝釣りIII想定: 約11.3%）
    treasure_rate: float = 0.113

    # 本は宝物6種のうちの1つなので 1/6
    treasure_types: int = 6

    # 魚カテゴリの内訳（宝釣りIIIでもほぼ一定と仮定）
    fish_rate_cod: float = 0.60
    fish_rate_salmon: float = 0.25
    fish_rate_puffer: float = 0.13
    fish_rate_tropical: float = 0.02

    # 魚の単価
    fish_price_cod: int = 20
    fish_price_salmon: int = 80
    fish_price_puffer: int = 180
    fish_price_tropical: int = 400

    # 本全体に対する修繕本率（提示データ: 20/530 ≒ 3.77%）
    book_mending_rate: float = 0.0377

    # 修繕本の内訳（単独エンチャ本の割合 / 複数エンチャ本の割合）
    book_mending_single_rate: float = 0.409
    book_mending_multi_rate: float = 0.591

    # 「修繕以外で売れる本」の確率（全本に対する割合。あなたの推定値）
    book_smite_only_rate: float = 0.0074     # 0.74%
    book_bane_only_rate: float = 0.0049      # 0.49%
    book_unb3_only_rate: float = 0.0143      # 1.43%

    # 「1冊あたり平均エンチャ数」（提示データ: 1116/530 ≒ 2.11）
    avg_enchants_per_book: float = 2.11

    # 「1エンチャあたり返ってくるXP」の平均（表をざっと平均して 25XP くらいをデフォルト）
    avg_xp_per_enchant: float = 25.0

    # 釣り1回あたりの平均XP（1〜6XP → 平均3.5XP）
    avg_xp_per_catch: float = 3.5

    # XP換金レート（12XPで40円）
    xp_cash_numer: float = 40.0
    xp_cash_denom: float = 12.0

    # 弓・釣り竿に付く平均エンチャ数（仮に3個）
    avg_enchants_per_tool: float = 3.0

    # 修繕本の売値
    price_mending_single: int = 220_000
    price_mending_multi: int = 120_000

    # 非修繕売れる本の売値
    price_smite_only: int = 15_000
    price_bane_only: int = 15_000
    price_unb3_only: int = 5_000


def compute_income(cfg: Config) -> Dict[str, float]:
    # 1XPあたりの円レート
    yen_per_xp = cfg.xp_cash_numer / cfg.xp_cash_denom

    # 1時間あたりの宝物数
    treasures_per_hour = cfg.catches_per_hour * cfg.treasure_rate

    # 1時間あたりの本の冊数
    books_per_hour = treasures_per_hour / cfg.treasure_types

    # 1時間あたりの修繕本冊数
    mending_books_per_hour = books_per_hour * cfg.book_mending_rate

    # 修繕本 売上
    mending_single_books = mending_books_per_hour * cfg.book_mending_single_rate
    mending_multi_books = mending_books_per_hour * cfg.book_mending_multi_rate
    revenue_mending = (
        mending_single_books * cfg.price_mending_single
        + mending_multi_books * cfg.price_mending_multi
    )

    # 「修繕以外で売れる本」冊数 & 売上
    sellable_non_mending_rate = (
        cfg.book_smite_only_rate
        + cfg.book_bane_only_rate
        + cfg.book_unb3_only_rate
    )
    sellable_non_mending_books = books_per_hour * sellable_non_mending_rate

    revenue_non_mending = (
        books_per_hour * cfg.book_smite_only_rate * cfg.price_smite_only
        + books_per_hour * cfg.book_bane_only_rate * cfg.price_bane_only
        + books_per_hour * cfg.book_unb3_only_rate * cfg.price_unb3_only
    )

    # 石臼にかける本（= 売れない全ての本）
    grind_books = books_per_hour - mending_books_per_hour - sellable_non_mending_books

    # 本の石臼で返るXP
    xp_from_books = grind_books * cfg.avg_enchants_per_book * cfg.avg_xp_per_enchant
    yen_from_books = xp_from_books * yen_per_xp

    # 弓(1/6) + 釣り竿(1/6) = 2/6 の宝物 → 1時間あたり本数
    tools_per_hour = treasures_per_hour * (2 / cfg.treasure_types)

    # 道具の石臼で返るXP
    xp_from_tools = tools_per_hour * cfg.avg_enchants_per_tool * cfg.avg_xp_per_enchant
    yen_from_tools = xp_from_tools * yen_per_xp

    # 釣りそのもののXP
    xp_from_fishing = cfg.catches_per_hour * cfg.avg_xp_per_catch
    yen_from_fishing = xp_from_fishing * yen_per_xp

    # 魚の匹数（魚 = 1 - treasure_rate）
    fish_rate_total = 1.0 - cfg.treasure_rate
    fish_per_hour = cfg.catches_per_hour * fish_rate_total

    cod = fish_per_hour * cfg.fish_rate_cod
    salmon = fish_per_hour * cfg.fish_rate_salmon
    puffer = fish_per_hour * cfg.fish_rate_puffer
    tropical = fish_per_hour * cfg.fish_rate_tropical

    revenue_fish = (
        cod * cfg.fish_price_cod
        + salmon * cfg.fish_price_salmon
        + puffer * cfg.fish_price_puffer
        + tropical * cfg.fish_price_tropical
    )

    total = (
        revenue_fish
        + yen_from_fishing
        + revenue_mending
        + revenue_non_mending
        + yen_from_books
        + yen_from_tools
    )

    return {
        "treasures_per_hour": treasures_per_hour,
        "books_per_hour": books_per_hour,
        "mending_books_per_hour": mending_books_per_hour,
        "mending_single_books": mending_single_books,
        "mending_multi_books": mending_multi_books,
        "sellable_non_mending_books": sellable_non_mending_books,
        "grind_books": grind_books,
        "tools_per_hour": tools_per_hour,
        "fish_per_hour": fish_per_hour,
        "cod": cod,
        "salmon": salmon,
        "puffer": puffer,
        "tropical": tropical,
        "revenue_fish": revenue_fish,
        "yen_from_fishing": yen_from_fishing,
        "revenue_mending": revenue_mending,
        "revenue_non_mending": revenue_non_mending,
        "yen_from_books": yen_from_books,
        "yen_from_tools": yen_from_tools,
        "total_yen_per_hour": total,
        "yen_per_xp": yen_per_xp,
        "xp_from_fishing": xp_from_fishing,
        "xp_from_books": xp_from_books,
        "xp_from_tools": xp_from_tools,
    }


def main():
    parser = argparse.ArgumentParser(description="Minecraft 釣り時給計算ツール")
    # 主要パラメータのみ argparse で渡せるようにする（全部は多いので適宜追加してください）
    parser.add_argument("--catches-per-hour", type=float, default=500.0)
    parser.add_argument("--treasure-rate", type=float, default=0.113)

    parser.add_argument("--fish-price-cod", type=int, default=20)
    parser.add_argument("--fish-price-salmon", type=int, default=80)
    parser.add_argument("--fish-price-puffer", type=int, default=180)
    parser.add_argument("--fish-price-tropical", type=int, default=400)

    parser.add_argument("--book-mending-rate", type=float, default=0.0377)
    parser.add_argument("--book-mending-single-rate", type=float, default=0.409)
    parser.add_argument("--book-mending-multi-rate", type=float, default=0.591)

    parser.add_argument("--book-smite-only-rate", type=float, default=0.0074)
    parser.add_argument("--book-bane-only-rate", type=float, default=0.0049)
    parser.add_argument("--book-unb3-only-rate", type=float, default=0.0143)

    parser.add_argument("--avg-enchants-per-book", type=float, default=2.11)
    parser.add_argument("--avg-xp-per-enchant", type=float, default=25.0)
    parser.add_argument("--avg-xp-per-catch", type=float, default=3.5)

    parser.add_argument("--xp-cash-numer", type=float, default=40.0)
    parser.add_argument("--xp-cash-denom", type=float, default=12.0)

    parser.add_argument("--avg-enchants-per-tool", type=float, default=3.0)

    args = parser.parse_args()

    cfg = Config(
        catches_per_hour=args.catches_per_hour,
        treasure_rate=args.treasure_rate,
        fish_price_cod=args.fish_price_cod,
        fish_price_salmon=args.fish_price_salmon,
        fish_price_puffer=args.fish_price_puffer,
        fish_price_tropical=args.fish_price_tropical,
        book_mending_rate=args.book_mending_rate,
        book_mending_single_rate=args.book_mending_single_rate,
        book_mending_multi_rate=args.book_mending_multi_rate,
        book_smite_only_rate=args.book_smite_only_rate,
        book_bane_only_rate=args.book_bane_only_rate,
        book_unb3_only_rate=args.book_unb3_only_rate,
        avg_enchants_per_book=args.avg_enchants_per_book,
        avg_xp_per_enchant=args.avg_xp_per_enchant,
        avg_xp_per_catch=args.avg_xp_per_catch,
        xp_cash_numer=args.xp_cash_numer,
        xp_cash_denom=args.xp_cash_denom,
        avg_enchants_per_tool=args.avg_enchants_per_tool,
    )

    result = compute_income(cfg)

    print("=== 設定 ===")
    for k, v in asdict(cfg).items():
        print(f"{k}: {v}")
    print("\n=== 結果（円/時 & 冊/時 等）===")
    for k, v in result.items():
        print(f"{k}: {v:,.2f}")


if __name__ == "__main__":
    main()
