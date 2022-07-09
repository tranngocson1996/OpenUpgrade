from openupgradelib import openupgrade


def create_account_payment_method_line(env):
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_payment_method_line apml
        SET payment_account_id = aj.{1}
        FROM account_payment_method apm
        JOIN payment_acquirer pa ON pa.provider = apm.code
        JOIN account_journal aj ON aj.id = pa.{0}
        WHERE pa.state = 'enabled' AND
        apm.payment_type = 'inbound'
        """.format(
            openupgrade.get_legacy_name("journal_id"),
            openupgrade.get_legacy_name("payment_debit_account_id"),
        ),
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_payment_method_line apml
        SET payment_account_id = aj.{1}
        FROM account_payment_method apm
        JOIN payment_acquirer pa ON pa.provider = apm.code
        JOIN account_journal aj ON aj.id = pa.{0}
        WHERE pa.state = 'enabled' AND
        apm.payment_type = 'outbound'
        """.format(
            openupgrade.get_legacy_name("journal_id"),
            openupgrade.get_legacy_name("payment_credit_account_id"),
        ),
    )


@openupgrade.migrate()
def migrate(env, version):
    create_account_payment_method_line(env)
