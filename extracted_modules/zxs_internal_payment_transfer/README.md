# Internal Payment Transfer

Odoo 19 module to restore the classic internal liquidity transfer workflow:
paired Send/Receive payments between bank and cash journals with automatic
journal entries and liquidity transfer account reconciliation.

## Supported scenarios

- Bank → Bank
- Bank → Cash
- Cash → Bank
- Cash → Cash and any other bank/cash journal pair in the same company

## Installation

1. Copy this module into your Odoo `addons` path.
2. Update the apps list and install **Internal Payment Transfer**.
3. Configure the company **Internal Transfer** account under
   *Accounting → Configuration → Settings*.
4. Set **Outstanding Payments** and **Outstanding Receipts** on the Manual
   payment method for each bank and cash journal.

## Dependencies

- `account` (Invoicing)

## Availability

| Platform     | Supported |
|--------------|-----------|
| Odoo Online  | No        |
| Odoo.sh      | Yes       |
| On Premise   | Yes       |

Free open-source module (LGPL-3). Compatible with Odoo Community and Enterprise
when using standard Accounting dependencies only.

## License

LGPL-3. See [LICENSE](LICENSE) for details.

## Author

[Zarixsol](https://www.zarixsol.com) — info@zarixsol.com
