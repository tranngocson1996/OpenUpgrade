from openupgradelib import openupgrade


def fast_fill_account_tax_country_id(env):
    vn_template = env.ref("l10n_vn.vn_template", raise_if_not_found=False)
    for company in env["res.company"].search(
        [("chart_template_id", "=", vn_template.id)]
    ):
        taxes = env["account.tax"].search([("company_id", "=", company.id)])
        query = """UPDATE account_tax
        SET country_id = %s
        WHERE id IN %s"""
        openupgrade.logged_query(
            env.cr,
            query,
            (vn_template.country_id.id, tuple(taxes.ids)),
        )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(env.cr, "l10n_vn", "15.0.2.0.1/noupdate_changes.xml")
    fast_fill_account_tax_country_id(env)
