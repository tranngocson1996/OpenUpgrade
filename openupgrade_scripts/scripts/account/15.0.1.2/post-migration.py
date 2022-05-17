from openupgradelib import openupgrade


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
