import logging

from openupgradelib import openupgrade

from odoo import _

_logger = logging.getLogger(__name__)


def fast_fill_account_analytic_line_category(env):
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_analytic_line aal
        SET category =
            CASE
                WHEN am.move_type IN ('out_invoice', 'out_refund', 'out_receipt')
                THEN 'invoice'
                WHEN am.move_type IN ('in_invoice', 'in_refund', 'in_receipt')
                THEN 'vendor_bill'
                ELSE 'other'
            END
        FROM account_move am
        WHERE am.id = aal.move_id""",
    )


def fast_fill_res_company_account_journal_payment_account_id(env):
    """Generate the Outstanding Receipts Account and
    Outstanding Payments Account for each company.
    Later code will do it for manually created accounts.
    """
    companies = (
        env["res.company"]
        .with_context(active_test=False)
        .search([("chart_template_id", "!=", False)])
    )
    for company in companies:
        account_type_current_assets = env.ref(
            "account.data_account_type_current_assets"
        )
        if not company.account_journal_payment_debit_account_id:
            company.account_journal_payment_debit_account_id = env[
                "account.account"
            ].create(
                {
                    "name": _("Outstanding Receipts"),
                    "code": env["account.account"]._search_new_account_code(
                        company,
                        company.chart_template_id.code_digits,
                        company.bank_account_code_prefix or "",
                    ),
                    "reconcile": True,
                    "user_type_id": account_type_current_assets.id,
                    "company_id": company.id,
                }
            )

        if not company.account_journal_payment_credit_account_id:
            company.account_journal_payment_credit_account_id = env[
                "account.account"
            ].create(
                {
                    "name": _("Outstanding Payments"),
                    "code": env["account.account"]._search_new_account_code(
                        company,
                        company.chart_template_id.code_digits,
                        company.bank_account_code_prefix or "",
                    ),
                    "reconcile": True,
                    "user_type_id": account_type_current_assets.id,
                    "company_id": company.id,
                }
            )


def fast_fill_account_tax_country_id(env):
    companies = (
        env["res.company"]
        .with_context(active_test=False)
        .search([("partner_id", "!=", False)])
    )
    for company in companies:
        address_data = company.partner_id.sudo().address_get(adr_pref=["contact"])
        if address_data["contact"]:
            partner = company.partner_id.browse(address_data["contact"]).sudo()
            country = company._get_company_address_update(partner).get(
                "country_id", False
            )
            if country:
                openupgrade.logged_query(
                    env.cr,
                    """
                    UPDATE account_tax
                    SET country_id = {}
                    WHERE company_id = {}""".format(
                        country.id,
                        company.id,
                    ),
                )
    _logger.warning(
        """It is possible that country will not be sure to be filled in.
        So please check and manually add country in tax"""
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(env.cr, "account", "15.0.1.2/noupdate_changes.xml")
    openupgrade.delete_record_translations(
        env.cr,
        "account",
        [
            "email_template_edi_invoice",
            "mail_template_data_payment_receipt",
        ],
    )
    fast_fill_account_analytic_line_category(env)
    fast_fill_res_company_account_journal_payment_account_id(env)
    fast_fill_account_tax_country_id(env)
