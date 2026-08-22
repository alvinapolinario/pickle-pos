"""Money and tax helpers. Prices default to VAT-inclusive (Philippines)."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

MONEY = Decimal("0.01")
DEFAULT_TAX_RATE = Decimal("0.12")


def money(value: Decimal | int | str) -> Decimal:
    return Decimal(value).quantize(MONEY, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class PricingConfig:
    tax_rate: Decimal = DEFAULT_TAX_RATE
    prices_include_tax: bool = True
    vat_registered: bool = True


def line_gross(unit_price: Decimal, quantity: Decimal) -> Decimal:
    return money(Decimal(unit_price) * Decimal(quantity))


def tax_amount(gross: Decimal, *, taxable: bool, config: PricingConfig) -> Decimal:
    amount = money(gross)
    if not taxable or config.tax_rate <= 0 or amount <= 0:
        return money(0)
    if config.prices_include_tax:
        return money(amount * config.tax_rate / (1 + config.tax_rate))
    return money(amount * config.tax_rate)


def line_net(gross: Decimal, tax: Decimal, *, config: PricingConfig) -> Decimal:
    if config.prices_include_tax:
        return money(gross)
    return money(Decimal(gross) + Decimal(tax))
